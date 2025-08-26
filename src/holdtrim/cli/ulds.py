"""Commands for the ULD register."""

from __future__ import annotations

import click

from holdtrim.cli.common import echo_table, opened_book
from holdtrim.model.uld import CONDITIONS, CONTOURS, uld
from holdtrim.store import ulds


@click.group("uld")
def group() -> None:
    """The devices, where they are and what state they are in."""


@group.command("add")
@click.argument("code")
@click.option("--tare", type=int, required=True, help="Tare weight in kilograms.")
@click.option("--max-gross", type=int, required=True, help="Maximum gross weight.")
@click.option("--at", "at_station", default="", help="Station it is standing at.")
@click.option(
    "--condition",
    type=click.Choice(CONDITIONS),
    default="serviceable",
    show_default=True,
    help="What state it is in.",
)
@click.option(
    "--contour", type=click.Choice(CONTOURS), default="flat", show_default=True, help="Its contour."
)
@click.pass_context
def add(
    ctx: click.Context,
    code: str,
    tare: int,
    max_gross: int,
    at_station: str,
    condition: str,
    contour: str,
) -> None:
    """Put a device on the register."""
    device = uld(
        code=code,
        tare=tare,
        max_gross=max_gross,
        at_station=at_station,
        condition=condition,
        contour=contour,
    )
    with opened_book(ctx) as book:
        ulds.add(book.connection, device)
    click.echo(f"added {device.describe()}")


@group.command("list")
@click.option("--at", "station", default=None, help="Only the devices at one station.")
@click.option("--base", default="", help="Only one base size.")
@click.option("--serviceable", is_flag=True, help="Only the ones that may be loaded.")
@click.pass_context
def listing(ctx: click.Context, station: str | None, base: str, serviceable: bool) -> None:
    """The devices on the register."""
    with opened_book(ctx) as book:
        if station is None:
            found = ulds.listing(book.connection)
        else:
            found = ulds.at_station(
                book.connection, station, base=base, serviceable_only=serviceable
            )
    echo_table(
        ["code", "base", "tare", "max gross", "capacity", "at", "condition"],
        [
            [
                device.code.formatted(),
                device.base,
                str(device.tare),
                str(device.max_gross),
                str(device.payload_capacity),
                device.at_station or "in transit",
                device.condition,
            ]
            for device in found
        ],
        empty="no devices on the register",
    )


@group.command("show")
@click.argument("code")
@click.pass_context
def show(ctx: click.Context, code: str) -> None:
    """One device in full."""
    with opened_book(ctx) as book:
        device = ulds.get(book.connection, code)
    click.echo(f"code {device.code}")
    click.echo(f"category {device.code.category}")
    click.echo(f"owner {device.code.owner}")
    click.echo(f"tare {device.tare} kg")
    click.echo(f"maximum gross {device.max_gross} kg")
    click.echo(f"payload capacity {device.payload_capacity} kg")
    click.echo(f"contour {device.contour}")
    click.echo(f"condition {device.condition}")
    click.echo(f"standing at {device.at_station or 'in transit'}")


@group.command("move")
@click.argument("code")
@click.argument("station")
@click.pass_context
def move(ctx: click.Context, code: str, station: str) -> None:
    """Record a device somewhere else."""
    with opened_book(ctx) as book:
        moved = ulds.move(book.connection, code, station)
    click.echo(f"{moved.code} is now at {moved.at_station}")


@group.command("condition")
@click.argument("code")
@click.argument("state", type=click.Choice(CONDITIONS))
@click.pass_context
def condition(ctx: click.Context, code: str, state: str) -> None:
    """Record a change of condition."""
    with opened_book(ctx) as book:
        device = ulds.get(book.connection, code)
        changed = uld(
            code=device.code.formatted(),
            tare=device.tare,
            max_gross=device.max_gross,
            at_station=device.at_station,
            condition=state,
            contour=device.contour,
        )
        ulds.save(book.connection, changed)
    click.echo(f"{changed.code} is now {state}")


@group.command("stock")
@click.argument("station")
@click.pass_context
def stock(ctx: click.Context, station: str) -> None:
    """How many of each base size stand at a station."""
    with opened_book(ctx) as book:
        held = ulds.stock(book.connection, station)
    echo_table(
        ["base", "held"],
        [[base, str(count)] for base, count in held.items()],
        empty=f"nothing is standing at {station.upper()}",
    )


@group.command("transit")
@click.pass_context
def transit(ctx: click.Context) -> None:
    """The devices that are somewhere between two stations."""
    with opened_book(ctx) as book:
        found = ulds.in_transit(book.connection)
    echo_table(
        ["code", "base", "condition"],
        [[d.code.formatted(), d.base, d.condition] for d in found],
        empty="nothing is in transit",
    )


@group.command("remove")
@click.argument("code")
@click.pass_context
def remove(ctx: click.Context, code: str) -> None:
    """Take a device off the register."""
    with opened_book(ctx) as book:
        ulds.remove(book.connection, code)
    click.echo(f"removed {code.upper()}")
