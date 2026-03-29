from decimal import Decimal

from holdtrim.balance import limits
from holdtrim.findings import Finding
from tests.balance.test_loading import balance


def checks_named(found: tuple[Finding, ...]) -> list[str]:
    return [finding.check for finding in found]


def test_an_ordinary_load_passes_everything() -> None:
    assert limits.check(balance({"11P": 2000})) == ()
    assert limits.legal(balance({"11P": 2000}))


def test_too_much_payload_breaks_the_zero_fuel_weight() -> None:
    found = limits.structural(balance({"11P": 3175, "21P": 3175, "51": 3175}, takeoff_fuel=1600))
    assert found[0].check == "structural"
    assert found[0].where == "zero fuel"
    assert found[0].over_by == 2365


def test_the_finding_names_the_limit_it_broke() -> None:
    found = limits.structural(balance({"11P": 3175, "21P": 3175, "51": 3175}, takeoff_fuel=1600))
    assert "against a limit of 20800 kg" in found[0].detail


def test_too_much_fuel_breaks_the_ramp_weight() -> None:
    found = limits.structural(balance({"11P": 3000, "21P": 3000}, takeoff_fuel=4400))
    assert "ramp" in [finding.where for finding in found]


def test_a_position_over_its_limit_is_found() -> None:
    found = limits.positions(balance({"11P": 3400}))
    assert found[0].check == "position"
    assert found[0].over_by == 225


def test_a_position_inside_its_limit_is_not_found() -> None:
    assert limits.positions(balance({"11P": 3000})) == ()


def test_the_running_load_is_checked_as_well_as_the_weight() -> None:
    found = limits.positions(balance({"11P": 3900}))
    assert "running load" in checks_named(found)


def test_a_combined_limit_catches_two_legal_positions() -> None:
    found = limits.combined(balance({"11P": 3000, "21P": 3000}))
    assert found[0].check == "combined limit"
    assert found[0].where == "11P+21P"
    assert found[0].over_by == 600


def test_positions_inside_their_combined_limit_are_not_found() -> None:
    assert limits.combined(balance({"11P": 2700, "21P": 2700})) == ()


def test_a_load_far_aft_falls_outside_the_envelope() -> None:
    found = limits.envelope(balance({"51": 3000}))
    assert found
    assert found[0].check == "envelope"


def test_the_envelope_finding_names_the_limits_it_missed() -> None:
    found = limits.envelope(balance({"51": 3000}))
    assert "is outside" in found[0].detail


def test_a_weight_off_the_end_of_the_envelope_is_reported() -> None:
    found = limits.envelope(balance({"11P": 3175, "21P": 3175, "51": 3175}, takeoff_fuel=1600))
    assert any("off the" in finding.detail for finding in found)


def test_everything_runs_and_nothing_stops_at_the_first_refusal() -> None:
    found = limits.check(balance({"11P": 3400, "21P": 3400}))
    assert "position" in checks_named(found)
    assert "combined limit" in checks_named(found)


def test_an_illegal_plan_is_not_legal() -> None:
    assert not limits.legal(balance({"11P": 3400}))


def test_the_worst_margin_is_positive_inside_the_envelope() -> None:
    assert limits.worst_margin(balance({"11P": 2000})) > Decimal("0")


def test_the_worst_margin_is_negative_when_it_is_outside() -> None:
    assert limits.worst_margin(balance({"51": 3000})) < Decimal("0")
