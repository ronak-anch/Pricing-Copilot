"""Application layer: individual, independently testable validation rules.

Each validator implements the `Validator` protocol: given a dataframe it
returns the tuple of `ValidationIssue`s it found. Validators never touch
Streamlit and never import each other; they only depend on the domain
layer and pandas.
"""

from __future__ import annotations

from typing import Protocol

import pandas as pd

from domain.models import Severity, ValidationIssue


class Validator(Protocol):
    """A single, independent validation rule."""

    def validate(self, df: pd.DataFrame) -> tuple[ValidationIssue, ...]:
        ...


class MissingValuesValidator:
    """Flags columns that contain missing (NaN/None/NaT) values."""

    check_name = "missing_values"

    def validate(self, df: pd.DataFrame) -> tuple[ValidationIssue, ...]:
        missing_counts = df.isna().sum()
        missing_counts = missing_counts[missing_counts > 0]
        if missing_counts.empty:
            return ()

        issues = []
        for column, count in missing_counts.items():
            issues.append(
                ValidationIssue(
                    check=self.check_name,
                    severity=Severity.WARNING,
                    message=f"Column '{column}' has {int(count)} missing value(s).",
                    columns=(str(column),),
                )
            )
        return tuple(issues)

    def missing_counts(self, df: pd.DataFrame) -> dict[str, int]:
        """Column -> missing-value count, restricted to affected columns."""
        counts = df.isna().sum()
        counts = counts[counts > 0]
        return {str(column): int(count) for column, count in counts.items()}


class DuplicateRowsValidator:
    """Flags rows that are exact duplicates of an earlier row."""

    check_name = "duplicate_rows"

    def validate(self, df: pd.DataFrame) -> tuple[ValidationIssue, ...]:
        duplicate_rows = self.duplicate_row_indices(df)
        if not duplicate_rows:
            return ()

        return (
            ValidationIssue(
                check=self.check_name,
                severity=Severity.WARNING,
                message=f"Found {len(duplicate_rows)} duplicate row(s).",
                row_indices=duplicate_rows,
            ),
        )

    def duplicate_row_indices(self, df: pd.DataFrame) -> tuple[int, ...]:
        mask = df.duplicated(keep="first")
        return tuple(df.index[mask])


class NegativePremiumValidator:
    """Flags rows where the premium column is present but negative."""

    check_name = "negative_premium"

    def __init__(self, premium_column: str = "premium") -> None:
        self.premium_column = premium_column

    def validate(self, df: pd.DataFrame) -> tuple[ValidationIssue, ...]:
        if self.premium_column not in df.columns:
            return (
                ValidationIssue(
                    check=self.check_name,
                    severity=Severity.WARNING,
                    message=f"Premium column '{self.premium_column}' not found; skipped negative-premium check.",
                    columns=(self.premium_column,),
                ),
            )

        negative_rows = self.negative_premium_indices(df)
        if not negative_rows:
            return ()

        return (
            ValidationIssue(
                check=self.check_name,
                severity=Severity.ERROR,
                message=f"Found {len(negative_rows)} row(s) with negative premium.",
                row_indices=negative_rows,
                columns=(self.premium_column,),
            ),
        )

    def negative_premium_indices(self, df: pd.DataFrame) -> tuple[int, ...]:
        if self.premium_column not in df.columns:
            return ()
        premium = pd.to_numeric(df[self.premium_column], errors="coerce")
        mask = premium < 0
        return tuple(df.index[mask.fillna(False)])


class InvalidExposureValidator:
    """Flags rows where exposure is missing, non-numeric, or not strictly positive.

    Optionally also flags exposure above `max_exposure`, when a domain
    ceiling (e.g. a policy cannot exceed 365 days) is supplied.
    """

    check_name = "invalid_exposure"

    def __init__(self, exposure_column: str = "exposure", max_exposure: float | None = None) -> None:
        self.exposure_column = exposure_column
        self.max_exposure = max_exposure

    def validate(self, df: pd.DataFrame) -> tuple[ValidationIssue, ...]:
        if self.exposure_column not in df.columns:
            return (
                ValidationIssue(
                    check=self.check_name,
                    severity=Severity.WARNING,
                    message=f"Exposure column '{self.exposure_column}' not found; skipped invalid-exposure check.",
                    columns=(self.exposure_column,),
                ),
            )

        invalid_rows = self.invalid_exposure_indices(df)
        if not invalid_rows:
            return ()

        return (
            ValidationIssue(
                check=self.check_name,
                severity=Severity.ERROR,
                message=f"Found {len(invalid_rows)} row(s) with invalid exposure "
                f"(missing, non-numeric, or not strictly positive"
                f"{f', or above {self.max_exposure}' if self.max_exposure is not None else ''}).",
                row_indices=invalid_rows,
                columns=(self.exposure_column,),
            ),
        )

    def invalid_exposure_indices(self, df: pd.DataFrame) -> tuple[int, ...]:
        if self.exposure_column not in df.columns:
            return ()
        exposure = pd.to_numeric(df[self.exposure_column], errors="coerce")
        mask = exposure.isna() | (exposure <= 0)
        if self.max_exposure is not None:
            mask = mask | (exposure > self.max_exposure)
        return tuple(df.index[mask])
