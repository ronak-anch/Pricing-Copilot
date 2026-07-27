from domain.models import Severity, ValidationIssue, ValidationResult


def make_result(**overrides) -> ValidationResult:
    defaults = dict(
        row_count=10,
        missing_values={},
        duplicate_rows=(),
        negative_premium_rows=(),
        invalid_exposure_rows=(),
        issues=(),
    )
    defaults.update(overrides)
    return ValidationResult(**defaults)


def test_is_valid_true_when_no_issues():
    result = make_result()
    assert result.is_valid
    assert result.error_messages == ()
    assert result.warning_messages == ()


def test_is_valid_false_when_error_issue_present():
    issue = ValidationIssue(check="negative_premium", severity=Severity.ERROR, message="bad")
    result = make_result(issues=(issue,))
    assert not result.is_valid
    assert result.error_messages == ("bad",)


def test_is_valid_true_when_only_warning_issues_present():
    issue = ValidationIssue(check="missing_values", severity=Severity.WARNING, message="heads up")
    result = make_result(issues=(issue,))
    assert result.is_valid
    assert result.warning_messages == ("heads up",)
    assert result.error_messages == ()


def test_has_flags_reflect_populated_fields():
    result = make_result(
        missing_values={"premium": 2},
        duplicate_rows=(1, 2),
        negative_premium_rows=(3,),
        invalid_exposure_rows=(4, 5),
    )
    assert result.has_missing_values
    assert result.has_duplicate_rows
    assert result.has_negative_premium
    assert result.has_invalid_exposure


def test_has_flags_false_when_empty():
    result = make_result()
    assert not result.has_missing_values
    assert not result.has_duplicate_rows
    assert not result.has_negative_premium
    assert not result.has_invalid_exposure


def test_to_dict_contains_expected_keys_and_values():
    issue = ValidationIssue(check="duplicate_rows", severity=Severity.WARNING, message="dupes found")
    result = make_result(duplicate_rows=(1,), issues=(issue,))
    as_dict = result.to_dict()
    assert as_dict["row_count"] == 10
    assert as_dict["is_valid"] is True
    assert as_dict["duplicate_rows"] == [1]
    assert as_dict["warnings"] == ["dupes found"]
    assert as_dict["errors"] == []
