from holdtrim.plan.lmc import Change, Changes
from holdtrim.sheet.render import (
    RULE,
    balance,
    distribution,
    footer,
    header,
    problems,
    render,
    weights,
)
from tests.sheet.test_loadsheet import sheet


def test_the_header_names_the_flight_and_the_aeroplane() -> None:
    printed = "\n".join(header(sheet()))
    assert "QH412/12" in printed
    assert "OY-JAF AT7F" in printed
    assert "BLL to LGG" in printed


def test_the_header_carries_the_edition_and_who_made_it() -> None:
    printed = "\n".join(header(sheet()))
    assert "edition" in printed
    assert "K Ravn" in printed


def test_the_weights_run_in_the_order_they_are_worked_out() -> None:
    lines = weights(sheet())
    labels = [line.split()[0] for line in lines if line and not line.startswith("-")]
    assert labels.index("dry") < labels.index("payload")
    assert labels.index("payload") < labels.index("takeoff")


def test_the_weights_are_grouped_for_reading() -> None:
    printed = "\n".join(weights(sheet()))
    assert "15 940" in printed
    assert "20 800" in printed


def test_the_distribution_lists_every_position() -> None:
    printed = "\n".join(distribution(sheet()))
    assert "11P bulk" in printed
    assert "51 bulk" in printed


def test_the_distribution_lists_the_compartments_and_the_offload_points() -> None:
    printed = "\n".join(distribution(sheet()))
    assert "compartment MAIN" in printed
    assert "for LGG" in printed


def test_an_empty_plan_says_nothing_is_loaded() -> None:
    printed = "\n".join(distribution(sheet({})))
    assert "nothing loaded" in printed


def test_the_balance_block_carries_the_trim() -> None:
    printed = "\n".join(balance(sheet()))
    assert "stabiliser trim" in printed
    assert "takeoff percent mac" in printed


def test_a_clean_sheet_prints_no_problem_block() -> None:
    assert problems(sheet().findings) == []


def test_a_sheet_with_a_finding_says_not_for_issue() -> None:
    printed = "\n".join(problems(sheet({"11P": 3400}).findings))
    assert "NOT FOR ISSUE" in printed
    assert "position 11P" in printed


def test_the_whole_sheet_renders_with_a_signature_block() -> None:
    printed = render(sheet())
    assert printed.startswith(" " * 18 + "LOADSHEET")
    assert "commander signature" in printed
    assert printed.endswith(RULE + "\n")


def test_every_line_of_the_sheet_fits_the_width() -> None:
    for line in render(sheet()).splitlines():
        assert len(line) <= 60


def test_the_sheet_ends_with_a_newline() -> None:
    assert render(sheet()).endswith("\n")


def test_a_sheet_with_no_changes_writes_none_in_the_box() -> None:
    printed = "\n".join(footer(sheet()))
    assert "LAST MINUTE CHANGES" in printed
    assert "none" in printed


def test_the_box_lists_the_changes_and_what_they_came_to() -> None:
    changes = Changes(changes=(Change(position="11P", weight=-200, what="one skid"),))
    printed = "\n".join(footer(sheet(changes=changes)))
    assert "offloaded 200 kg at 11P one skid" in printed
    assert "handled" in printed


def test_changes_past_the_tolerance_say_so_on_the_sheet() -> None:
    changes = Changes(changes=(Change(position="11P", weight=900),))
    printed = "\n".join(footer(sheet(changes=changes)))
    assert "past tolerance by" in printed
