"""Domain layer: framework-agnostic entities for dataframe validation.

This module has no dependency on pandas, Streamlit, or any validator
implementation. It defines the vocabulary the rest of the application
speaks: what a validation issue looks like, and what the final result
of validating a dataframe looks like.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Severity(str, Enum):
    """How serious a single validation finding is."""

    ERROR = "error"
    WARNING = "warning"


@dataclass(frozen=True)
class ValidationIssue:
    """A single finding produced by one validation check.

    Attributes:
        check: Stable machine-readable name of the check that produced
            this issue (e.g. "negative_premium").
        severity: Whether this issue should block downstream processing
            (ERROR) or merely be surfaced to the user (WARNING).
        message: Human-readable description, safe to display as-is.
        row_indices: Original dataframe index labels affected by this
            issue, if the issue is row-scoped.
        columns: Column names affected by this issue, if the issue is
            column-scoped.
    """

    check: str
    severity: Severity
    message: str
    row_indices: tuple[int, ...] = field(default_factory=tuple)
    columns: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class ValidationResult:
    """Aggregate outcome of validating a dataframe.

    Attributes:
        row_count: Number of rows in the dataframe that was validated.
        missing_values: Mapping of column name -> count of missing
            (NaN/None) values, restricted to columns with at least one
            missing value.
        duplicate_rows: Index labels of rows that are exact duplicates
            of an earlier row.
        negative_premium_rows: Index labels of rows whose premium value
            is present but negative.
        invalid_exposure_rows: Index labels of rows whose exposure
            value is missing, non-numeric, or not strictly positive.
        issues: Every issue raised by every check, in the order the
            checks ran.
    """

    row_count: int
    missing_values: dict[str, int]
    duplicate_rows: tuple[int, ...]
    negative_premium_rows: tuple[int, ...]
    invalid_exposure_rows: tuple[int, ...]
    issues: tuple[ValidationIssue, ...]

    @property
    def warning_messages(self) -> tuple[str, ...]:
        """Messages for every issue of WARNING severity."""
        return tuple(issue.message for issue in self.issues if issue.severity is Severity.WARNING)

    @property
    def error_messages(self) -> tuple[str, ...]:
        """Messages for every issue of ERROR severity."""
        return tuple(issue.message for issue in self.issues if issue.severity is Severity.ERROR)

    @property
    def has_missing_values(self) -> bool:
        return bool(self.missing_values)

    @property
    def has_duplicate_rows(self) -> bool:
        return bool(self.duplicate_rows)

    @property
    def has_negative_premium(self) -> bool:
        return bool(self.negative_premium_rows)

    @property
    def has_invalid_exposure(self) -> bool:
        return bool(self.invalid_exposure_rows)

    @property
    def is_valid(self) -> bool:
        """True when no check raised an ERROR-severity issue.

        Rows with only WARNING-severity issues do not affect this flag.
        """
        return not self.error_messages

    def to_dict(self) -> dict[str, object]:
        """Plain-data representation, convenient for logging or display."""
        return {
            "row_count": self.row_count,
            "is_valid": self.is_valid,
            "missing_values": dict(self.missing_values),
            "duplicate_rows": list(self.duplicate_rows),
            "negative_premium_rows": list(self.negative_premium_rows),
            "invalid_exposure_rows": list(self.invalid_exposure_rows),
            "warnings": list(self.warning_messages),
            "errors": list(self.error_messages),
        }
