import pandas as pd
import pytest

from domain.kpi_models import KPIResult
from kpis import calculate_kpis


def test_calculate_kpis_returns_kpi_result_instance():
    df = pd.DataFrame({"premium": [100], "exposure": [1], "loss": [0]})
    result = calculate_kpis(df)
    assert isinstance(result, KPIResult)


def test_calculate_kpis_computes_expected_values():
    df = pd.DataFrame(
        {
            "premium": [100, 200, 300],
            "exposure": [1, 1, 1],
            "loss": [0, 50, 150],
        }
    )
    result = calculate_kpis(df)

    assert result.total_premium == pytest.approx(600.0)
    assert result.total_exposure == pytest.approx(3.0)
    assert result.total_losses == pytest.approx(200.0)
    assert result.claim_count == 2
    assert result.loss_ratio == pytest.approx(200.0 / 600.0)
    assert result.frequency == pytest.approx(2.0 / 3.0)
    assert result.severity == pytest.approx(100.0)
    assert result.average_premium == pytest.approx(200.0)
    assert result.burning_cost == pytest.approx(200.0 / 3.0)


def test_calculate_kpis_supports_custom_columns():
    df = pd.DataFrame(
        {
            "gross_premium": [100, 200],
            "policy_exposure": [1, 2],
            "incurred_loss": [10, 20],
            "num_claims": [1, 1],
        }
    )
    result = calculate_kpis(
        df,
        premium_column="gross_premium",
        exposure_column="policy_exposure",
        loss_column="incurred_loss",
        claim_count_column="num_claims",
    )

    assert result.total_premium == pytest.approx(300.0)
    assert result.claim_count == 2


def test_calculate_kpis_raises_key_error_for_missing_column():
    df = pd.DataFrame({"exposure": [1], "loss": [0]})
    with pytest.raises(KeyError):
        calculate_kpis(df)
