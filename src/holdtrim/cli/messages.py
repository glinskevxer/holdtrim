"""Commands for the teletype messages.

The filing time is asked for rather than taken off the clock. This tool runs
on a laptop in an office whose clock nobody has ever checked, and a message
filed at the wrong minute is worse than one filed by hand, because it looks
right.
"""

from __future__ import annotations

import click

from holdtrim.cli.common import opened_book, parse_day
from holdtrim.errors import DataError
from holdtrim.message import cpm, ldm, mvt, ucm
from holdtrim.message.mvt import Arrival, Departure, delay
from holdtrim.message.ucm import DeviceMovement
from holdtrim.office import Office


def _movement(text: str, direction: str) -> DeviceMovement:
    """Read a CODE/STATE argument into a movement."""
    code, separator, state = text.partition("/")
    if not separator:
        raise DataError(f"{text!r} is not a device and a state, write it as CODE/L")
    return DeviceMovement(uld=code, direction=direction, state=state)


@click.group("message")
def group() -> None:
    """The messages that leave when the aeroplane does."""


@group.command("ldm")
@click.argument("designator")
@click.argument("day")
@click.option("--to", "addresses", multiple=True, required=True, help="Teletype address.")
@click.option("--from", "origin", required=True, help="Our own teletype address.")
@click.option("--filed", required=True, help="Filing time as DDHHMM.")
@click.option("--by", "prepared_by", default="the office", help="Who prepared the figures.")
@click.pass_context
def load_distribution(
    ctx: click.Context,
    designator: str,
    day: str,
    addresses: tuple[str, ...],
    origin: str,
    filed: str,
    prepared_by: str,
) -> None:
    """The load distribution message."""
    with opened_book(ctx) as book:
        file = Office(connection=book.connection).on(designator, parse_day(day))
        sheet = file.loadsheet(prepared_by)
    message = ldm.build(sheet, addresses=addresses, origin=origin, filed=filed)
    click.echo(message.render(), nl=False)


@group.command("cpm")
@click.argument("designator")
@click.argument("day")
@click.option("--to", "addresses", multiple=True, required=True, help="Teletype address.")
@click.option("--from", "origin", required=True, help="Our own teletype address.")
@click.option("--filed", required=True, help="Filing time as DDHHMM.")
@click.option("--by", "prepared_by", default="the office", help="Who prepared the figures.")
@click.pass_context
def container_pallet(
    ctx: click.Context,
    designator: str,
    day: str,
    addresses: tuple[str, ...],
    origin: str,
    filed: str,
    prepared_by: str,
) -> None:
    """The container and pallet message."""
    with opened_book(ctx) as book:
        file = Office(connection=book.connection).on(designator, parse_day(day))
        sheet = file.loadsheet(prepared_by)
    message = cpm.build(sheet, addresses=addresses, origin=origin, filed=filed)
    click.echo(message.render(), nl=False)


@group.command("ucm")
@click.argument("designator")
@click.argument("day")
@click.option("--on", "going_on", multiple=True, help="A device going on, as CODE/STATE.")
@click.option("--off", "coming_off", multiple=True, help="A device coming off, as CODE/STATE.")
@click.option("--to", "addresses", multiple=True, required=True, help="Teletype address.")
@click.option("--from", "origin", required=True, help="Our own teletype address.")
@click.option("--filed", required=True, help="Filing time as DDHHMM.")
@click.pass_context
def uld_control(
    ctx: click.Context,
    designator: str,
    day: str,
    going_on: tuple[str, ...],
    coming_off: tuple[str, ...],
    addresses: tuple[str, ...],
    origin: str,
    filed: str,
) -> None:
    """The ULD control message."""
    movements = (
        *(_movement(entry, "on") for entry in going_on),
        *(_movement(entry, "off") for entry in coming_off),
    )
    with opened_book(ctx) as book:
        file = Office(connection=book.connection).on(designator, parse_day(day))
    message = ucm.build(
        file.sector,
        movements,
        station=file.sector.origin,
        addresses=addresses,
        origin=origin,
        filed=filed,
    )
    click.echo(message.render(), nl=False)


def _delay(text: str) -> tuple[str, int]:
    """Read a CODE/MINUTES argument."""
    code, separator, minutes = text.partition("/")
    if not separator or not minutes.strip().isdigit():
        raise DataError(f"{text!r} is not a delay, write it as CODE/MINUTES")
    return delay(code, int(minutes))


@group.command("mvt")
@click.argument("designator")
@click.argument("day")
@click.option("--off-blocks", default="", help="Time off blocks, as HHMM.")
@click.option("--airborne", default="", help="Time airborne, as HHMM.")
@click.option("--eta", default="", help="Estimated arrival, as HHMM.")
@click.option("--touchdown", default="", help="Time on the runway, as HHMM.")
@click.option("--on-blocks", default="", help="Time on stand, as HHMM.")
@click.option("--delay", "delays", multiple=True, help="A delay, as CODE/MINUTES.")
@click.option("--to", "addresses", multiple=True, required=True, help="Teletype address.")
@click.option("--from", "origin", required=True, help="Our own teletype address.")
@click.option("--filed", required=True, help="Filing time as DDHHMM.")
@click.pass_context
def movement(
    ctx: click.Context,
    designator: str,
    day: str,
    off_blocks: str,
    airborne: str,
    eta: str,
    touchdown: str,
    on_blocks: str,
    delays: tuple[str, ...],
    addresses: tuple[str, ...],
    origin: str,
    filed: str,
) -> None:
    """The movement message, on departure or on arrival."""
    with opened_book(ctx) as book:
        file = Office(connection=book.connection).on(designator, parse_day(day))
    reported: Departure | Arrival
    if touchdown or on_blocks:
        reported = Arrival(touchdown=touchdown, on_blocks=on_blocks)
        station = file.sector.destination
    else:
        reported = Departure(
            off_blocks=off_blocks,
            airborne=airborne,
            estimated_arrival=eta,
            arrival_station=file.sector.destination,
            delays=tuple(_delay(entry) for entry in delays),
        )
        station = file.sector.origin
    message = mvt.build(
        file.sector,
        reported,
        station=station,
        addresses=addresses,
        origin=origin,
        filed=filed,
    )
    click.echo(message.render(), nl=False)


@group.command("plan")
@click.argument("designator")
@click.argument("day")
@click.option("--to", "addresses", multiple=True, required=True, help="Teletype address.")
@click.option("--from", "origin", required=True, help="Our own teletype address.")
@click.option("--filed", required=True, help="Filing time as DDHHMM.")
@click.pass_context
def both(
    ctx: click.Context,
    designator: str,
    day: str,
    addresses: tuple[str, ...],
    origin: str,
    filed: str,
) -> None:
    """The LDM and the CPM together, which is what actually gets sent."""
    with opened_book(ctx) as book:
        file = Office(connection=book.connection).on(designator, parse_day(day))
        sheet = file.loadsheet("the office")
    for message in (
        ldm.build(sheet, addresses=addresses, origin=origin, filed=filed),
        cpm.build(sheet, addresses=addresses, origin=origin, filed=filed),
    ):
        click.echo(message.render(), nl=False)
