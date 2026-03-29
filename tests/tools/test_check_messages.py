import ast
from pathlib import Path

import pytest

from holdtrim.tools import check_messages
from holdtrim.tools.check_messages import ending, opening, problems


def expression(text: str) -> ast.expr:
    statement = ast.parse(text).body[0]
    assert isinstance(statement, ast.Expr)
    return statement.value


def written(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, body: str) -> None:
    path = tmp_path / "bad.py"
    path.write_text(f'"""A file."""\n\nfrom holdtrim.errors import DataError\n\n{body}\n')
    monkeypatch.setattr(check_messages, "package_files", lambda: [path])
    monkeypatch.setattr(check_messages, "where", lambda entry: entry.name)


def test_every_message_in_the_package_reads_the_same_way() -> None:
    assert problems() == []


def test_the_check_passes_over_this_package() -> None:
    assert check_messages.main() == 0


def test_the_opening_of_a_plain_string_is_the_string() -> None:
    assert opening(expression('"no station here"')) == "no station here"


def test_the_opening_of_an_f_string_is_its_first_literal() -> None:
    assert opening(expression('f"no station {code} here"')) == "no station "


def test_a_message_starting_with_a_value_has_no_opening() -> None:
    assert opening(expression('f"{code} is not a station"')) == ""


def test_the_ending_of_an_f_string_is_its_last_literal() -> None:
    assert ending(expression('f"no station {code} here"')) == " here"


def test_a_message_ending_in_a_value_has_no_ending() -> None:
    assert ending(expression('f"no station {code}"')) == ""


def test_a_full_stop_at_the_end_is_found(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    written(tmp_path, monkeypatch, 'RAISED = DataError("no station here.")')
    assert "ends in a full stop" in problems()[0]


def test_a_leading_capital_is_found(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    written(tmp_path, monkeypatch, 'RAISED = DataError("No station here")')
    assert "starts with a capital" in problems()[0]


def test_a_leading_acronym_is_allowed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    written(tmp_path, monkeypatch, 'RAISED = DataError("UN 9999 is not a UN number")')
    assert problems() == []


def test_a_message_that_says_error_is_found(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    written(tmp_path, monkeypatch, 'RAISED = DataError("error: no station here")')
    assert "starts by saying" in problems()[0]


def test_a_message_starting_with_a_value_is_left_alone(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    written(tmp_path, monkeypatch, 'RAISED = DataError(f"{1} is not a station")')
    assert problems() == []
