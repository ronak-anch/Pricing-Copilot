import pandas as pd
import pytest

from application.validators import (
    DuplicateRowsValidator,
    InvalidExposureValidator,
    MissingValuesValidator,
    NegativePremiumValidator,
)
from domain.models import Severity


class TestMissingValuesValidator:
    def test_no_issues_when_no_missing_values(self):
        df = pd.DataFrame({"premium": [100, 200], "exposure": [1, 1]})
        validator = MissingValuesValidator()
        assert validator.validate(df) == ()
        assert validator.missing_counts(df) == {}

    def test_flags_column_with_missing_values(self):
        df = pd.DataFrame({"premium": [100, None, None], "exposure": [1, 1, 1]})
        validator = MissingValuesValidator()
        issues = validator.validate(df)
        assert len(issues) == 1
        assert issues[0].severity is Severity.WARNING
        assert issues[0].columns == ("premium",)
        assert "2 missing" in issues[0].message
        assert validator.missing_counts(df) == {"premium": 2}

    def test_flags_multiple_columns_independently(self):
        df = pd.DataFrame({"premium": [None, 200], "exposure": [1, None]})
        validator = MissingValuesValidator()
        counts = validator.missing_counts(df)
        assert counts == {"premium": 1, "exposure": 1}
        assert len(validator.validate(df)) == 2


class TestDuplicateRowsValidator:
    def test_no_issues_when_all_rows_unique(self):
        df = pd.DataFrame({"premium": [100, 200], "exposure": [1, 2]})
        validator = DuplicateRowsValidator()
        assert validator.validate(df) == ()
        assert validator.duplicate_row_indices(df) == ()

    def test_flags_exact_duplicate_rows_keeping_first_occurrence(self):
        df = pd.DataFrame({"premium": [100, 100, 200], "exposure": [1, 1, 2]})
        validator = DuplicateRowsValidator()
        duplicate_indices = validator.duplicate_row_indices(df)
        assert duplicate_indices == (1,)
        issues = validator.validate(df)
        assert len(issues) == 1
        assert issues[0].severity is Severity.WARNING
        assert issues[0].row_indices == (1,)

    def test_flags_all_but_first_when_more_than_two_duplicates(self):
        df = pd.DataFrame({"premium": [100, 100, 100], "exposure": [1, 1, 1]})
        validator = DuplicateRowsValidator()
        assert validator.duplicate_row_indices(df) == (1, 2)


class TestNegativePremiumValidator:
    def test_no_issues_when_all_premiums_non_negative(self):
        df = pd.DataFrame({"premium": [0, 100, 200]})
        validator = NegativePremiumValidator()
        assert validator.validate(df) == ()
        assert validator.negative_premium_indices(df) == ()

    def test_flags_negative_premium_rows(self):
        df = pd.DataFrame({"premium": [100, -50, -1]})
        validator = NegativePremiumValidator()
        indices = validator.negative_premium_indices(df)
        assert indices == (1, 2)
        issues = validator.validate(df)
        assert len(issues) == 1
        assert issues[0].severity is Severity.ERROR
        assert issues[0].columns == ("premium",)

    def test_ignores_missing_premium_values_without_crashing(self):
        df = pd.DataFrame({"premium": [100, None, -5]})
        validator = NegativePremiumValidator()
        assert validator.negative_premium_indices(df) == (2,)

    def test_warns_when_premium_column_missing(self):
        df = pd.DataFrame({"exposure": [1, 2]})
        validator = NegativePremiumValidator(premium_column="premium")
        issues = validator.validate(df)
        assert len(issues) == 1
        assert issues[0].severity is Severity.WARNING
        assert validator.negative_premium_indices(df) == ()

    def test_respects_custom_premium_column_name(self):
        df = pd.DataFrame({"gross_premium": [-10, 20]})
        validator = NegativePremiumValidator(premium_column="gross_premium")
        assert validator.negative_premium_indices(df) == (0,)

    def test_handles_non_numeric_premium_values(self):
        df = pd.DataFrame({"premium": ["abc", -5, 100]})
        validator = NegativePremiumValidator()
        assert validator.negative_premium_indices(df) == (1,)


class TestInvalidExposureValidator:
    def test_no_issues_when_all_exposure_valid(self):
        df = pd.DataFrame({"exposure": [0.5, 1, 1.0]})
        validator = InvalidExposureValidator()
        assert validator.validate(df) == ()
        assert validator.invalid_exposure_indices(df) == ()

    def test_flags_zero_and_negative_exposure(self):
        df = pd.DataFrame({"exposure": [1, 0, -1]})
        validator = InvalidExposureValidator()
        assert validator.invalid_exposure_indices(df) == (1, 2)
        issues = validator.validate(df)
        assert issues[0].severity is Severity.ERROR

    def test_flags_missing_exposure(self):
        df = pd.DataFrame({"exposure": [1, None, 2]})
        validator = InvalidExposureValidator()
        assert validator.invalid_exposure_indices(df) == (1,)

    def test_flags_non_numeric_exposure(self):
        df = pd.DataFrame({"exposure": [1, "not-a-number", 2]})
        validator = InvalidExposureValidator()
        assert validator.invalid_exposure_indices(df) == (1,)

    def test_warns_when_exposure_column_missing(self):
        df = pd.DataFrame({"premium": [1, 2]})
        validator = InvalidExposureValidator(exposure_column="exposure")
        issues = validator.validate(df)
        assert len(issues) == 1
        assert issues[0].severity is Severity.WARNING

    def test_respects_max_exposure_ceiling(self):
        df = pd.DataFrame({"exposure": [1, 366, 100]})
        validator = InvalidExposureValidator(max_exposure=365)
        assert validator.invalid_exposure_indices(df) == (1,)

    def test_no_ceiling_applied_when_max_exposure_not_set(self):
        df = pd.DataFrame({"exposure": [1, 10000]})
        validator = InvalidExposureValidator()
        assert validator.invalid_exposure_indices(df) == ()


@pytest.fixture
def clean_dataframe() -> pd.DataFrame:
    return pd.DataFrame({"premium": [100, 200, 300], "exposure": [1, 1, 0.5]})


def test_all_validators_are_no_ops_on_a_clean_dataframe(clean_dataframe):
    validators = [
        MissingValuesValidator(),
        DuplicateRowsValidator(),
        NegativePremiumValidator(),
        InvalidExposureValidator(),
    ]
    for validator in validators:
        assert validator.validate(clean_dataframe) == ()
