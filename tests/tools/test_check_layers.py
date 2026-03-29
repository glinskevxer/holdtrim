import ast

import pytest

from holdtrim.tools import check_layers
from holdtrim.tools.check_layers import imports, layer_of, problems


def test_nothing_in_the_package_imports_upwards() -> None:
    assert problems() == []


def test_the_check_passes_over_this_package() -> None:
    assert check_layers.main() == 0


def test_the_bottom_of_the_stack_is_layer_zero() -> None:
    assert layer_of("holdtrim.units") == 0
    assert layer_of("holdtrim.errors") == 0


def test_a_module_takes_the_layer_of_its_package() -> None:
    assert layer_of("holdtrim.model.station") == layer_of("holdtrim.model")
    assert layer_of("holdtrim.cli.main") == layer_of("holdtrim.cli")


def test_the_model_sits_below_the_arithmetic_that_reads_it() -> None:
    assert layer_of("holdtrim.model.fuel") < layer_of("holdtrim.balance.index")


def test_the_store_sits_above_everything_it_stores() -> None:
    assert layer_of("holdtrim.store.fleet") > layer_of("holdtrim.model.aircraft")
    assert layer_of("holdtrim.store.plans") > layer_of("holdtrim.plan.loadplan")


def test_the_command_line_sits_near_the_top() -> None:
    assert layer_of("holdtrim.cli.main") > layer_of("holdtrim.office")


def test_a_module_nobody_has_placed_is_refused() -> None:
    with pytest.raises(KeyError):
        layer_of("elsewhere.entirely")


def test_the_imports_of_a_file_are_found() -> None:
    tree = ast.parse(
        "import holdtrim.units\n"
        "from holdtrim.model.station import Station\n"
        "from decimal import Decimal\n"
    )
    assert imports(tree) == ["holdtrim.units", "holdtrim.model.station"]


def test_an_import_from_outside_the_package_is_ignored() -> None:
    assert imports(ast.parse("import json\nfrom pathlib import Path\n")) == []
