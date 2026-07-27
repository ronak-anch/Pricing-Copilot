import pandas as pd
import pytest

from application.validation_service import ValidationService
from domain.models import Severity, ValidationIssue


def test_validate_rejects_non_dataframe_input():
    service = ValidationService()
    with pytest.raises(TypeError):
        service.validate({"premium": [1, 2]})


def test_validate_returns_valid_result_for_clean_data():
    df = pd.DataFrame({"premium": [100, 200], "exposure": [1, 0.5]})
    service = ValidationService()
    result = service.validate(df)

    assert result.row_count == 2
    assert result.is_valid
    assert result.missing_values == {}
    assert result.duplicate_rows == ()
    assert result.negative_premium_rows == ()
    assert result.invalid_exposure_rows == ()
    assert result.issues == ()


def test_validate_aggregates_findings_across_all_checks():
    df = pd.DataFrame(
        {
            "premium": [100, 100, -50, None],
            "exposure": [1, 1, 1, 0],
        }
    )
    service = ValidationService()
    result = service.validate(df)

    assert result.row_count == 4
    assert result.missing_values == {"premium": 1}
    assert result.duplicate_rows == (1,)
    assert result.negative_premium_rows == (2,)
    assert result.invalid_exposure_rows == (3,)
    assert not result.is_valid
    # negative premium and invalid exposure are errors; missing/duplicate are warnings
    assert len(result.error_messages) == 2
    assert len(result.warning_messages) == 2


def test_validate_uses_custom_column_names():
    df = pd.DataFrame({"gross_premium": [-10], "policy_exposure": [0]})
    service = ValidationService(premium_column="gross_premium", exposure_column="policy_exposure")
    result = service.validate(df)

    assert result.negative_premium_rows == (0,)
    assert result.invalid_exposure_rows == (0,)


def test_validate_applies_max_exposure_ceiling():
    df = pd.DataFrame({"premium": [100, 100], "exposure": [1, 400]})
    service = ValidationService(max_exposure=365)
    result = service.validate(df)
    assert result.invalid_exposure_rows == (1,)


def test_validate_runs_extra_validators():
    class AlwaysFailsValidator:
        def validate(self, df: pd.DataFrame) -> tuple[ValidationIssue, ...]:
            return (
                ValidationIssue(
                    check="custom_rule",
                    severity=Severity.ERROR,
                    message="custom rule violated",
                ),
            )

    df = pd.DataFrame({"premium": [100], "exposure": [1]})
    service = ValidationService(extra_validators=(AlwaysFailsValidator(),))
    result = service.validate(df)

    assert not result.is_valid
    assert "custom rule violated" in result.error_messages


def test_validate_on_empty_dataframe_reports_zero_rows_and_is_valid():
    df = pd.DataFrame({"premium": [], "exposure": []})
    service = ValidationService()
    result = service.validate(df)

    assert result.row_count == 0
    assert result.is_valid
