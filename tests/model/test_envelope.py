from decimal import Decimal

import pytest

from holdtrim.errors import DataError, RuleError
from holdtrim.model.envelope import Envelope, EnvelopePoint


def envelope() -> Envelope:
    return Envelope(
        name="zero fuel",
        points=(
            EnvelopePoint(weight=13000, forward_index=Decimal("38.0"), aft_index=Decimal("62.0")),
            EnvelopePoint(weight=17000, forward_index=Decimal("42.0"), aft_index=Decimal("60.0")),
            EnvelopePoint(weight=20800, forward_index=Decimal("46.0"), aft_index=Decimal("57.0")),
        ),
    )


def test_a_breakpoint_with_the_limits_the_wrong_way_round_is_refused() -> None:
    with pytest.raises(DataError, match="is not forward of the aft limit"):
        EnvelopePoint(weight=13000, forward_index=Decimal("62"), aft_index=Decimal("38"))


def test_a_breakpoint_reports_how_wide_it_is() -> None:
    assert envelope().points[0].width == Decimal("24.0")


def test_an_envelope_needs_two_breakpoints() -> None:
    with pytest.raises(DataError, match="at least two breakpoints"):
        Envelope(
            name="takeoff",
            points=(
                EnvelopePoint(weight=13000, forward_index=Decimal("38"), aft_index=Decimal("62")),
            ),
        )


def test_an_envelope_with_no_name_is_refused() -> None:
    with pytest.raises(DataError, match="needs a name"):
        Envelope(name="  ", points=envelope().points)


def test_breakpoints_out_of_weight_order_are_refused() -> None:
    with pytest.raises(DataError, match="not in weight order"):
        Envelope(name="takeoff", points=tuple(reversed(envelope().points)))


def test_the_envelope_knows_the_weights_it_is_drawn_for() -> None:
    assert envelope().lightest == 13000
    assert envelope().heaviest == 20800


def test_a_weight_off_the_ends_is_not_covered() -> None:
    assert not envelope().covers(12000)
    assert not envelope().covers(21000)
    assert envelope().covers(17000)


def test_the_limits_at_a_breakpoint_are_the_printed_ones() -> None:
    assert envelope().limits_at(17000) == (Decimal("42.0"), Decimal("60.0"))


def test_the_limits_between_breakpoints_interpolate() -> None:
    forward, aft = envelope().limits_at(15000)
    assert forward == Decimal("40.0")
    assert aft == Decimal("61.0")


def test_the_limits_at_the_lightest_weight_read_straight_off() -> None:
    assert envelope().limits_at(13000) == (Decimal("38.0"), Decimal("62.0"))


def test_a_weight_outside_the_envelope_is_refused_with_the_range() -> None:
    with pytest.raises(RuleError, match="runs 13000 to 20800 kg"):
        envelope().limits_at(21000)


def test_an_index_inside_the_shape_is_inside() -> None:
    assert envelope().contains(17000, Decimal("50"))


def test_an_index_forward_of_the_limit_is_outside() -> None:
    assert not envelope().contains(17000, Decimal("41.9"))


def test_an_index_aft_of_the_limit_is_outside() -> None:
    assert not envelope().contains(17000, Decimal("60.1"))


def test_the_margin_inside_is_the_distance_to_the_nearer_edge() -> None:
    assert envelope().margin(17000, Decimal("43")) == Decimal("1.0")
    assert envelope().margin(17000, Decimal("59")) == Decimal("1.0")


def test_the_margin_outside_reads_negative() -> None:
    assert envelope().margin(17000, Decimal("41")) == Decimal("-1.0")
    assert envelope().margin(17000, Decimal("61")) == Decimal("-1.0")


def test_the_widest_breakpoint_is_the_lightest_one_here() -> None:
    assert envelope().widest().weight == 13000
