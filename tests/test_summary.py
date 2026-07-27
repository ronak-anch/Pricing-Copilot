from unittest.mock import patch

from domain.kpi_models import KPIResult
from domain.prompt_models import ExecutiveSummary
from summary import ClaudeExecutiveSummaryService, generate_executive_summary


def make_result(**overrides) -> KPIResult:
    defaults = dict(
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
    defaults.update(overrides)
    return KPIResult(**defaults)


def test_generate_executive_summary_delegates_to_service():
    expected = ExecutiveSummary(text="summary text", model="claude-opus-4-8", stop_reason="end_turn")

    with patch.object(ClaudeExecutiveSummaryService, "generate", return_value=expected) as mock_generate:
        result = generate_executive_summary(make_result())

    assert result is expected
    mock_generate.assert_called_once()


def test_generate_executive_summary_passes_through_configuration():
    expected = ExecutiveSummary(text="summary text", model="claude-sonnet-5", stop_reason="end_turn")
    captured_builders = []

    original_init = ClaudeExecutiveSummaryService.__init__

    def capturing_init(self, *args, **kwargs):
        captured_builders.append(kwargs.get("prompt_builder"))
        original_init(self, *args, **kwargs)

    with (
        patch.object(ClaudeExecutiveSummaryService, "__init__", capturing_init),
        patch.object(ClaudeExecutiveSummaryService, "generate", return_value=expected),
    ):
        generate_executive_summary(
            make_result(),
            target_audience="CFO",
            tone="direct",
            max_words=100,
            model="claude-sonnet-5",
        )

    builder = captured_builders[0]
    assert builder.target_audience == "CFO"
    assert builder.tone == "direct"
    assert builder.max_words == 100
