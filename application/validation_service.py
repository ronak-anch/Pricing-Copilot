"""Application layer: orchestrates validators into a single ValidationResult.

This is the one place that knows about *all* the checks and how to
assemble their findings into the domain's `ValidationResult`. It is the
only entry point the presentation layer (Streamlit) should call.
"""

from __future__ import annotations

import pandas as pd

from application.validators import (
    DuplicateRowsValidator,
    InvalidExposureValidator,
    MissingValuesValidator,
    NegativePremiumValidator,
    Validator,
)
from domain.models import ValidationResult


class ValidationService:
    """Runs the standard set of dataframe validation checks.

    Args:
        premium_column: Name of the column holding premium amounts.
        exposure_column: Name of the column holding exposure amounts.
        max_exposure: Optional upper bound for a valid exposure value.
        extra_validators: Additional validators to run alongside the
            standard set, e.g. domain-specific checks supplied by a
            caller.
    """

    def __init__(
        self,
        premium_column: str = "premium",
        exposure_column: str = "exposure",
        max_exposure: float | None = None,
        extra_validators: tuple[Validator, ...] = (),
    ) -> None:
        self._missing_values_validator = MissingValuesValidator()
        self._duplicate_rows_validator = DuplicateRowsValidator()
        self._negative_premium_validator = NegativePremiumValidator(premium_column=premium_column)
        self._invalid_exposure_validator = InvalidExposureValidator(
            exposure_column=exposure_column, max_exposure=max_exposure
        )
        self._extra_validators = extra_validators

    def validate(self, df: pd.DataFrame) -> ValidationResult:
        """Validate `df` and return the aggregated result.

        Raises:
            TypeError: If `df` is not a pandas DataFrame.
        """
        if not isinstance(df, pd.DataFrame):
            raise TypeError(f"validate() expects a pandas DataFrame, got {type(df).__name__}.")

        missing_values = self._missing_values_validator.missing_counts(df)
        duplicate_rows = self._duplicate_rows_validator.duplicate_row_indices(df)
        negative_premium_rows = self._negative_premium_validator.negative_premium_indices(df)
        invalid_exposure_rows = self._invalid_exposure_validator.invalid_exposure_indices(df)

        issues = (
            self._missing_values_validator.validate(df)
            + self._duplicate_rows_validator.validate(df)
            + self._negative_premium_validator.validate(df)
            + self._invalid_exposure_validator.validate(df)
        )
        for validator in self._extra_validators:
            issues += validator.validate(df)

        return ValidationResult(
            row_count=len(df),
            missing_values=missing_values,
            duplicate_rows=duplicate_rows,
            negative_premium_rows=negative_premium_rows,
            invalid_exposure_rows=invalid_exposure_rows,
            issues=issues,
        )
