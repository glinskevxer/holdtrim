"""Commands for the dangerous goods.

Where a shipment is loaded decides whether the load is legal, so screening
takes the positions as well as the waybills. The positions come off the plan
where the plan knows them, which is also how the check knows whether something
is in a device or loose on the floor.
"""

from __future__ import annotations

from decimal import Decimal

import click

from holdtrim.cli.common import echo_table, opened_book, parse_day
from holdtrim.danger import screen
from holdtrim.danger.notoc import Notoc, render
from holdtrim.danger.screen import Placement
from holdtrim.danger.table import CLASS_NAMES, class_name
from holdtrim.errors import DataError
from holdtrim.ids import parse_awb
from holdtrim.model.danger import DangerousGoods
from holdtrim.office import Office
from holdtrim.store import dangerous


def _placement(text: str) -> tuple[str, str]:
    """Read an AWB=POSITION argument."""
    awb, separator, position = text.partition("=")
    if not separator or not position.strip():
        raise DataError(f"{text!r} is not a waybill and a position, write it as AWB=POSITION")
    return parse_awb(awb).plain(), position.strip().upper()


@click.group("danger")
def group() -> None:
    """The dangerous goods and where they may go."""


@group.command("classes")
def classes() -> None:
    """The classes this build knows, and what they are called."""
    echo_table(
        ["class", "name"],
        [[hazard, name] for hazard, name in sorted(CLASS_NAMES.items())],
        empty="no classes",
    )


@group.command("declare")
@click.argument("awb")
@click.option("--un", type=int, required=True, help="The UN number.")
@click.option("--name", required=True, help="The proper shipping name.")
@click.option("--hazard", required=True, help="The class or division.")
@click.option("--packages", type=int, required=True, help="How many packages.")
@click.option("--quantity", required=True, help="Net quantity in one package.")
@click.option("--unit", required=True, help="The unit that quantity is in.")
@click.option("--pg", default="", help="Packing group, blank where there is none.")
@click.option("--pi", default="", help="Packing instruction.")
@click.option("--risk", "risks", multiple=True, help="A subsidiary risk.")
@click.option("--cao", is_flag=True, help="Cargo aircraft only.")
@click.option("--ti", default="", help="Transport index, for class 7.")
@click.pass_context
def declare(
    ctx: click.Context,
    awb: str,
    un: int,
    name: str,
    hazard: str,
    packages: int,
    quantity: str,
    unit: str,
    pg: str,
    pi: str,
    risks: tuple[str, ...],
    cao: bool,
    ti: str,
) -> None:
    """Declare one line against a waybill."""
    entry = DangerousGoods(
        un_number=un,
        proper_shipping_name=name,
        hazard_class=hazard,
        packages=packages,
        net_quantity=Decimal(quantity),
        unit=unit,
        packing_group=pg,
        packing_instruction=pi,
        subsidiary_risks=risks,
        cargo_aircraft_only=cao,
        transport_index=Decimal(ti) if ti else None,
    )
    with opened_book(ctx) as book:
        dangerous.declare(book.connection, awb, entry)
    click.echo(f"declared {entry.describe()} against {awb}")


@group.command("list")
@click.option("--awb", default=None, help="Only one waybill.")
@click.pass_context
def listing(ctx: click.Context, awb: str | None) -> None:
    """Everything declared, or everything on one waybill."""
    with opened_book(ctx) as book:
        keys = [awb] if awb else dangerous.waybills(book.connection)
        lines = [(key, entry) for key in keys for entry in dangerous.against(book.connection, key)]
    echo_table(
        ["waybill", "UN", "class", "name", "packages", "quantity", "CAO"],
        [
            [
                key,
                str(entry.un_number),
                entry.hazard_class,
                entry.proper_shipping_name,
                str(entry.packages),
                f"{entry.total_quantity} {entry.unit}",
                "yes" if entry.cargo_aircraft_only else "no",
            ]
            for key, entry in lines
        ],
        empty="nothing is declared",
    )


@group.command("screen")
@click.argument("designator")
@click.argument("day")
@click.option("--place", "places", multiple=True, help="A waybill and a position, as AWB=POSITION.")
@click.pass_context
def screen_load(ctx: click.Context, designator: str, day: str, places: tuple[str, ...]) -> None:
    """Screen what is planned against the segregation rules."""
    with opened_book(ctx) as book:
        file = Office(connection=book.connection).on(designator, parse_day(day))
        placements = []
        for entry in places:
            key, position = _placement(entry)
            declared = dangerous.against(book.connection, key)
            in_device = file.plan.holds(position) and bool(file.plan.at(position).uld)
            placements.append(
                Placement(position=position, awb=key, entries=declared, in_device=in_device)
            )
        found = screen.screen(tuple(placements), file.kind.layout, freighter=file.sector.freighter)
    if not found:
        click.echo(f"{file.sector.reference} screens clean")
        return
    for finding in found:
        click.echo(f"{finding.severity} {finding.describe()}")
    if not screen.acceptable(found):
        raise SystemExit(6)


@group.command("notoc")
@click.argument("designator")
@click.argument("day")
@click.option("--by", "prepared_by", required=True, help="Who prepared the notice.")
@click.option("--place", "places", multiple=True, help="A waybill and a position, as AWB=POSITION.")
@click.pass_context
def notoc(
    ctx: click.Context, designator: str, day: str, prepared_by: str, places: tuple[str, ...]
) -> None:
    """Print the notification to captain."""
    with opened_book(ctx) as book:
        file = Office(connection=book.connection).on(designator, parse_day(day))
        placements = []
        for entry in places:
            key, position = _placement(entry)
            placements.append(
                Placement(
                    position=position,
                    awb=key,
                    entries=dangerous.against(book.connection, key),
                )
            )
    notice = Notoc(
        sector=file.sector, placements=tuple(placements), prepared_by=prepared_by
    ).issue()
    click.echo(render(notice), nl=False)


@group.command("meaning")
@click.argument("hazard")
def meaning(hazard: str) -> None:
    """What one class or division is called."""
    click.echo(f"{hazard} {class_name(hazard)}")


@group.command("clear")
@click.argument("awb")
@click.pass_context
def clear(ctx: click.Context, awb: str) -> None:
    """Take every declared line off a waybill."""
    with opened_book(ctx) as book:
        gone = dangerous.clear(book.connection, awb)
    click.echo(f"cleared {gone} line(s) from {awb}")
