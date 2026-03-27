"""Commands for the loadsheet."""

from __future__ import annotations

from dataclasses import replace

import click

from holdtrim.cli.common import opened_book, parse_day
from holdtrim.errors import DataError
from holdtrim.model.flight import CLOSED
from holdtrim.office import Office
from holdtrim.plan.lmc import Change, Changes
from holdtrim.sheet.loadsheet import after_changes
from holdtrim.sheet.render import render
from holdtrim.store import flights, sheets


def _change(text: str) -> Change:
    """Read a POSITION=WEIGHT change, where the weight may be negative."""
    position, separator, weight = text.partition("=")
    if not separator:
        raise DataError(f"{text!r} is not a change, write it as POSITION=KILOS")
    cleaned = weight.strip()
    if not cleaned.lstrip("-+").isdigit():
        raise DataError(f"{weight!r} is not a weight, write it as a whole number of kilos")
    return Change(position=position, weight=int(cleaned))


@click.group("sheet")
def group() -> None:
    """The loadsheet and what goes on it."""


@group.command("print")
@click.argument("designator")
@click.argument("day")
@click.option("--by", "prepared_by", required=True, help="Who prepared it.")
@click.option("--edition", type=int, default=1, show_default=True, help="Which edition.")
@click.option("--lmc", "lmc_changes", multiple=True, help="A change, as POSITION=KILOS.")
@click.pass_context
def print_sheet(
    ctx: click.Context,
    designator: str,
    day: str,
    prepared_by: str,
    edition: int,
    lmc_changes: tuple[str, ...],
) -> None:
    """Print the loadsheet, whether or not it may be issued."""
    changes = Changes(changes=tuple(_change(entry) for entry in lmc_changes))
    with opened_book(ctx) as book:
        file = Office(connection=book.connection).on(designator, parse_day(day))
        sheet = file.loadsheet(prepared_by, edition=edition)
    if not changes.empty:
        sheet = after_changes(sheet, changes)
    click.echo(render(sheet), nl=False)


@group.command("summary")
@click.argument("designator")
@click.argument("day")
@click.option("--by", "prepared_by", default="the office", help="Who prepared it.")
@click.pass_context
def summary(ctx: click.Context, designator: str, day: str, prepared_by: str) -> None:
    """The one line a handover note carries."""
    with opened_book(ctx) as book:
        file = Office(connection=book.connection).on(designator, parse_day(day))
        sheet = file.loadsheet(prepared_by)
    click.echo(sheet.summary())


@group.command("issue")
@click.argument("designator")
@click.argument("day")
@click.option("--by", "prepared_by", required=True, help="Who prepared it.")
@click.option("--on", default=None, help="The day it was issued, the flight day by default.")
@click.pass_context
def issue(ctx: click.Context, designator: str, day: str, prepared_by: str, on: str | None) -> None:
    """Check the sheet, record it, close the flight, and hand it over.

    The edition is not asked for. It follows what has already been issued for
    this flight, because an edition number typed in by hand is an edition
    number that eventually repeats.
    """
    when = parse_day(day)
    with opened_book(ctx) as book:
        office = Office(connection=book.connection)
        file = office.on(designator, when)
        file.check_flyable()
        edition = sheets.next_edition(book.connection, file.key)
        sheet = file.loadsheet(prepared_by, edition=edition).issue()
        sheets.record(book.connection, sheets.from_sheet(sheet, parse_day(on) if on else when))
        flights.save(book.connection, replace(file.sector, status=CLOSED))
    click.echo(f"issued {sheet.reference}")
    click.echo(sheet.summary())


@group.command("history")
@click.argument("designator")
@click.argument("day")
@click.pass_context
def history(ctx: click.Context, designator: str, day: str) -> None:
    """Every edition that has been issued for a flight."""
    key = flights.key_for(designator, parse_day(day))
    with opened_book(ctx) as book:
        found = sheets.editions(book.connection, key)
    if not found:
        click.echo(f"no loadsheet has been issued for {key}")
        return
    for entry in found:
        click.echo(entry.describe())


@group.command("findings")
@click.argument("designator")
@click.argument("day")
@click.pass_context
def findings(ctx: click.Context, designator: str, day: str) -> None:
    """Everything standing between this flight and a signed loadsheet."""
    with opened_book(ctx) as book:
        file = Office(connection=book.connection).on(designator, parse_day(day))
        sheet = file.loadsheet("the office")
    if sheet.signable:
        click.echo(f"{sheet.reference} may be issued")
        return
    for finding in sheet.findings:
        click.echo(finding.describe())
    raise SystemExit(6)
