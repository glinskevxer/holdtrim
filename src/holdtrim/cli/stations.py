"""Commands for the station register."""

from __future__ import annotations

import click

from holdtrim.cli.common import echo_table, opened_book
from holdtrim.model.station import Station
from holdtrim.store import stations


@click.group("station")
def group() -> None:
    """The airports this operation works."""


@group.command("add")
@click.argument("code")
@click.argument("name")
@click.option("--elevation", type=int, required=True, help="Field elevation in feet.")
@click.option("--agent", default="", help="Handling agent, blank where we handle ourselves.")
@click.option("--free-days", type=int, default=2, show_default=True, help="Free storage days.")
@click.pass_context
def add(
    ctx: click.Context, code: str, name: str, elevation: int, agent: str, free_days: int
) -> None:
    """Put a station in the register."""
    station = Station(
        code=code,
        name=name,
        elevation_feet=elevation,
        handling_agent=agent,
        free_storage_days=free_days,
    )
    with opened_book(ctx) as book:
        stations.add(book.connection, station)
    click.echo(f"added {station.describe()}")


@group.command("list")
@click.pass_context
def listing(ctx: click.Context) -> None:
    """Every station in the register."""
    with opened_book(ctx) as book:
        found = stations.listing(book.connection)
    echo_table(
        ["code", "name", "elevation", "agent", "free days"],
        [
            [
                station.code,
                station.name,
                str(station.elevation_feet),
                station.handling_agent or "self handled",
                str(station.free_storage_days),
            ]
            for station in found
        ],
        empty="no stations in the register",
    )


@group.command("show")
@click.argument("code")
@click.pass_context
def show(ctx: click.Context, code: str) -> None:
    """One station in full."""
    with opened_book(ctx) as book:
        station = stations.get(book.connection, code)
    click.echo(f"code {station.code}")
    click.echo(f"name {station.name}")
    click.echo(f"elevation {station.elevation_feet} ft")
    click.echo(f"agent {station.handling_agent or 'self handled'}")
    click.echo(f"free storage {station.free_storage_days} days")


@group.command("set")
@click.argument("code")
@click.option("--name", default=None, help="Change the name.")
@click.option("--agent", default=None, help="Change the handling agent.")
@click.option("--free-days", type=int, default=None, help="Change the free storage days.")
@click.pass_context
def change(
    ctx: click.Context, code: str, name: str | None, agent: str | None, free_days: int | None
) -> None:
    """Change what is already registered for a station."""
    with opened_book(ctx) as book:
        station = stations.get(book.connection, code)
        changed = Station(
            code=station.code,
            name=station.name if name is None else name,
            elevation_feet=station.elevation_feet,
            handling_agent=station.handling_agent if agent is None else agent,
            free_storage_days=(station.free_storage_days if free_days is None else free_days),
        )
        stations.save(book.connection, changed)
    click.echo(f"changed {changed.describe()}")


@group.command("remove")
@click.argument("code")
@click.pass_context
def remove(ctx: click.Context, code: str) -> None:
    """Take a station out of the register."""
    with opened_book(ctx) as book:
        stations.remove(book.connection, code)
    click.echo(f"removed {code.upper()}")
