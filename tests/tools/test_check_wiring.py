from holdtrim.tools import check_wiring
from holdtrim.tools.check_wiring import edges, problems, reachable, roots


def test_every_module_is_reached_from_something_that_runs() -> None:
    assert problems() == []


def test_the_check_passes_over_this_package() -> None:
    assert check_wiring.main() == 0


def test_the_graph_has_an_edge_for_every_module() -> None:
    graph = edges()
    assert "holdtrim.units" in graph
    assert "holdtrim.errors" in graph["holdtrim.units"]


def test_the_command_line_reaches_the_store() -> None:
    assert "holdtrim.store.fleet" in reachable(edges(), ("holdtrim.cli.main",))


def test_the_command_line_reaches_the_dangerous_goods_screen() -> None:
    assert "holdtrim.danger.screen" in reachable(edges(), ("holdtrim.cli.main",))


def test_the_units_do_not_reach_the_command_line() -> None:
    assert "holdtrim.cli.main" not in reachable(edges(), ("holdtrim.units",))


def test_the_roots_include_the_checks_ci_runs() -> None:
    assert "holdtrim.tools.check_layers" in roots()
    assert "holdtrim.cli.main" in roots()


def test_a_module_nothing_imports_is_not_reachable() -> None:
    graph = {"a": {"b"}, "b": set(), "orphan": set()}
    assert reachable(graph, ("a",)) == {"a", "b"}


def test_a_cycle_does_not_loop_forever() -> None:
    graph = {"a": {"b"}, "b": {"a"}}
    assert reachable(graph, ("a",)) == {"a", "b"}
