from pathlib import Path

from holdtrim.tools import sources


def test_the_package_files_are_found() -> None:
    files = sources.package_files()
    assert any(path.name == "units.py" for path in files)
    assert all(path.suffix == ".py" for path in files)


def test_no_bytecode_directory_creeps_in() -> None:
    assert all("__pycache__" not in path.parts for path in sources.package_files())


def test_the_test_files_are_found() -> None:
    assert any(path.name == "test_units.py" for path in sources.test_files())


def test_a_module_name_is_dotted() -> None:
    path = sources.PACKAGE / "model" / "station.py"
    assert sources.module_name(path) == "holdtrim.model.station"


def test_a_package_init_names_the_package() -> None:
    path = sources.PACKAGE / "model" / "__init__.py"
    assert sources.module_name(path) == "holdtrim.model"


def test_a_path_reports_relative_to_the_repository() -> None:
    path = sources.PACKAGE / "units.py"
    assert sources.where(path) == "src/holdtrim/units.py"


def test_a_path_outside_the_repository_reports_whole() -> None:
    assert sources.where(Path("/somewhere/else.py")) == "/somewhere/else.py"


def test_a_file_parses_into_definitions() -> None:
    tree = sources.parsed(sources.PACKAGE / "units.py")
    names = [getattr(node, "name", "") for node in sources.definitions(tree)]
    assert "to_kilos" in names


def test_a_clean_report_returns_zero(capsys: object) -> None:
    assert sources.report([], checked=3, what="things") == 0


def test_a_report_with_problems_returns_one(capsys: object) -> None:
    assert sources.report(["something"], checked=3, what="things") == 1
