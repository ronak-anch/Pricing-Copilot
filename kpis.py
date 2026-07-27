"""KPIs module: computes pricing KPIs from a pandas DataFrame.

Public API:
    KPIResult      - re-exported from the domain layer.
    KPICalculator  - re-exported from the application layer.
    calculate_kpis - convenience function: DataFrame -> KPIResult.

KPIs computed: total premium, total exposure, loss ratio, frequency,
severity, average premium, and burning cost. See `domain.kpi_models.KPIResult`
for the exact definition of each field.
"""

from __future__ import annotations

import pandas as pd

from application.kpi_calculator import KPICalculator
from domain.kpi_models import KPIResult

__all__ = ["KPIResult", "KPICalculator", "calculate_kpis"]


def calculate_kpis(
    df: pd.DataFrame,
    premium_column: str = "premium",
    exposure_column: str = "exposure",
    loss_column: str = "loss",
    claim_count_column: str | None = None,
) -> KPIResult:
    """Calculate pricing KPIs for `df` and return a `KPIResult`.

    Thin convenience wrapper around `KPICalculator`, exposed at module
    level so callers don't need to know the application layer exists.
    """
    calculator = KPICalculator(
        premium_column=premium_column,
        exposure_column=exposure_column,
        loss_column=loss_column,
        claim_count_column=claim_count_column,
    )
    return calculator.calculate(df)
