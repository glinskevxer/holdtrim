from pathlib import Path

import pytest

from holdtrim.store.migrations import MIGRATIONS
from holdtrim.tools import check_migrations
from holdtrim.tools.check_migrations import current, fingerprint, problems, recorded, render


def test_no_migration_has_been_edited_since_it_was_accepted() -> None:
    assert problems() == []


def test_the_check_passes_over_this_package() -> None:
    assert check_migrations.main([]) == 0


def test_a_fingerprint_is_stable() -> None:
    assert fingerprint(1) == fingerprint(1)
    assert len(fingerprint(1)) == 16


def test_two_migrations_fingerprint_differently() -> None:
    assert fingerprint(1) != fingerprint(2)


def test_every_migration_has_a_fingerprint_recorded() -> None:
    assert set(recorded()) == set(current())


def test_the_file_lists_one_line_a_migration() -> None:
    lines = [line for line in render().splitlines() if not line.startswith("#")]
    assert len(lines) == len(MIGRATIONS)


def test_an_edited_migration_is_reported(monkeypatch: pytest.MonkeyPatch) -> None:
    changed = dict(current())
    changed[1] = "0000000000000000"
    monkeypatch.setattr(check_migrations, "current", lambda: changed)
    assert "has been edited" in problems()[0]


def test_a_new_migration_with_no_fingerprint_is_reported(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(check_migrations, "recorded", lambda: {1: fingerprint(1)})
    assert any("has no fingerprint" in problem for problem in problems())


def test_a_fingerprint_for_a_migration_that_is_gone_is_reported(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    held = dict(recorded())
    held[99] = "0000000000000000"
    monkeypatch.setattr(check_migrations, "recorded", lambda: held)
    assert any("not in the list any more" in problem for problem in problems())


def test_a_book_with_no_fingerprints_at_all_is_reported(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(check_migrations, "recorded", dict)
    assert "have ever been written" in problems()[0]


def test_writing_the_fingerprints_puts_them_where_asked(tmp_path: Path) -> None:
    out = tmp_path / "migrations.txt"
    assert check_migrations.main(["--write", "--out", str(out)]) == 0
    assert out.read_text(encoding="utf-8") == render()
