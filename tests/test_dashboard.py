import plotly.graph_objects as go
import pytest
from streamlit.testing.v1 import AppTest

from dashboard import build_kpi_dashboard_figure
from domain.kpi_models import KPIResult


def make_result(**overrides) -> KPIResult:
    defaults = dict(
        policy_count=1000,
        total_premium=1_250_000.0,
        total_exposure=980.0,
        total_losses=725_000.0,
        claim_count=150,
        loss_ratio=0.58,
        frequency=0.153,
        severity=4833.33,
        average_premium=1250.0,
        burning_cost=739.80,
    )
    defaults.update(overrides)
    return KPIResult(**defaults)


def all_annotation_text(fig: go.Figure) -> str:
    return " ".join(str(a.text) for a in fig.layout.annotations)


def test_returns_a_plotly_figure():
    fig = build_kpi_dashboard_figure(make_result())
    assert isinstance(fig, go.Figure)


def test_creates_one_card_per_kpi_with_label_value_and_caption():
    fig = build_kpi_dashboard_figure(make_result())

    # 7 KPIs x (card rect + accent line) = 14 shapes
    assert len(fig.layout.shapes) == 14
    # 7 KPIs x (label + value + caption) = 21 annotations
    assert len(fig.layout.annotations) == 21

    text = all_annotation_text(fig)
    for label in ("PREMIUM", "EXPOSURE", "LOSS RATIO", "FREQUENCY", "SEVERITY", "AVERAGE PREMIUM", "BURNING COST"):
        assert label in text


def test_values_rendered_come_from_the_kpi_result_not_hardcoded():
    result = make_result(total_premium=9_999_999.0, claim_count=42, policy_count=7)
    fig = build_kpi_dashboard_figure(result)
    text = all_annotation_text(fig)

    assert "10.00M" in text  # total_premium compact format
    assert "42" in text  # claim_count caption
    assert "7" in text  # policy_count caption


def test_different_result_produces_different_rendered_values():
    fig_a = build_kpi_dashboard_figure(make_result(total_premium=100_000.0))
    fig_b = build_kpi_dashboard_figure(make_result(total_premium=500_000.0))

    assert all_annotation_text(fig_a) != all_annotation_text(fig_b)


def test_none_ratios_render_as_not_available():
    result = make_result(loss_ratio=None, frequency=None, severity=None, average_premium=None, burning_cost=None)
    fig = build_kpi_dashboard_figure(result)
    text = all_annotation_text(fig)
    assert text.count("N/A") == 5


def test_columns_parameter_controls_row_wrapping():
    fig_4col = build_kpi_dashboard_figure(make_result(), columns=4)
    fig_7col = build_kpi_dashboard_figure(make_result(), columns=7)

    # 7 tiles over 4 columns needs 2 rows; over 7 columns needs 1 row.
    assert fig_4col.layout.height > fig_7col.layout.height


def test_rejects_non_positive_columns():
    with pytest.raises(ValueError):
        build_kpi_dashboard_figure(make_result(), columns=0)


def test_figure_is_configured_for_responsive_layout():
    fig = build_kpi_dashboard_figure(make_result())
    assert fig.layout.autosize is True
    assert fig.layout.xaxis.visible is False
    assert fig.layout.yaxis.visible is False


def _render_dashboard_for_app_test() -> None:
    from dashboard import render_kpi_dashboard
    from domain.kpi_models import KPIResult

    result = KPIResult(
        policy_count=100,
        total_premium=250_000.0,
        total_exposure=95.0,
        total_losses=120_000.0,
        claim_count=20,
        loss_ratio=0.48,
        frequency=0.21,
        severity=6000.0,
        average_premium=2500.0,
        burning_cost=1263.16,
    )
    render_kpi_dashboard(result)


def test_render_kpi_dashboard_renders_without_exception_in_streamlit():
    at = AppTest.from_function(_render_dashboard_for_app_test)
    at.run()

    assert not at.exception
    assert len(at.get("plotly_chart")) == 1
