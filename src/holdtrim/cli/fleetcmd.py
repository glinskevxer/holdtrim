"""Commands for the fleet register: the types and their weight schedules."""

from __future__ import annotations

from pathlib import Path

import click

from holdtrim.cli.common import echo_table, opened_book
from holdtrim.schedule.compare import differences
from holdtrim.schedule.document import load_schedule, save_schedule
from holdtrim.store import fleet


@click.group("fleet")
def group() -> None:
    """The types this operation flies."""


@group.command("load")
@click.argument("schedule", type=click.Path(dir_okay=False, path_type=Path))
@click.pass_context
def load(ctx: click.Context, schedule: Path) -> None:
    """Register a type from its weight schedule document."""
    kind = load_schedule(schedule)
    with opened_book(ctx) as book:
        fleet.add_type(book.connection, kind)
    click.echo(f"registered {kind.describe()}")


@group.command("types")
@click.pass_context
def types(ctx: click.Context) -> None:
    """Every registered type."""
    with opened_book(ctx) as book:
        found = fleet.list_types(book.connection)
    echo_table(
        ["code", "name", "MZFW", "MTOW", "positions"],
        [
            [
                kind.code,
                kind.name,
                str(kind.limits.max_zero_fuel),
                str(kind.limits.max_takeoff),
                str(len(kind.layout.positions)),
            ]
            for kind in found
        ],
        empty="no types in the fleet register",
    )


@group.command("show")
@click.argument("code")
@click.pass_context
def show(ctx: click.Context, code: str) -> None:
    """The certificate weights and the index geometry for one type."""
    with opened_book(ctx) as book:
        kind = fleet.get_type(book.connection, code)
    click.echo(f"{kind.code} {kind.name}")
    for name, weight in kind.limits.as_dict().items():
        click.echo(f"{name.replace('_', ' ')} {weight} kg")
    click.echo(f"taxi allowance {kind.limits.taxi_allowance} kg")
    click.echo(f"reference arm {kind.geometry.reference_arm} m")
    click.echo(f"lemac {kind.geometry.lemac} m")
    click.echo(f"mac length {kind.geometry.mac_length} m")
    click.echo(f"index constant {kind.geometry.index_constant}")
    click.echo(f"index reference {kind.geometry.index_reference}")
    click.echo(f"structural payload {kind.structural_payload} kg")


@group.command("positions")
@click.argument("code")
@click.pass_context
def positions(ctx: click.Context, code: str) -> None:
    """The loading positions on a type, front to back."""
    with opened_book(ctx) as book:
        kind = fleet.get_type(book.connection, code)
    echo_table(
        ["position", "hold", "arm", "max kg", "kg/m", "kg/sqm", "takes"],
        [
            [
                position.code,
                position.compartment,
                str(position.arm),
                str(position.max_weight),
                str(position.max_running_load),
                str(position.max_area_load),
                "/".join(position.accepts) if position.accepts else "bulk",
            ]
            for position in kind.layout.by_arm()
        ],
        empty=f"type {code.upper()} has no positions",
    )
    for limit in kind.layout.cumulative:
        click.echo(f"combined {'+'.join(limit.positions)} max {limit.max_weight} kg")


@group.command("envelope")
@click.argument("code")
@click.argument("name")
@click.pass_context
def envelope(ctx: click.Context, code: str, name: str) -> None:
    """The breakpoints of one certified envelope."""
    with opened_book(ctx) as book:
        kind = fleet.get_type(book.connection, code)
    shape = kind.envelope(name)
    echo_table(
        ["weight", "forward", "aft", "width"],
        [
            [
                str(point.weight),
                str(point.forward_index),
                str(point.aft_index),
                str(point.width),
            ]
            for point in shape.points
        ],
        empty=f"the {shape.name} envelope has no breakpoints",
    )


@group.command("dump")
@click.argument("code")
@click.argument("destination", type=click.Path(dir_okay=False, path_type=Path))
@click.pass_context
def dump(ctx: click.Context, code: str, destination: Path) -> None:
    """Write a registered type back out as a schedule document."""
    with opened_book(ctx) as book:
        kind = fleet.get_type(book.connection, code)
    save_schedule(kind, destination)
    click.echo(f"wrote {kind.code} to {destination}")


@group.command("compare")
@click.argument("code")
@click.argument("schedule", type=click.Path(dir_okay=False, path_type=Path))
@click.pass_context
def compare(ctx: click.Context, code: str, schedule: Path) -> None:
    """Say what a new schedule document changes about a registered type."""
    incoming = load_schedule(schedule)
    with opened_book(ctx) as book:
        registered = fleet.get_type(book.connection, code)
    found = differences(registered, incoming)
    if not found:
        click.echo(f"{schedule.name} says the same as the registered {registered.code}")
        return
    for change in found:
        click.echo(change.describe())
    click.echo(f"{len(found)} difference(s)")


@group.command("remove")
@click.argument("code")
@click.pass_context
def remove(ctx: click.Context, code: str) -> None:
    """Take a type out of the register."""
    with opened_book(ctx) as book:
        fleet.remove_type(book.connection, code)
    click.echo(f"removed {code.upper()}")
