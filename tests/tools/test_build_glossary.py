from pathlib import Path

import pytest

from holdtrim.tools import build_glossary
from holdtrim.tools.build_glossary import TERMS, missing_from_source, render


def test_the_written_glossary_is_current() -> None:
    assert build_glossary.main(["--check"]) == 0


def test_every_term_still_appears_in_the_source() -> None:
    assert missing_from_source() == []


def test_the_glossary_defines_the_words_that_are_not_guessable() -> None:
    for term in ("index", "underload", "tare", "notoc"):
        assert term in TERMS


def test_the_terms_come_out_in_order() -> None:
    text = render()
    assert text.index("**arm**") < text.index("**index**")
    assert text.index("**index**") < text.index("**underload**")


def test_a_term_the_source_forgot_is_reported(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(TERMS, "flux capacitance", "not a real thing")
    assert missing_from_source() == ["flux capacitance"]


def test_writing_the_glossary_puts_it_where_asked(tmp_path: Path) -> None:
    out = tmp_path / "deep" / "glossary.md"
    assert build_glossary.main(["--out", str(out)]) == 0
    assert out.read_text(encoding="utf-8") == render()


def test_a_glossary_that_was_never_written_fails_the_check(tmp_path: Path) -> None:
    assert build_glossary.main(["--check", "--out", str(tmp_path / "nothing.md")]) == 1


def test_a_stale_glossary_fails_the_check(tmp_path: Path) -> None:
    out = tmp_path / "glossary.md"
    out.write_text("out of date", encoding="utf-8")
    assert build_glossary.main(["--check", "--out", str(out)]) == 1
