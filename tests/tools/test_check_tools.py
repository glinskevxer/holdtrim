import pytest

from holdtrim.tools import check_tools
from holdtrim.tools.check_tools import (
    expected_test,
    named_in_workflow,
    problems,
    runnable,
    tool_names,
)
from holdtrim.tools.sources import TESTS


def test_every_check_is_runnable_run_and_tested() -> None:
    assert problems() == []


def test_the_check_passes_over_this_package() -> None:
    assert check_tools.main() == 0


def test_the_tools_are_found_by_name() -> None:
    names = tool_names()
    assert "check_layers" in names
    assert "__init__" not in names


def test_every_tool_that_ci_calls_has_a_main() -> None:
    for name in tool_names():
        if name in check_tools.NOT_RUNNABLE:
            continue
        assert runnable(name)


def test_the_shared_source_reader_is_not_expected_to_run() -> None:
    assert "sources" in check_tools.NOT_RUNNABLE


def test_the_workflow_is_searched_by_module_name() -> None:
    assert named_in_workflow("run: python -m holdtrim.tools.check_layers\n", "check_layers")
    assert not named_in_workflow("run: python -m holdtrim.tools.check_layers\n", "check_sql")


def test_the_expected_test_is_where_it_has_to_be() -> None:
    assert expected_test("check_layers").name == "test_check_layers.py"
    assert expected_test("check_layers").exists()


def test_a_tool_that_is_never_run_is_reported(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(check_tools, "tool_names", lambda: ["check_layers"])
    monkeypatch.setattr(check_tools, "named_in_workflow", lambda _text, _name: False)
    assert "is never run by the workflow" in problems()[0]


def test_a_tool_with_no_test_is_reported(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(check_tools, "tool_names", lambda: ["check_layers"])
    monkeypatch.setattr(check_tools, "expected_test", lambda name: TESTS / f"{name}.py")
    assert any("has no test file" in problem for problem in problems())


def test_the_smoke_test_is_not_expected_in_the_lint_job() -> None:
    assert "smoke" in check_tools.NOT_A_CHECK
