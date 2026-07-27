import pandas as pd
import pytest

from application.kpi_calculator import KPICalculator


def test_calculate_rejects_non_dataframe_input():
    calculator = KPICalculator()
    with pytest.raises(TypeError):
        calculator.calculate({"premium": [1, 2]})


def test_calculate_raises_when_premium_column_missing():
    df = pd.DataFrame({"exposure": [1], "loss": [0]})
    with pytest.raises(KeyError, match="premium"):
        KPICalculator().calculate(df)


def test_calculate_raises_when_exposure_column_missing():
    df = pd.DataFrame({"premium": [1], "loss": [0]})
    with pytest.raises(KeyError, match="exposure"):
        KPICalculator().calculate(df)


def test_calculate_raises_when_loss_column_missing():
    df = pd.DataFrame({"premium": [1], "exposure": [1]})
    with pytest.raises(KeyError, match="loss"):
        KPICalculator().calculate(df)


def test_calculate_raises_when_claim_count_column_missing():
    df = pd.DataFrame({"premium": [1], "exposure": [1], "loss": [0]})
    calculator = KPICalculator(claim_count_column="num_claims")
    with pytest.raises(KeyError, match="num_claims"):
        calculator.calculate(df)


def test_calculate_derives_claim_count_from_positive_losses_by_default():
    df = pd.DataFrame(
        {
            "premium": [100, 200, 300],
            "exposure": [1, 1, 1],
            "loss": [0, 50, 150],
        }
    )
    result = KPICalculator().calculate(df)

    assert result.policy_count == 3
    assert result.total_premium == pytest.approx(600.0)
    assert result.total_exposure == pytest.approx(3.0)
    assert result.total_losses == pytest.approx(200.0)
    assert result.claim_count == 2
    assert result.loss_ratio == pytest.approx(200.0 / 600.0)
    assert result.frequency == pytest.approx(2.0 / 3.0)
    assert result.severity == pytest.approx(100.0)
    assert result.average_premium == pytest.approx(200.0)
    assert result.burning_cost == pytest.approx(200.0 / 3.0)


def test_calculate_uses_explicit_claim_count_column_when_given():
    df = pd.DataFrame(
        {
            "premium": [100, 200, 300],
            "exposure": [1, 1, 1],
            "loss": [0, 50, 150],
            "num_claims": [0, 1, 2],
        }
    )
    calculator = KPICalculator(claim_count_column="num_claims")
    result = calculator.calculate(df)

    assert result.claim_count == 3
    assert result.frequency == pytest.approx(1.0)
    assert result.severity == pytest.approx(200.0 / 3.0)


def test_calculate_respects_custom_column_names():
    df = pd.DataFrame(
        {
            "gross_premium": [100, 200],
            "policy_exposure": [1, 2],
            "incurred_loss": [10, 20],
        }
    )
    calculator = KPICalculator(
        premium_column="gross_premium",
        exposure_column="policy_exposure",
        loss_column="incurred_loss",
    )
    result = calculator.calculate(df)

    assert result.total_premium == pytest.approx(300.0)
    assert result.total_exposure == pytest.approx(3.0)
    assert result.total_losses == pytest.approx(30.0)


def test_calculate_treats_non_numeric_values_as_missing():
    df = pd.DataFrame(
        {
            "premium": [100, "not-a-number", 200],
            "exposure": [1, 1, 1],
            "loss": [0, 0, 0],
        }
    )
    result = KPICalculator().calculate(df)
    assert result.total_premium == pytest.approx(300.0)


def test_calculate_returns_none_ratios_on_zero_denominators():
    df = pd.DataFrame({"premium": [0, 0], "exposure": [0, 0], "loss": [0, 0]})
    result = KPICalculator().calculate(df)

    assert result.total_premium == 0.0
    assert result.total_exposure == 0.0
    assert result.claim_count == 0
    assert result.loss_ratio is None
    assert result.frequency is None
    assert result.severity is None
    assert result.burning_cost is None
    # average_premium denominator is policy_count (2 rows), not premium/exposure
    assert result.average_premium == pytest.approx(0.0)


def test_calculate_on_empty_dataframe_returns_all_none_ratios():
    df = pd.DataFrame({"premium": [], "exposure": [], "loss": []})
    result = KPICalculator().calculate(df)

    assert result.policy_count == 0
    assert result.total_premium == 0.0
    assert result.claim_count == 0
    assert result.loss_ratio is None
    assert result.frequency is None
    assert result.severity is None
    assert result.average_premium is None
    assert result.burning_cost is None


def test_calculate_ignores_nan_values_in_sums():
    df = pd.DataFrame(
        {
            "premium": [100, None, 200],
            "exposure": [1, None, 1],
            "loss": [10, None, 20],
        }
    )
    result = KPICalculator().calculate(df)

    assert result.policy_count == 3
    assert result.total_premium == pytest.approx(300.0)
    assert result.total_exposure == pytest.approx(2.0)
    assert result.total_losses == pytest.approx(30.0)
