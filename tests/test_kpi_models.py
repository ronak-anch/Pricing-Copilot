from domain.kpi_models import KPIResult


def make_result(**overrides) -> KPIResult:
    defaults = dict(
        policy_count=10,
        total_premium=1000.0,
        total_exposure=10.0,
        total_losses=500.0,
        claim_count=5,
        loss_ratio=0.5,
        frequency=0.5,
        severity=100.0,
        average_premium=100.0,
        burning_cost=50.0,
    )
    defaults.update(overrides)
    return KPIResult(**defaults)


def test_to_dict_contains_all_fields_with_expected_values():
    result = make_result()
    as_dict = result.to_dict()
    assert as_dict == {
        "policy_count": 10,
        "total_premium": 1000.0,
        "total_exposure": 10.0,
        "total_losses": 500.0,
        "claim_count": 5,
        "loss_ratio": 0.5,
        "frequency": 0.5,
        "severity": 100.0,
        "average_premium": 100.0,
        "burning_cost": 50.0,
    }


def test_ratio_fields_can_be_none():
    result = make_result(loss_ratio=None, frequency=None, severity=None, average_premium=None, burning_cost=None)
    assert result.to_dict()["loss_ratio"] is None
    assert result.to_dict()["severity"] is None
