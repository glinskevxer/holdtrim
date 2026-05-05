"""Commands for the reports and for moving data in and out."""

from __future__ import annotations

from pathlib import Path

import click

from holdtrim.cli.common import echo_table, opened_book, parse_day
from holdtrim.errors import DataError
from holdtrim.report import audit, capacity, season, stock
from holdtrim.store import export, flights, importer, settings


@click.group("report")
def group() -> None:
    """The questions no single record answers."""


@group.command("stock")
@click.argument("station")
@click.pass_context
def stock_report(ctx: click.Context, station: str) -> None:
    """What is standing at a station, by base size."""
    with opened_book(ctx) as book:
        lines = stock.at(book.connection, station)
    echo_table(
        ["base", "held", "serviceable", "damaged", "unusable"],
        [
            [
                line.base,
                str(line.held),
                str(line.serviceable),
                str(line.damaged),
                str(line.unusable),
            ]
            for line in lines
        ],
        empty=f"nothing is standing at {station.upper()}",
    )


@group.command("standing")
@click.argument("station")
@click.option("--on", required=True, help="The day to read the stock as at.")
@click.option("--free-days", type=int, default=None, help="Days before charging.")
@click.option("--rate", type=int, default=None, help="Charge a day after the free days.")
@click.pass_context
def standing_report(
    ctx: click.Context, station: str, on: str, free_days: int | None, rate: int | None
) -> None:
    """What has been standing too long, and what it is costing.

    The free days and the rate are policy, so they come off the settings unless
    the caller asks for something else. A default written into the command is
    how two reports end up disagreeing about the same station.
    """
    day = parse_day(on)
    with opened_book(ctx) as book:
        days = (
            settings.whole(book.connection, "demurrage.free_days")
            if free_days is None
            else free_days
        )
        daily = settings.whole(book.connection, "demurrage.daily_rate") if rate is None else rate
        found = stock.standing(book.connection, station, day, free_days=days, daily_rate=daily)
        owed = stock.owing(book.connection, station, day, free_days=days, daily_rate=daily)
    echo_table(
        ["uld", "base", "since", "days", "chargeable", "charge"],
        [
            [
                entry.uld,
                entry.base,
                entry.since.isoformat(),
                str(entry.days),
                str(entry.chargeable_days),
                str(entry.charge),
            ]
            for entry in found
        ],
        empty=f"nothing has been standing at {station.upper()} on {day.isoformat()}",
    )
    if found:
        click.echo(f"owing {owed}")


@group.command("disagreements")
@click.argument("station")
@click.option("--on", required=True, help="The day to compare the two records on.")
@click.pass_context
def disagreements(ctx: click.Context, station: str, on: str) -> None:
    """Where the register and the movement log do not agree."""
    day = parse_day(on)
    with opened_book(ctx) as book:
        found = stock.disagreements(book.connection, station, day)
    echo_table(
        ["base", "register", "movement log"],
        [[base, str(registered), str(logged)] for base, registered, logged in found],
        empty=f"the two records agree at {station.upper()} on {day.isoformat()}",
    )


@group.command("day")
@click.argument("day")
@click.pass_context
def day_report(ctx: click.Context, day: str) -> None:
    """How full every flight on a day is."""
    when = parse_day(day)
    with opened_book(ctx) as book:
        report = capacity.programme(book.connection, when)
    echo_table(
        ["flight", "route", "payload", "spare", "limited by", "positions", "findings"],
        [
            [
                entry.reference,
                entry.route,
                str(entry.payload),
                str(entry.underload),
                entry.limited_by,
                f"{entry.positions_used}/{entry.positions_total}",
                str(entry.findings),
            ]
            for entry in report
        ],
        empty=f"nothing is flying on {when.isoformat()}",
    )
    if report:
        click.echo(f"carried {capacity.carried(report)} kg, spare {capacity.spare(report)} kg")
        for limit, times in capacity.limits_biting(report).items():
            click.echo(f"limited by {limit} on {times} flight(s)")


@group.command("flight")
@click.argument("designator")
@click.argument("day")
@click.pass_context
def flight_file(ctx: click.Context, designator: str, day: str) -> None:
    """Everything the book holds about one flight."""
    key = flights.key_for(designator, parse_day(day))
    with opened_book(ctx) as book:
        trail = audit.gather(book.connection, key)
    click.echo(audit.render(trail), nl=False)


@group.command("period")
@click.option("--from", "start", required=True, help="The first day of the period.")
@click.option("--to", "end", required=True, help="The last day of the period.")
@click.pass_context
def period_report(ctx: click.Context, start: str, end: str) -> None:
    """What a period came to, flights and kilograms and limits."""
    covered = season.Period(start=parse_day(start), end=parse_day(end))
    with opened_book(ctx) as book:
        summary = season.summarise(book.connection, covered)
    for line in summary.lines():
        click.echo(line)


@group.command("export")
@click.argument("destination", type=click.Path(file_okay=False, path_type=Path))
@click.pass_context
def export_book(ctx: click.Context, destination: Path) -> None:
    """Write the whole book out as CSV."""
    with opened_book(ctx) as book:
        written = export.everything(book.connection, destination)
    for entry in written:
        click.echo(entry.describe())
    click.echo(f"{export.total(written)} row(s) in {len(written)} file(s)")


@group.command("import")
@click.argument("source", type=click.Path(dir_okay=False, exists=True, path_type=Path))
@click.pass_context
def import_bookings(ctx: click.Context, source: Path) -> None:
    """Read a booking file in, reporting the rows that would not go."""
    text = source.read_text(encoding="utf-8")
    with opened_book(ctx) as book:
        outcome = importer.load(book.connection, text)
    for rejected in outcome.rejected:
        click.echo(rejected.describe())
    click.echo(outcome.describe())
    if not outcome.clean:
        raise DataError(f"{len(outcome.rejected)} row(s) of {source.name} would not go in")
