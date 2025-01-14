import pytest

from holdtrim.errors import (
    BookError,
    DataError,
    DuplicateError,
    HoldtrimError,
    IdentifierError,
    LimitError,
    NotFoundError,
    RuleError,
    StateError,
    UnitError,
)


def test_every_error_descends_from_the_package_base() -> None:
    for cls in (
        DataError,
        UnitError,
        IdentifierError,
        NotFoundError,
        DuplicateError,
        StateError,
        RuleError,
        LimitError,
        BookError,
    ):
        assert issubclass(cls, HoldtrimError)


def test_unit_and_identifier_errors_are_both_data_errors() -> None:
    assert issubclass(UnitError, DataError)
    assert issubclass(IdentifierError, DataError)


def test_limit_exceeded_is_a_rule_violation() -> None:
    assert issubclass(LimitError, RuleError)


def test_codes_are_distinct_across_the_hierarchy() -> None:
    classes: list[type[HoldtrimError]] = [
        HoldtrimError,
        DataError,
        UnitError,
        IdentifierError,
        NotFoundError,
        DuplicateError,
        StateError,
        RuleError,
        LimitError,
        BookError,
    ]
    codes = [cls.code for cls in classes]
    assert len(set(codes)) == len(codes)


def test_the_message_is_the_string_form() -> None:
    err = NotFoundError("no tail OY-JAF in the fleet")
    assert str(err) == "no tail OY-JAF in the fleet"
    assert err.message == "no tail OY-JAF in the fleet"


def test_limit_exceeded_reports_how_far_over() -> None:
    err = LimitError("zero fuel weight over structural", limit=20800, actual=21150)
    assert err.limit == 20800
    assert err.actual == 21150
    assert err.over_by == 350


def test_a_figure_inside_the_limit_is_over_by_nothing() -> None:
    err = LimitError("held for reporting", limit=20800, actual=20000)
    assert err.over_by == 0


def test_errors_can_be_caught_by_the_base_class() -> None:
    with pytest.raises(HoldtrimError):
        raise UnitError("negative kilos")
