"""Application layer: computes pricing KPIs from a dataframe.

This is the only place that knows how to turn raw premium/exposure/loss
columns into the domain's `KPIResult`. It has no dependency on
Streamlit.
"""

from __future__ import annotations

import pandas as pd

from domain.kpi_models import KPIResult


class KPICalculator:
    """Computes pricing KPIs (loss ratio, frequency, severity, etc.).

    Args:
        premium_column: Name of the column holding premium amounts.
        exposure_column: Name of the column holding exposure amounts.
        loss_column: Name of the column holding incurred loss amounts.
        claim_count_column: Name of a column holding a per-row claim
            count. When `None` (the default), claim count is instead
            derived as the number of rows with a strictly positive
            loss value.

    Raises:
        ValueError: At construction time this is not checked (the
            dataframe isn't known yet); `calculate()` raises
            `KeyError` if `premium_column`, `exposure_column`, or
            `loss_column` is missing from the dataframe it is given.
    """

    def __init__(
        self,
        premium_column: str = "premium",
        exposure_column: str = "exposure",
        loss_column: str = "loss",
        claim_count_column: str | None = None,
    ) -> None:
        self.premium_column = premium_column
        self.exposure_column = exposure_column
        self.loss_column = loss_column
        self.claim_count_column = claim_count_column

    def calculate(self, df: pd.DataFrame) -> KPIResult:
        """Compute KPIs for `df` and return a `KPIResult`.

        Non-numeric values in the premium/exposure/loss/claim-count
        columns are treated as missing (coerced to NaN) and excluded
        from sums, consistent with how `application.validators` treats
        the same data.

        Raises:
            TypeError: If `df` is not a pandas DataFrame.
            KeyError: If `premium_column`, `exposure_column`, or
                `loss_column` is not present in `df`.
        """
        if not isinstance(df, pd.DataFrame):
            raise TypeError(f"calculate() expects a pandas DataFrame, got {type(df).__name__}.")

        for column in (self.premium_column, self.exposure_column, self.loss_column):
            if column not in df.columns:
                raise KeyError(f"Required column '{column}' not found in the dataframe.")

        premium = pd.to_numeric(df[self.premium_column], errors="coerce")
        exposure = pd.to_numeric(df[self.exposure_column], errors="coerce")
        losses = pd.to_numeric(df[self.loss_column], errors="coerce")

        total_premium = float(premium.sum(skipna=True))
        total_exposure = float(exposure.sum(skipna=True))
        total_losses = float(losses.sum(skipna=True))
        policy_count = len(df)

        if self.claim_count_column is not None:
            if self.claim_count_column not in df.columns:
                raise KeyError(f"Claim-count column '{self.claim_count_column}' not found in the dataframe.")
            claim_counts = pd.to_numeric(df[self.claim_count_column], errors="coerce")
            claim_count = int(claim_counts.sum(skipna=True))
        else:
            claim_count = int((losses > 0).sum())

        return KPIResult(
            policy_count=policy_count,
            total_premium=total_premium,
            total_exposure=total_exposure,
            total_losses=total_losses,
            claim_count=claim_count,
            loss_ratio=_safe_divide(total_losses, total_premium),
            frequency=_safe_divide(claim_count, total_exposure),
            severity=_safe_divide(total_losses, claim_count),
            average_premium=_safe_divide(total_premium, policy_count),
            burning_cost=_safe_divide(total_losses, total_exposure),
        )


def _safe_divide(numerator: float, denominator: float) -> float | None:
    """`numerator / denominator`, or `None` when the denominator is zero."""
    if denominator == 0:
        return None
    return numerator / denominator
