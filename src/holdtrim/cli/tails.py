"""Commands for the aeroplanes themselves."""

from __future__ import annotations

from decimal import Decimal

import click

from holdtrim.cli.common import echo_table, opened_book, parse_day
from holdtrim.model.tail import STATUSES, WEIGHING_VALID_MONTHS, Tail
from holdtrim.store import fleet


@click.group("tail")
def group() -> None:
    """The aeroplanes on the fleet."""


@group.command("add")
@click.argument("registration")
@click.argument("type_code")
@click.option("--dow", type=int, required=True, help="Dry operating weight in kilograms.")
@click.option("--doi", required=True, help="Dry operating index off the schedule.")
@click.option("--weighed", required=True, help="The day of the weighing, YYYY-MM-DD.")
@click.option("--serial", default="", help="Manufacturer serial number.")
@click.option(
    "--valid-months",
    type=int,
    default=WEIGHING_VALID_MONTHS,
    show_default=True,
    help="How long the weighing counts for.",
)
@click.pass_context
def add(
    ctx: click.Context,
    registration: str,
    type_code: str,
    dow: int,
    doi: str,
    weighed: str,
    serial: str,
    valid_months: int,
) -> None:
    """Put an aeroplane on the fleet."""
    aeroplane = Tail(
        registration=registration,
        type_code=type_code,
        dry_operating_weight=dow,
        dry_operating_index=Decimal(doi),
        weighed_on=parse_day(weighed),
        serial_number=serial,
        weighing_valid_months=valid_months,
    )
    with opened_book(ctx) as book:
        fleet.add_tail(book.connection, aeroplane)
    click.echo(f"added {aeroplane.describe()}")


@group.command("list")
@click.option("--type", "type_code", default=None, help="Only aeroplanes of one type.")
@click.pass_context
def listing(ctx: click.Context, type_code: str | None) -> None:
    """Every aeroplane on the fleet."""
    with opened_book(ctx) as book:
        found = (
            fleet.list_tails(book.connection)
            if type_code is None
            else fleet.tails_of_type(book.connection, type_code)
        )
    echo_table(
        ["registration", "type", "DOW", "DOI", "weighed", "status"],
        [
            [
                aeroplane.registration,
                aeroplane.type_code,
                str(aeroplane.dry_operating_weight),
                str(aeroplane.dry_operating_index),
                aeroplane.weighed_on.isoformat(),
                aeroplane.status,
            ]
            for aeroplane in found
        ],
        empty="no aeroplanes on the fleet",
    )


@group.command("show")
@click.argument("registration")
@click.option("--on", default=None, help="Read the weighing as at this day.")
@click.pass_context
def show(ctx: click.Context, registration: str, on: str | None) -> None:
    """One aeroplane in full."""
    with opened_book(ctx) as book:
        aeroplane = fleet.get_tail(book.connection, registration)
    click.echo(f"registration {aeroplane.registration}")
    click.echo(f"type {aeroplane.type_code}")
    click.echo(f"serial {aeroplane.serial_number or 'not recorded'}")
    click.echo(f"dry operating weight {aeroplane.dry_operating_weight} kg")
    click.echo(f"dry operating index {aeroplane.dry_operating_index}")
    click.echo(f"weighed {aeroplane.weighed_on.isoformat()}")
    click.echo(f"weighing expires {aeroplane.weighing_expires.isoformat()}")
    click.echo(f"status {aeroplane.status}")
    if on is not None:
        day = parse_day(on)
        left = aeroplane.days_of_weighing_left(day)
        if left < 0:
            click.echo(f"weighing expired {-left} days ago")
        else:
            click.echo(f"weighing good for another {left} days")


@group.command("status")
@click.argument("registration")
@click.argument("status", type=click.Choice(STATUSES))
@click.pass_context
def set_status(ctx: click.Context, registration: str, status: str) -> None:
    """Move an aeroplane in or out of service."""
    with opened_book(ctx) as book:
        aeroplane = fleet.get_tail(book.connection, registration)
        changed = Tail(
            registration=aeroplane.registration,
            type_code=aeroplane.type_code,
            dry_operating_weight=aeroplane.dry_operating_weight,
            dry_operating_index=aeroplane.dry_operating_index,
            weighed_on=aeroplane.weighed_on,
            serial_number=aeroplane.serial_number,
            status=status,
            weighing_valid_months=aeroplane.weighing_valid_months,
        )
        fleet.save_tail(book.connection, changed)
    click.echo(f"{changed.registration} is now {status}")


@group.command("vary")
@click.argument("registration")
@click.option("--weight", type=int, required=True, help="Change to the dry operating weight.")
@click.option("--index", required=True, help="Matching change to the dry operating index.")
@click.pass_context
def vary(ctx: click.Context, registration: str, weight: int, index: str) -> None:
    """Apply a variation to an aeroplane's dry operating figures."""
    with opened_book(ctx) as book:
        aeroplane = fleet.get_tail(book.connection, registration)
        changed = aeroplane.with_variation(weight, Decimal(index))
        fleet.save_tail(book.connection, changed)
    click.echo(f"varied {changed.describe()}")


@group.command("weighings")
@click.option("--on", required=True, help="The day to read the fleet as at.")
@click.option("--within", type=int, default=90, show_default=True, help="Days to look ahead.")
@click.pass_context
def weighings(ctx: click.Context, on: str, within: int) -> None:
    """Aeroplanes whose weighing has run out or is about to."""
    day = parse_day(on)
    with opened_book(ctx) as book:
        due = fleet.weighings_due(book.connection, day, within_days=within)
    echo_table(
        ["registration", "weighed", "expires", "days left"],
        [
            [
                aeroplane.registration,
                aeroplane.weighed_on.isoformat(),
                aeroplane.weighing_expires.isoformat(),
                str(aeroplane.days_of_weighing_left(day)),
            ]
            for aeroplane in due
        ],
        empty=f"no weighings due within {within} days of {day.isoformat()}",
    )


@group.command("remove")
@click.argument("registration")
@click.pass_context
def remove(ctx: click.Context, registration: str) -> None:
    """Take an aeroplane off the fleet."""
    with opened_book(ctx) as book:
        fleet.remove_tail(book.connection, registration)
    click.echo(f"removed {registration.upper()}")
