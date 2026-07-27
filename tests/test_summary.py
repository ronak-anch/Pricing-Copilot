import sys
from unittest.mock import patch

import anthropic
import httpx
import pandas as pd
import pytest

import summary
from domain.kpi_models import KPIResult
from domain.prompt_models import ExecutiveSummary, ExecutiveSummaryRefusedError
from summary import ClaudeExecutiveSummaryService, generate_executive_summary, main


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


@pytest.fixture
def sample_csv(tmp_path):
    path = tmp_path / "policies.csv"
    pd.DataFrame({"premium": [100, 200], "exposure": [1, 1], "loss": [0, 50]}).to_csv(path, index=False)
    return path


def test_main_prints_the_generated_summary(sample_csv, monkeypatch, capsys):
    expected = ExecutiveSummary(text="All KPIs look healthy.", model="claude-opus-4-8", stop_reason="end_turn")
    monkeypatch.setattr(sys, "argv", ["summary.py", str(sample_csv)])

    with patch.object(summary, "generate_executive_summary", return_value=expected) as mock_generate:
        main()

    mock_generate.assert_called_once()
    output = capsys.readouterr().out
    assert "2 policies" in output
    assert "All KPIs look healthy." in output


def test_main_prompt_only_never_calls_the_api(sample_csv, monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["summary.py", str(sample_csv), "--prompt-only"])

    with patch.object(summary, "generate_executive_summary") as mock_generate:
        main()

    mock_generate.assert_not_called()
    output = capsys.readouterr().out
    assert "Paste everything below into claude.ai" in output
    assert "Policy count: 2" in output
    assert "Never invent" in output


def test_main_defaults_to_the_sample_csv_path(sample_csv, monkeypatch):
    expected = ExecutiveSummary(text="summary", model="claude-opus-4-8", stop_reason="end_turn")
    monkeypatch.setattr(sys, "argv", ["summary.py"])
    monkeypatch.setattr(summary, "DEFAULT_CSV_PATH", str(sample_csv))

    with (
        patch.object(summary, "generate_executive_summary", return_value=expected),
        patch.object(summary, "calculate_kpis", wraps=summary.calculate_kpis) as mock_calculate_kpis,
    ):
        main()

    mock_calculate_kpis.assert_called_once()


def test_main_handles_refusal_gracefully(sample_csv, monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["summary.py", str(sample_csv)])

    with patch.object(
        summary, "generate_executive_summary", side_effect=ExecutiveSummaryRefusedError("claude-opus-4-8")
    ):
        main()

    output = capsys.readouterr().out
    assert "declined" in output


def test_main_handles_authentication_error_gracefully(sample_csv, monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["summary.py", str(sample_csv)])
    request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    response = httpx.Response(status_code=401, request=request, json={"error": {"message": "invalid x-api-key"}})
    error = anthropic.AuthenticationError("invalid x-api-key", response=response, body=None)

    with patch.object(summary, "generate_executive_summary", side_effect=error):
        main()

    output = capsys.readouterr().out
    assert "401" in output
    assert "ANTHROPIC_API_KEY" in output


def test_main_handles_connection_error_gracefully(sample_csv, monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["summary.py", str(sample_csv)])
    request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    error = anthropic.APIConnectionError(request=request)

    with patch.object(summary, "generate_executive_summary", side_effect=error):
        main()

    output = capsys.readouterr().out
    assert "Could not reach the Claude API" in output


def test_main_handles_missing_credentials_gracefully(sample_csv, monkeypatch, capsys):
    """The SDK raises a bare TypeError (not AuthenticationError) when no
    credential source is configured at all — this is what a fresh machine
    with no ANTHROPIC_API_KEY / `ant auth login` hits."""
    monkeypatch.setattr(sys, "argv", ["summary.py", str(sample_csv)])
    error = TypeError(
        "Could not resolve authentication method. Expected one of api_key, auth_token, or credentials to be set."
    )

    with patch.object(summary, "generate_executive_summary", side_effect=error):
        main()

    output = capsys.readouterr().out
    assert "No Anthropic credentials found" in output


def test_main_reraises_unrelated_type_errors(sample_csv, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["summary.py", str(sample_csv)])

    with (
        patch.object(summary, "generate_executive_summary", side_effect=TypeError("unrelated bug")),
        pytest.raises(TypeError, match="unrelated bug"),
    ):
        main()
