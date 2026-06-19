"""Commands for the flight file."""

from __future__ import annotations

from dataclasses import replace

import click

from holdtrim.cli.common import echo_table, opened_book, parse_day
from holdtrim.ids import parse_flight
from holdtrim.model.flight import DEPARTED, STATUSES, Sector
from holdtrim.office import Office, departure_checks, may_depart
from holdtrim.store import fleet, flights


@click.group("flight")
def group() -> None:
    """The flights this office works."""


@group.command("add")
@click.argument("designator")
@click.argument("day")
@click.argument("registration")
@click.argument("origin")
@click.argument("destination")
@click.option("--taxi", type=int, required=True, help="Taxi fuel in kilograms.")
@click.option("--trip", type=int, required=True, help="Trip fuel in kilograms.")
@click.option("--takeoff", type=int, required=True, help="Takeoff fuel in kilograms.")
@click.option("--crew", type=int, default=2, show_default=True, help="Crew on board.")
@click.option(
    "--passenger", is_flag=True, help="A passenger flight, which refuses cargo only shipments."
)
@click.pass_context
def add(
    ctx: click.Context,
    designator: str,
    day: str,
    registration: str,
    origin: str,
    destination: str,
    taxi: int,
    trip: int,
    takeoff: int,
    crew: int,
    passenger: bool,
) -> None:
    """Put a flight on file."""
    sector = Sector(
        designator=parse_flight(designator),
        day=parse_day(day),
        registration=registration,
        origin=origin,
        destination=destination,
        taxi_fuel=taxi,
        trip_fuel=trip,
        takeoff_fuel=takeoff,
        crew=crew,
        freighter=not passenger,
    )
    with opened_book(ctx) as book:
        flights.add(book.connection, sector)
    click.echo(f"filed {sector.describe()}")


@group.command("list")
@click.option("--day", default=None, help="Only one day.")
@click.option("--tail", default=None, help="Only one aeroplane.")
@click.option("--open", "open_only", is_flag=True, help="Only the flights still open.")
@click.pass_context
def listing(ctx: click.Context, day: str | None, tail: str | None, open_only: bool) -> None:
    """The flights on file."""
    with opened_book(ctx) as book:
        if day and open_only:
            found = flights.still_open(book.connection, parse_day(day))
        elif day:
            found = flights.on_day(book.connection, parse_day(day))
        elif tail:
            found = flights.for_tail(book.connection, tail)
        else:
            found = flights.listing(book.connection)
    echo_table(
        ["flight", "date", "route", "aircraft", "takeoff fuel", "trip fuel", "status"],
        [
            [
                str(sector.designator),
                sector.day.isoformat(),
                sector.route,
                sector.registration,
                str(sector.takeoff_fuel),
                str(sector.trip_fuel),
                sector.status,
            ]
            for sector in found
        ],
        empty="no flights on file",
    )


@group.command("show")
@click.argument("designator")
@click.argument("day")
@click.pass_context
def show(ctx: click.Context, designator: str, day: str) -> None:
    """One flight in full, with the aeroplane it is on."""
    with opened_book(ctx) as book:
        sector = flights.find(book.connection, designator, parse_day(day))
        tail = fleet.get_tail(book.connection, sector.registration)
        kind = fleet.get_type(book.connection, tail.type_code)
    click.echo(f"flight {sector.reference}")
    click.echo(f"date {sector.day.isoformat()}")
    click.echo(f"route {sector.origin} to {sector.destination}")
    click.echo(f"aircraft {sector.registration} {kind.code}")
    click.echo(f"dry operating weight {tail.dry_operating_weight} kg")
    click.echo(f"taxi fuel {sector.taxi_fuel} kg")
    click.echo(f"takeoff fuel {sector.takeoff_fuel} kg")
    click.echo(f"trip fuel {sector.trip_fuel} kg")
    click.echo(f"landing fuel {sector.landing_fuel} kg")
    click.echo(f"block fuel {sector.block_fuel} kg")
    click.echo(f"crew {sector.crew}")
    click.echo(f"freighter {'yes' if sector.freighter else 'no'}")
    click.echo(f"status {sector.status}")


@group.command("status")
@click.argument("designator")
@click.argument("day")
@click.argument("status", type=click.Choice(STATUSES))
@click.pass_context
def set_status(ctx: click.Context, designator: str, day: str, status: str) -> None:
    """Move a flight on to its next state."""
    with opened_book(ctx) as book:
        sector = flights.find(book.connection, designator, parse_day(day))
        changed = replace(sector, status=status)
        flights.save(book.connection, changed)
    click.echo(f"{changed.reference} is now {status}")


@group.command("fuel")
@click.argument("designator")
@click.argument("day")
@click.option("--taxi", type=int, default=None, help="New taxi fuel.")
@click.option("--trip", type=int, default=None, help="New trip fuel.")
@click.option("--takeoff", type=int, default=None, help="New takeoff fuel.")
@click.pass_context
def refuel(
    ctx: click.Context,
    designator: str,
    day: str,
    taxi: int | None,
    trip: int | None,
    takeoff: int | None,
) -> None:
    """Record the fuel figures the flight plan came back with."""
    with opened_book(ctx) as book:
        sector = flights.find(book.connection, designator, parse_day(day))
        changed = replace(
            sector,
            taxi_fuel=sector.taxi_fuel if taxi is None else taxi,
            trip_fuel=sector.trip_fuel if trip is None else trip,
            takeoff_fuel=sector.takeoff_fuel if takeoff is None else takeoff,
        )
        flights.save(book.connection, changed)
    click.echo(
        f"{changed.reference} fuel {changed.takeoff_fuel}/{changed.trip_fuel}, "
        f"landing with {changed.landing_fuel} kg"
    )


@group.command("depart")
@click.argument("designator")
@click.argument("day")
@click.pass_context
def depart(ctx: click.Context, designator: str, day: str) -> None:
    """Record a flight as gone, once nothing is standing in the way."""
    with opened_book(ctx) as book:
        file = Office(connection=book.connection).on(designator, parse_day(day))
        found = departure_checks(book.connection, file)
        if not may_depart(found):
            for finding in found:
                click.echo(f"{finding.severity} {finding.describe()}")
            raise SystemExit(6)
        flights.save(book.connection, replace(file.sector, status=DEPARTED))
    for finding in found:
        click.echo(f"{finding.severity} {finding.describe()}")
    click.echo(f"{file.sector.reference} has gone")


@group.command("remove")
@click.argument("designator")
@click.argument("day")
@click.pass_context
def remove(ctx: click.Context, designator: str, day: str) -> None:
    """Take a flight off file."""
    key = flights.key_for(designator, parse_day(day))
    with opened_book(ctx) as book:
        flights.remove(book.connection, key)
    click.echo(f"removed {key}")
