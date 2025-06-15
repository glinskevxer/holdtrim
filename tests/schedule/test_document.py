import json
from pathlib import Path
from typing import Any

import pytest

from holdtrim.errors import DataError
from holdtrim.schedule.document import (
    load_schedule,
    read_schedule,
    save_schedule,
    write_schedule,
)
from tests.fleet.test_type_store import a_type


def document() -> dict[str, Any]:
    parsed: dict[str, Any] = json.loads(write_schedule(a_type()))
    return parsed


def test_a_schedule_writes_out_and_reads_back_the_same(tmp_path: Path) -> None:
    path = save_schedule(a_type(), tmp_path / "at7f.json")
    assert load_schedule(path) == a_type()


def test_the_arms_stay_text_in_the_document() -> None:
    assert document()["geometry"] == {
        "reference_arm": "12.615",
        "lemac": "11.409",
        "mac_length": "2.303",
        "index_constant": "1000.000",
        "index_reference": "50.0",
    }


def test_a_schedule_that_is_not_json_says_where_it_broke() -> None:
    with pytest.raises(DataError, match="not readable"):
        read_schedule("{ not json")


def test_a_schedule_that_is_not_a_block_is_refused() -> None:
    with pytest.raises(DataError, match="not a block of fields"):
        read_schedule("[]")


def test_a_missing_field_is_named() -> None:
    broken = document()
    del broken["geometry"]
    with pytest.raises(DataError, match="missing geometry in the schedule"):
        read_schedule(json.dumps(broken))


def test_a_missing_limit_names_the_limit_and_the_block() -> None:
    broken = document()
    limits = dict(broken["limits"])
    del limits["max_landing"]
    broken["limits"] = limits
    with pytest.raises(DataError, match="missing max_landing in limits"):
        read_schedule(json.dumps(broken))


def test_a_weight_written_as_text_is_refused() -> None:
    broken = document()
    limits = dict(broken["limits"])
    limits["max_landing"] = "22350"
    broken["limits"] = limits
    with pytest.raises(DataError, match="not a whole number of kilograms"):
        read_schedule(json.dumps(broken))


def test_an_arm_written_as_a_number_is_refused() -> None:
    broken = document()
    geometry = dict(broken["geometry"])
    geometry["lemac"] = 11.409
    broken["geometry"] = geometry
    with pytest.raises(DataError, match="written as text"):
        read_schedule(json.dumps(broken))


def test_an_arm_that_is_not_a_number_is_refused() -> None:
    broken = document()
    geometry = dict(broken["geometry"])
    geometry["lemac"] = "the front bit"
    broken["geometry"] = geometry
    with pytest.raises(DataError, match="is not a number"):
        read_schedule(json.dumps(broken))


def test_a_schedule_with_no_positions_is_refused() -> None:
    broken = document()
    broken["positions"] = []
    with pytest.raises(DataError, match="lists no positions"):
        read_schedule(json.dumps(broken))


def test_a_position_missing_its_arm_names_the_position() -> None:
    broken = document()
    positions = [dict(entry) for entry in broken["positions"]]
    del positions[1]["arm"]
    broken["positions"] = positions
    with pytest.raises(DataError, match="missing arm in position 21P"):
        read_schedule(json.dumps(broken))


def test_an_accepts_field_that_is_not_a_list_is_refused() -> None:
    broken = document()
    positions = [dict(entry) for entry in broken["positions"]]
    positions[0]["accepts"] = "PMC"
    broken["positions"] = positions
    with pytest.raises(DataError, match="accepts in position 11P is not a list"):
        read_schedule(json.dumps(broken))


def test_a_cumulative_limit_with_positions_that_are_not_a_list_is_refused() -> None:
    broken = document()
    limits = [dict(entry) for entry in broken["cumulative"]]
    limits[0]["positions"] = "11P"
    broken["cumulative"] = limits
    with pytest.raises(DataError, match="positions in cumulative limit .* is not a list"):
        read_schedule(json.dumps(broken))


def test_an_envelope_with_no_breakpoints_is_refused() -> None:
    broken = document()
    envelopes = dict(broken["envelopes"])
    envelopes["takeoff"] = []
    broken["envelopes"] = envelopes
    with pytest.raises(DataError, match="the takeoff envelope has no breakpoints"):
        read_schedule(json.dumps(broken))


def test_the_fuel_table_writes_out_and_reads_back() -> None:
    assert document()["fuel"][0] == {"weight": 0, "index": "0.0"}


def test_a_schedule_with_no_fuel_table_is_refused() -> None:
    broken = document()
    del broken["fuel"]
    with pytest.raises(DataError, match="missing fuel in the schedule"):
        read_schedule(json.dumps(broken))


def test_a_fuel_table_with_no_rows_is_refused() -> None:
    broken = document()
    broken["fuel"] = []
    with pytest.raises(DataError, match="the fuel index table has no rows"):
        read_schedule(json.dumps(broken))


def test_a_schedule_that_is_not_on_disk_is_refused(tmp_path: Path) -> None:
    with pytest.raises(DataError, match="no schedule at"):
        load_schedule(tmp_path / "missing.json")
