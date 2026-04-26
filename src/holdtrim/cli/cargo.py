"""Commands for the waybill file."""

from __future__ import annotations

from decimal import Decimal

import click

from holdtrim.cargo import handling
from holdtrim.cargo.acceptance import acceptable, check
from holdtrim.cargo.buildup import build
from holdtrim.cli.common import echo_table, opened_book, parse_day
from holdtrim.errors import DataError
from holdtrim.ids import parse_awb
from holdtrim.model.consignment import Consignment
from holdtrim.office import Office
from holdtrim.store import consignments, ulds


def _codes(text: str) -> tuple[str, ...]:
    """Read the handling codes off the command line and check them."""
    codes = tuple(code for code in text.replace(",", " ").split() if code)
    unknown = handling.unknown(codes)
    if unknown:
        raise DataError(f"handling code(s) this build does not know: {', '.join(unknown)}")
    return codes


@click.group("cargo")
def group() -> None:
    """The consignments waiting to fly."""


@group.command("book")
@click.argument("awb")
@click.argument("origin")
@click.argument("destination")
@click.option("--pieces", type=int, required=True, help="How many pieces.")
@click.option("--weight", type=int, required=True, help="Gross weight in kilograms.")
@click.option("--volume", default="0", help="Volume in cubic metres.")
@click.option("--commodity", required=True, help="What it is.")
@click.option("--ready", required=True, help="The day it is ready to fly.")
@click.option("--shc", default="", help="Special handling codes, space separated.")
@click.option("--shipper", default="", help="Shipper name.")
@click.option("--consignee", default="", help="Consignee name.")
@click.pass_context
def book(
    ctx: click.Context,
    awb: str,
    origin: str,
    destination: str,
    pieces: int,
    weight: int,
    volume: str,
    commodity: str,
    ready: str,
    shc: str,
    shipper: str,
    consignee: str,
) -> None:
    """Put a waybill on file."""
    consignment = Consignment(
        awb=parse_awb(awb),
        origin=origin,
        destination=destination,
        pieces=pieces,
        gross_weight=weight,
        volume=Decimal(volume),
        commodity=commodity,
        ready_on=parse_day(ready),
        shipper=shipper,
        consignee=consignee,
        handling=_codes(shc),
    )
    with opened_book(ctx) as opened:
        consignments.add(opened.connection, consignment)
    click.echo(f"booked {consignment.describe()}")


@group.command("list")
@click.option("--from", "origin", default=None, help="Only this origin.")
@click.option("--to", "destination", default=None, help="Only this destination.")
@click.option("--ready-by", default=None, help="Only what is ready by this day.")
@click.pass_context
def listing(
    ctx: click.Context, origin: str | None, destination: str | None, ready_by: str | None
) -> None:
    """The waybills on file."""
    with opened_book(ctx) as opened:
        if origin and destination and ready_by:
            found = consignments.ready_by(
                opened.connection, origin, destination, parse_day(ready_by)
            )
        elif origin and destination:
            found = consignments.on_route(opened.connection, origin, destination)
        else:
            found = consignments.listing(opened.connection)
    echo_table(
        ["waybill", "route", "pieces", "weight", "chargeable", "ready", "codes"],
        [
            [
                str(consignment.awb),
                consignment.route,
                str(consignment.pieces),
                str(consignment.gross_weight),
                str(consignment.chargeable_weight),
                consignment.ready_on.isoformat(),
                " ".join(consignment.handling),
            ]
            for consignment in found
        ],
        empty="no waybills on file",
    )


@group.command("show")
@click.argument("awb")
@click.pass_context
def show(ctx: click.Context, awb: str) -> None:
    """One waybill in full."""
    with opened_book(ctx) as opened:
        consignment = consignments.get(opened.connection, awb)
    click.echo(f"waybill {consignment.awb}")
    click.echo(f"route {consignment.origin} to {consignment.destination}")
    click.echo(f"pieces {consignment.pieces}")
    click.echo(f"gross weight {consignment.gross_weight} kg")
    click.echo(f"volume {consignment.volume} cbm")
    click.echo(f"volumetric weight {consignment.volumetric_weight} kg")
    click.echo(f"chargeable weight {consignment.chargeable_weight} kg")
    click.echo(f"density {consignment.density} kg per cbm")
    click.echo(f"average piece {consignment.average_piece} kg")
    click.echo(f"commodity {consignment.commodity}")
    click.echo(f"ready {consignment.ready_on.isoformat()}")
    for code in consignment.handling:
        click.echo(f"handling {code} {handling.meaning(code)}")


@group.command("build")
@click.argument("code")
@click.option("--awb", "waybills", multiple=True, required=True, help="A waybill to load.")
@click.pass_context
def build_up(ctx: click.Context, code: str, waybills: tuple[str, ...]) -> None:
    """Build waybills into a device, in the order they are given.

    Nothing is written. This is the check the warehouse runs before it starts
    stacking, so that a device that will not take the load is found out about
    on paper rather than on a scale.
    """
    with opened_book(ctx) as opened:
        device = ulds.get(opened.connection, code)
        loaded = tuple(consignments.get(opened.connection, awb) for awb in waybills)
    made = build(device, loaded)
    click.echo(made.describe())
    click.echo(f"tare {made.uld.tare} kg")
    click.echo(f"contents {made.contents_weight} kg")
    click.echo(f"gross {made.gross_weight} kg of {made.uld.max_gross} kg")
    click.echo(f"spare {made.uld.payload_capacity - made.contents_weight} kg")
    click.echo(f"volume {made.volume} cbm")
    click.echo(f"stackable {'yes' if made.stackable else 'no'}")
    click.echo(f"dangerous goods {'yes' if made.dangerous else 'no'}")
    click.echo(f"cargo aircraft only {'yes' if made.cargo_aircraft_only else 'no'}")


@group.command("accept")
@click.argument("awb")
@click.argument("designator")
@click.argument("day")
@click.pass_context
def accept(ctx: click.Context, awb: str, designator: str, day: str) -> None:
    """Whether a waybill may go on a flight tonight."""
    with opened_book(ctx) as opened:
        consignment = consignments.get(opened.connection, awb)
        file = Office(connection=opened.connection).on(designator, parse_day(day))
        found = check(
            consignment,
            file.sector,
            file.kind,
            underload=file.balance().underload,
        )
    if not found:
        click.echo(f"{consignment.awb} may go on {file.sector.reference}")
        return
    for finding in found:
        click.echo(f"{finding.severity} {finding.describe()}")
    if not acceptable(found):
        raise SystemExit(6)


@group.command("tonnage")
@click.argument("origin")
@click.argument("destination")
@click.pass_context
def tonnage(ctx: click.Context, origin: str, destination: str) -> None:
    """What is booked over one sector."""
    with opened_book(ctx) as opened:
        booked = consignments.tonnage(opened.connection, origin, destination)
        found = consignments.on_route(opened.connection, origin, destination)
    click.echo(f"{origin.upper()}{destination.upper()} {len(found)} waybill(s) {booked} kg")


@group.command("remove")
@click.argument("awb")
@click.pass_context
def remove(ctx: click.Context, awb: str) -> None:
    """Take a waybill off file."""
    with opened_book(ctx) as opened:
        consignments.remove(opened.connection, awb)
    click.echo(f"removed {awb}")
