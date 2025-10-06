from pathlib import Path

from holdtrim.tools import check_docstrings, sources


def test_the_package_has_a_docstring_everywhere_it_should() -> None:
    assert check_docstrings.problems() == []


def test_the_check_passes_and_says_so(capsys: object) -> None:
    assert check_docstrings.main() == 0


def test_a_module_with_no_docstring_is_reported(tmp_path: Path, monkeypatch: object) -> None:
    bad = tmp_path / "bad.py"
    bad.write_text("def loud():\n    return 1\n")
    import pytest

    monkeypatch.setattr(sources, "PACKAGE", tmp_path)  # type: ignore[attr-defined]
    monkeypatch.setattr(  # type: ignore[attr-defined]
        check_docstrings, "package_files", lambda: [bad]
    )
    monkeypatch.setattr(check_docstrings, "where", lambda path: path.name)  # type: ignore[attr-defined]
    found = check_docstrings.problems()
    assert any("no docstring" in problem for problem in found)
    assert pytest is not None


def test_a_private_helper_needs_no_docstring(tmp_path: Path, monkeypatch: object) -> None:
    good = tmp_path / "good.py"
    good.write_text(
        '"""A file."""\n\n\ndef _quiet():\n    return 1\n\n\n'
        "class Thing:\n"
        '    """A thing."""\n\n'
        "    def __str__(self):\n"
        "        return 'thing'\n"
    )
    monkeypatch.setattr(  # type: ignore[attr-defined]
        check_docstrings, "package_files", lambda: [good]
    )
    monkeypatch.setattr(check_docstrings, "where", lambda path: path.name)  # type: ignore[attr-defined]
    assert check_docstrings.problems() == []
