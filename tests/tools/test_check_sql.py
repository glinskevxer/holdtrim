import ast
from pathlib import Path

import pytest

from holdtrim.tools import check_sql
from holdtrim.tools.check_sql import _is_fragment, problems


def expression(text: str) -> ast.expr:
    statement = ast.parse(text).body[0]
    assert isinstance(statement, ast.Expr)
    return statement.value


def test_nothing_in_the_package_formats_a_value_into_a_statement() -> None:
    assert problems() == []


def test_the_check_passes_over_this_package() -> None:
    assert check_sql.main() == 0


def test_a_capitalised_constant_is_a_fragment() -> None:
    assert _is_fragment(expression("COLUMNS"))
    assert _is_fragment(expression("thing.COLUMNS"))


def test_a_join_is_a_fragment() -> None:
    assert _is_fragment(expression("' AND '.join(where)"))


def test_a_number_forced_with_int_is_a_fragment() -> None:
    assert _is_fragment(expression("int(milliseconds)"))


def test_an_ordinary_variable_is_not_a_fragment() -> None:
    assert not _is_fragment(expression("code"))
    assert not _is_fragment(expression("station.code"))


def test_a_value_formatted_into_a_statement_is_found(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    bad = tmp_path / "bad.py"
    bad.write_text(
        '"""A file."""\n\n\ndef read(conn, code):\n'
        "    return conn.execute(f\"SELECT * FROM station WHERE code = '{code}'\")\n"
    )
    monkeypatch.setattr(check_sql, "package_files", lambda: [bad])
    monkeypatch.setattr(check_sql, "where", lambda path: path.name)
    found = problems()
    assert len(found) == 1
    assert "bind it as a parameter" in found[0]


def test_a_statement_built_by_concatenation_is_found(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    bad = tmp_path / "bad.py"
    bad.write_text(
        '"""A file."""\n\n\ndef read(conn, code):\n'
        '    return conn.execute("SELECT * FROM station WHERE code = " + code)\n'
    )
    monkeypatch.setattr(check_sql, "package_files", lambda: [bad])
    monkeypatch.setattr(check_sql, "where", lambda path: path.name)
    assert "built by concatenation" in problems()[0]


def test_a_column_list_formatted_in_is_allowed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    good = tmp_path / "good.py"
    good.write_text(
        '"""A file."""\n\nCOLUMNS = "code, name"\n\n\ndef read(conn, code):\n'
        '    return conn.execute(f"SELECT {COLUMNS} FROM station WHERE code = ?", (code,))\n'
    )
    monkeypatch.setattr(check_sql, "package_files", lambda: [good])
    monkeypatch.setattr(check_sql, "where", lambda path: path.name)
    assert problems() == []


def test_a_call_that_is_not_an_execute_is_left_alone(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    good = tmp_path / "good.py"
    good.write_text('"""A file."""\n\n\ndef shout(name):\n    return print(f"{name}")\n')
    monkeypatch.setattr(check_sql, "package_files", lambda: [good])
    monkeypatch.setattr(check_sql, "where", lambda path: path.name)
    assert problems() == []
