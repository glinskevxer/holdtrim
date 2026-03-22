"""Commands for building a load plan."""

from __future__ import annotations

import click

from holdtrim.balance import limits
from holdtrim.cli.common import echo_table, opened_book, parse_day
from holdtrim.errors import DataError
from holdtrim.office import Office
from holdtrim.plan.allocate import Item, for_flight
from holdtrim.plan.loadplan import Assignment
from holdtrim.plan.offload import GENERAL, LEVELS, Candidate, for_balance
from holdtrim.store import flights, plans, ulds


def _pair(text: str) -> tuple[str, int]:
    """Read a CODE=WEIGHT argument, which is how a load is offered."""
    code, separator, weight = text.partition("=")
    if not separator or not weight.strip().isdigit():
        raise DataError(f"{text!r} is not a device and a weight, written as CODE=KILOS")
    return code.strip().upper(), int(weight)


@click.group("plan")
def group() -> None:
    """What goes where on a flight."""


@group.command("show")
@click.argument("designator")
@click.argument("day")
@click.pass_context
def show(ctx: click.Context, designator: str, day: str) -> None:
    """The plan as it stands."""
    with opened_book(ctx) as book:
        file = Office(connection=book.connection).on(designator, parse_day(day))
        figures = file.balance()
    echo_table(
        ["position", "device", "weight", "for", "arm"],
        [
            [
                assignment.position,
                assignment.uld or "bulk",
                str(assignment.weight),
                assignment.destination or file.sector.destination,
                str(file.kind.layout.position(assignment.position).arm),
            ]
            for assignment in file.plan.assignments
        ],
        empty=f"nothing is planned for {file.sector.reference}",
    )
    click.echo(f"payload {figures.payload} kg")
    click.echo(f"zero fuel weight {figures.zero_fuel.weight} kg")
    click.echo(f"takeoff weight {figures.takeoff.weight} kg")
    click.echo(f"underload {figures.underload} kg, limited by {figures.limiting_weight}")


@group.command("put")
@click.argument("designator")
@click.argument("day")
@click.argument("position")
@click.option("--weight", type=int, required=True, help="What is going in, in kilograms.")
@click.option("--uld", default="", help="The device, left out for loose cargo.")
@click.option("--to", "destination", default="", help="Where it comes off.")
@click.pass_context
def put(
    ctx: click.Context,
    designator: str,
    day: str,
    position: str,
    weight: int,
    uld: str,
    destination: str,
) -> None:
    """Put something in a position."""
    with opened_book(ctx) as book:
        file = Office(connection=book.connection).on(designator, parse_day(day))
        file.kind.layout.position(position)
        assignment = Assignment(position=position, weight=weight, uld=uld, destination=destination)
        plan = file.plan.assign(assignment)
        plans.save(book.connection, plan)
    click.echo(f"planned {assignment.describe()}")


@group.command("pull")
@click.argument("designator")
@click.argument("day")
@click.argument("position")
@click.pass_context
def pull(ctx: click.Context, designator: str, day: str, position: str) -> None:
    """Take whatever is in a position back out."""
    with opened_book(ctx) as book:
        file = Office(connection=book.connection).on(designator, parse_day(day))
        plans.save(book.connection, file.plan.release(position))
    click.echo(f"released {position.upper()}")


@group.command("auto")
@click.argument("designator")
@click.argument("day")
@click.option("--load", "loads", multiple=True, help="A device and its gross, as CODE=KILOS.")
@click.pass_context
def auto(ctx: click.Context, designator: str, day: str, loads: tuple[str, ...]) -> None:
    """Suggest a plan, heaviest first, aiming for the middle of the envelope."""
    with opened_book(ctx) as book:
        file = Office(connection=book.connection).on(designator, parse_day(day))
        items = []
        for entry in loads:
            code, weight = _pair(entry)
            device = ulds.get(book.connection, code)
            items.append(
                Item(
                    label=device.code.formatted(),
                    weight=weight,
                    base=device.base,
                    destination=file.sector.destination,
                )
            )
        made = for_flight(file.key, file.kind, file.tail, tuple(items))
        plans.save(book.connection, made.plan)
    for assignment in made.plan.assignments:
        click.echo(f"planned {assignment.describe()}")
    for item, reason in made.unplaced:
        click.echo(f"left behind {item.label}: {reason}")
    if made.complete and made.plan.assignments:
        click.echo("everything offered was placed")


def _priority(text: str) -> tuple[str, int]:
    """Read a POSITION=LEVEL argument."""
    position, separator, level = text.partition("=")
    if not separator or not level.strip().isdigit():
        raise DataError(f"{text!r} is not a position and a level, write it as POSITION=LEVEL")
    wanted = int(level)
    if wanted not in LEVELS:
        raise DataError(f"{wanted} is not a priority, use one of {LEVELS}")
    return position.strip().upper(), wanted


@group.command("offload")
@click.argument("designator")
@click.argument("day")
@click.option(
    "--priority",
    "priorities",
    multiple=True,
    help="What a position was promised, as POSITION=LEVEL.",
)
@click.pass_context
def offload(ctx: click.Context, designator: str, day: str, priorities: tuple[str, ...]) -> None:
    """Say what has to come off, and what it should be."""
    promised = dict(_priority(entry) for entry in priorities)
    with opened_book(ctx) as book:
        file = Office(connection=book.connection).on(designator, parse_day(day))
        candidates = tuple(
            Candidate(
                position=assignment.position,
                weight=assignment.weight,
                uld=assignment.uld,
                priority=promised.get(assignment.position, GENERAL),
            )
            for assignment in file.plan.assignments
        )
        made = for_balance(file.balance(), candidates)
    if not made.removed:
        click.echo(f"{file.sector.reference} is inside its limits, nothing has to come off")
        return
    for candidate in made.removed:
        click.echo(f"offload {candidate.describe()}")
    click.echo(made.describe())
    if not made.enough:
        click.echo(f"still {made.short_by} kg over")
        raise SystemExit(6)


@group.command("check")
@click.argument("designator")
@click.argument("day")
@click.pass_context
def check(ctx: click.Context, designator: str, day: str) -> None:
    """Run every limit check against the plan."""
    with opened_book(ctx) as book:
        file = Office(connection=book.connection).on(designator, parse_day(day))
        file.check_flyable()
        found = limits.check(file.balance())
    if not found:
        click.echo(f"{file.sector.reference} passes every check")
        return
    for finding in found:
        click.echo(finding.describe())
    raise SystemExit(6)


@group.command("clear")
@click.argument("designator")
@click.argument("day")
@click.pass_context
def clear(ctx: click.Context, designator: str, day: str) -> None:
    """Throw the plan away and start again."""
    key = flights.key_for(designator, parse_day(day))
    with opened_book(ctx) as book:
        plans.remove(book.connection, key)
    click.echo(f"cleared the plan for {key}")
