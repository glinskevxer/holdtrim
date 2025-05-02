from decimal import Decimal

import pytest

from holdtrim.errors import DataError
from holdtrim.model.danger import DangerousGoods


def entry(**changes: object) -> DangerousGoods:
    fields: dict[str, object] = {
        "un_number": 1263,
        "proper_shipping_name": "Paint",
        "hazard_class": "3",
        "packages": 4,
        "net_quantity": Decimal("5.000"),
        "unit": "L",
        "packing_group": "II",
        "packing_instruction": "364",
    }
    fields.update(changes)
    return DangerousGoods(**fields)  # type: ignore[arg-type]


def test_a_un_number_outside_the_list_is_refused() -> None:
    with pytest.raises(DataError, match="is not a UN number"):
        entry(un_number=9999)


def test_an_entry_with_no_shipping_name_is_refused() -> None:
    with pytest.raises(DataError, match="no proper shipping name"):
        entry(proper_shipping_name="  ")


def test_a_class_that_is_not_one_is_refused() -> None:
    with pytest.raises(DataError, match="not a hazard class"):
        entry(hazard_class="12")


def test_a_bare_class_one_is_refused_because_it_needs_a_division() -> None:
    with pytest.raises(DataError, match="not a hazard class"):
        entry(hazard_class="1")


def test_an_explosive_division_carries_its_compatibility_group() -> None:
    explosive = entry(hazard_class="1.4G", packing_group="")
    assert explosive.explosive
    assert explosive.division == "4G"
    assert explosive.compatibility_group == "G"


def test_anything_that_is_not_class_one_has_no_compatibility_group() -> None:
    assert entry().compatibility_group == ""


def test_the_primary_class_drops_the_division() -> None:
    assert entry(hazard_class="2.1", packing_group="").primary_class == "2"
    assert entry(hazard_class="2.1", packing_group="").division == "1"


def test_a_gas_with_a_packing_group_is_refused() -> None:
    with pytest.raises(DataError, match="class 2 has no packing group"):
        entry(hazard_class="2.1", packing_group="II")


def test_a_radioactive_entry_with_a_packing_group_is_refused() -> None:
    with pytest.raises(DataError, match="class 7 has no packing group"):
        entry(hazard_class="7", packing_group="II", transport_index=Decimal("0.4"))


def test_a_packing_group_that_is_not_one_is_refused() -> None:
    with pytest.raises(DataError, match="is not a packing group"):
        entry(packing_group="IV")


def test_a_subsidiary_risk_that_is_not_a_class_is_refused() -> None:
    with pytest.raises(DataError, match="not a subsidiary risk"):
        entry(subsidiary_risks=("corrosive",))


def test_the_risks_read_primary_first() -> None:
    assert entry(subsidiary_risks=("8",)).all_risks == ("3", "8")


def test_an_entry_with_no_packages_is_refused() -> None:
    with pytest.raises(DataError, match="has no packages"):
        entry(packages=0)


def test_an_entry_with_no_quantity_is_refused() -> None:
    with pytest.raises(DataError, match="no quantity in a package"):
        entry(net_quantity=Decimal("0"))


def test_a_unit_that_is_not_on_a_declaration_is_refused() -> None:
    with pytest.raises(DataError, match="not a quantity unit"):
        entry(unit="tonnes")


def test_radioactive_material_needs_a_transport_index() -> None:
    with pytest.raises(DataError, match="no transport index"):
        entry(hazard_class="7", packing_group="")


def test_a_negative_transport_index_is_refused() -> None:
    with pytest.raises(DataError, match="negative transport index"):
        entry(transport_index=Decimal("-1"))


def test_radioactive_material_reads_as_radioactive() -> None:
    hot = entry(hazard_class="7", packing_group="", transport_index=Decimal("0.4"), unit="TBq")
    assert hot.radioactive
    assert hot.transport_index == Decimal("0.4")


def test_the_packages_add_up() -> None:
    assert entry(packages=4, net_quantity=Decimal("5.000")).total_quantity == Decimal("20.000")


def test_the_label_is_the_way_it_is_written_on_the_package() -> None:
    assert entry().label == "UN 1263"


def test_an_entry_describes_itself_for_the_notice() -> None:
    assert entry().describe() == "UN 1263 Paint 3 PG II 4 x 5.000 L"


def test_an_entry_with_no_packing_group_leaves_it_out_of_the_line() -> None:
    line = entry(hazard_class="2.1", packing_group="", unit="kg").describe()
    assert line == "UN 1263 Paint 2.1 4 x 5.000 kg"
