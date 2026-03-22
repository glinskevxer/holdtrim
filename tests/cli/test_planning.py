from pathlib import Path

from click.testing import CliRunner, Result

from holdtrim.cli import planning
from holdtrim.cli.main import cli
from tests.cli.conftest import invoke


def run(runner: CliRunner, book: Path, *args: str) -> Result:
    return invoke(runner, book, *args)


def planned(runner: CliRunner, book: Path, position: str = "11P", weight: str = "2000") -> Result:
    uld = {"11P": "PMC12345QH", "21P": "PMC12346QH"}.get(position, "")
    args = [
        "plan",
        "put",
        "QH412",
        "2025-05-12",
        position,
        "--weight",
        weight,
        "--to",
        "LGG",
    ]
    if uld:
        args.extend(["--uld", uld])
    return run(runner, book, *args)


def test_an_empty_plan_says_so(runner: CliRunner, flight_book: Path) -> None:
    result = run(runner, flight_book, "plan", "show", "QH412", "2025-05-12")
    assert "nothing is planned for QH412/12" in result.output


def test_something_can_be_put_in_a_position(runner: CliRunner, flight_book: Path) -> None:
    result = planned(runner, flight_book)
    assert "planned 11P PMC12345QH 2000 kg for LGG" in result.output


def test_the_plan_shows_the_weights_that_follow(runner: CliRunner, flight_book: Path) -> None:
    planned(runner, flight_book)
    result = run(runner, flight_book, "plan", "show", "QH412", "2025-05-12")
    assert "payload 2000 kg" in result.output
    assert "zero fuel weight 15640 kg" in result.output
    assert "limited by" in result.output


def test_a_position_that_is_not_on_the_type_is_refused(
    runner: CliRunner, flight_book: Path
) -> None:
    result = run(
        runner, flight_book, "plan", "put", "QH412", "2025-05-12", "99X", "--weight", "100"
    )
    assert result.exception is not None


def test_a_position_can_be_pulled_back_out(runner: CliRunner, flight_book: Path) -> None:
    planned(runner, flight_book)
    run(runner, flight_book, "plan", "pull", "QH412", "2025-05-12", "11P")
    result = run(runner, flight_book, "plan", "show", "QH412", "2025-05-12")
    assert "nothing is planned" in result.output


def test_a_good_plan_passes_every_check(runner: CliRunner, flight_book: Path) -> None:
    planned(runner, flight_book)
    result = run(runner, flight_book, "plan", "check", "QH412", "2025-05-12")
    assert "passes every check" in result.output


def test_an_overloaded_position_fails_the_check(runner: CliRunner, flight_book: Path) -> None:
    planned(runner, flight_book, weight="3400")
    result = run(runner, flight_book, "plan", "check", "QH412", "2025-05-12")
    assert "position 11P" in result.output
    assert result.exit_code == 6


def test_the_planner_places_what_it_is_offered(runner: CliRunner, flight_book: Path) -> None:
    result = run(
        runner,
        flight_book,
        "plan",
        "auto",
        "QH412",
        "2025-05-12",
        "--load",
        "PMC12345QH=2000",
        "--load",
        "PMC12346QH=1500",
    )
    assert "everything offered was placed" in result.output
    assert "PMC12345QH" in result.output


def test_the_planner_says_what_it_could_not_place(runner: CliRunner, flight_book: Path) -> None:
    result = run(
        runner,
        flight_book,
        "plan",
        "auto",
        "QH412",
        "2025-05-12",
        "--load",
        "PMC12345QH=3400",
    )
    assert "left behind PMC12345QH" in result.output


def test_a_load_that_is_not_a_pair_is_refused(runner: CliRunner, flight_book: Path) -> None:
    result = run(runner, flight_book, "plan", "auto", "QH412", "2025-05-12", "--load", "PMC12345QH")
    assert result.exception is not None


def test_a_flight_inside_its_limits_offloads_nothing(runner: CliRunner, flight_book: Path) -> None:
    planned(runner, flight_book)
    result = run(runner, flight_book, "plan", "offload", "QH412", "2025-05-12")
    assert "is inside its limits" in result.output


def test_an_overloaded_flight_says_what_comes_off(runner: CliRunner, flight_book: Path) -> None:
    planned(runner, flight_book, "11P", "3175")
    planned(runner, flight_book, "21P", "3175")
    planned(runner, flight_book, "51", "3175")
    run(runner, flight_book, "flight", "fuel", "QH412", "2025-05-12", "--takeoff", "1600")
    result = run(runner, flight_book, "plan", "offload", "QH412", "2025-05-12")
    assert "offload" in result.output
    assert "kg more than needed" in result.output


def test_the_promise_decides_what_goes_first(runner: CliRunner, flight_book: Path) -> None:
    planned(runner, flight_book, "11P", "3175")
    planned(runner, flight_book, "21P", "3175")
    planned(runner, flight_book, "51", "3175")
    run(runner, flight_book, "flight", "fuel", "QH412", "2025-05-12", "--takeoff", "1600")
    result = run(
        runner,
        flight_book,
        "plan",
        "offload",
        "QH412",
        "2025-05-12",
        "--priority",
        "11P=3",
        "--priority",
        "51=0",
    )
    assert result.output.splitlines()[0].endswith("from 51, 3175 kg")


def test_a_priority_that_is_not_a_pair_is_refused(runner: CliRunner, flight_book: Path) -> None:
    planned(runner, flight_book)
    result = run(runner, flight_book, "plan", "offload", "QH412", "2025-05-12", "--priority", "11P")
    assert result.exception is not None


def test_a_plan_can_be_thrown_away(runner: CliRunner, flight_book: Path) -> None:
    planned(runner, flight_book)
    result = run(runner, flight_book, "plan", "clear", "QH412", "2025-05-12")
    assert "cleared the plan" in result.output


def test_the_group_is_registered_under_its_name() -> None:
    assert cli.commands["plan"] is planning.group
