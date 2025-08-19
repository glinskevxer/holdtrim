from decimal import Decimal

import pytest

from holdtrim.danger.notoc import Notoc, goods, header, other, radioactive, render
from holdtrim.danger.screen import Placement
from holdtrim.errors import RuleError
from tests.danger.test_screen import entry, placed
from tests.sheet.test_loadsheet import sector


def notice(**changes: object) -> Notoc:
    fields: dict[str, object] = {
        "sector": sector(),
        "placements": (placed("11P", "3"),),
        "prepared_by": "K Ravn",
    }
    fields.update(changes)
    return Notoc(**fields)  # type: ignore[arg-type]


def hot() -> Placement:
    return Placement(
        position="21P",
        awb="125-20000048",
        entries=(entry("7", transport_index=Decimal("0.4"), unit="TBq", packages=2),),
    )


def test_the_header_names_the_flight_and_the_aeroplane() -> None:
    printed = "\n".join(header(notice()))
    assert "QH412/12" in printed
    assert "OY-JAF" in printed
    assert "K Ravn" in printed


def test_the_goods_are_listed_position_first() -> None:
    lines = goods(notice())
    assert lines[0].startswith("position")
    assert lines[1].startswith("11P")


def test_a_flight_with_nothing_dangerous_says_so() -> None:
    assert goods(notice(placements=())) == ["no dangerous goods on board"]


def test_the_line_carries_the_shipping_name_and_the_quantity() -> None:
    line = goods(notice())[1]
    assert "Paint" in line
    assert "20.000 L" in line


def test_a_cargo_only_entry_says_yes() -> None:
    held = (placed("11P", entries=(entry("3", cargo_aircraft_only=True),)),)
    assert " yes " in goods(notice(placements=held))[1] + " "


def test_radioactive_material_gets_its_own_section() -> None:
    printed = "\n".join(radioactive(notice(placements=(hot(),))))
    assert "RADIOACTIVE MATERIAL" in printed
    assert "transport index 0.8" in printed


def test_nothing_radioactive_prints_no_section() -> None:
    assert radioactive(notice()) == []


def test_the_transport_indices_add_up() -> None:
    assert notice(placements=(hot(), hot())).total_transport_index == Decimal("1.6")


def test_live_animals_get_their_own_section() -> None:
    printed = "\n".join(other(notice(live_animals=(("51", "125-30000047", 4),))))
    assert "OTHER SPECIAL LOAD" in printed
    assert "AVI 4 piece(s)" in printed


def test_nothing_else_prints_no_section() -> None:
    assert other(notice()) == []


def test_a_notice_is_needed_when_anything_is_on_board() -> None:
    assert notice().needed
    assert notice(placements=(), live_animals=(("51", "125-30000047", 4),)).needed
    assert not notice(placements=()).needed


def test_a_notice_with_nobody_named_will_not_issue() -> None:
    with pytest.raises(RuleError, match="who prepared it"):
        notice(prepared_by="  ").issue()


def test_a_notice_that_names_its_preparer_issues() -> None:
    assert notice().issue() is not None


def test_the_whole_notice_ends_with_a_signature_block() -> None:
    printed = render(notice())
    assert "commander signature" in printed
    assert printed.endswith("\n")


def test_the_cargo_only_placements_come_back() -> None:
    held = (placed("11P", entries=(entry("3", cargo_aircraft_only=True),)),)
    assert len(notice(placements=held).cargo_aircraft_only) == 1
