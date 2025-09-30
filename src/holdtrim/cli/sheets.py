"""Commands for the loadsheet."""

from __future__ import annotations

import click

from holdtrim.cli.common import opened_book, parse_day
from holdtrim.errors import DataError
from holdtrim.model.flight import CLOSED, Sector
from holdtrim.office import Office
from holdtrim.plan.lmc import Change, Changes
from holdtrim.sheet.loadsheet import after_changes
from holdtrim.sheet.render import render
from holdtrim.store import flights


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
@click.option("--edition", type=int, default=1, show_default=True, help="Which edition.")
@click.pass_context
def issue(ctx: click.Context, designator: str, day: str, prepared_by: str, edition: int) -> None:
    """Check the sheet, close the flight, and say it may be handed over."""
    with opened_book(ctx) as book:
        office = Office(connection=book.connection)
        file = office.on(designator, parse_day(day))
        file.check_flyable()
        sheet = file.loadsheet(prepared_by, edition=edition).issue()
        closed = Sector(
            designator=file.sector.designator,
            day=file.sector.day,
            registration=file.sector.registration,
            origin=file.sector.origin,
            destination=file.sector.destination,
            taxi_fuel=file.sector.taxi_fuel,
            trip_fuel=file.sector.trip_fuel,
            takeoff_fuel=file.sector.takeoff_fuel,
            crew=file.sector.crew,
            freighter=file.sector.freighter,
            status=CLOSED,
        )
        flights.save(book.connection, closed)
    click.echo(f"issued {sheet.reference}")
    click.echo(sheet.summary())


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
