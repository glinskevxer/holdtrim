from holdtrim.findings import (
    STOP,
    WATCH,
    Finding,
    by_check,
    lines,
    stopping,
    watching,
    worst,
)


def finding(check: str = "structural", over_by: int = 0, severity: str = STOP) -> Finding:
    return Finding(
        check=check, where="takeoff", detail="over the limit", over_by=over_by, severity=severity
    )


def test_a_finding_describes_itself_in_one_line() -> None:
    assert finding().describe() == "structural takeoff: over the limit"


def test_a_finding_stops_the_flight_by_default() -> None:
    assert finding().stops_the_flight
    assert not finding(severity=WATCH).stops_the_flight


def test_the_stopping_findings_are_picked_out() -> None:
    found = (finding(), finding(severity=WATCH))
    assert len(stopping(found)) == 1
    assert len(watching(found)) == 1


def test_nothing_wrong_leaves_both_lists_empty() -> None:
    assert stopping(()) == ()
    assert watching(()) == ()


def test_findings_group_by_the_check_that_made_them() -> None:
    grouped = by_check((finding("structural"), finding("envelope"), finding("structural")))
    assert sorted(grouped) == ["envelope", "structural"]
    assert len(grouped["structural"]) == 2


def test_the_worst_finding_is_the_one_over_by_the_most() -> None:
    found = (finding(over_by=10), finding(over_by=400), finding(over_by=90))
    picked = worst(found)
    assert picked is not None
    assert picked.over_by == 400


def test_a_stopping_finding_beats_a_bigger_watch() -> None:
    found = (finding(over_by=10), finding(over_by=4000, severity=WATCH))
    picked = worst(found)
    assert picked is not None
    assert picked.over_by == 10


def test_nothing_wrong_has_no_worst() -> None:
    assert worst(()) is None


def test_the_lines_come_back_for_printing() -> None:
    assert lines((finding(),)) == ("structural takeoff: over the limit",)
