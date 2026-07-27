import pytest

from domain.kpi_models import KPIResult
from domain.prompt_models import ExecutiveSummaryPrompt
from prompts import build_executive_summary_prompt


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


def test_build_executive_summary_prompt_returns_expected_type():
    prompt = build_executive_summary_prompt(make_result())
    assert isinstance(prompt, ExecutiveSummaryPrompt)


def test_build_executive_summary_prompt_uses_defaults():
    prompt = build_executive_summary_prompt(make_result())
    assert "Pricing Director" in prompt.system_prompt
    assert "professional" in prompt.system_prompt
    assert "250 words" in prompt.system_prompt


def test_build_executive_summary_prompt_respects_overrides():
    prompt = build_executive_summary_prompt(
        make_result(),
        target_audience="CFO",
        tone="direct",
        max_words=150,
    )
    assert "CFO" in prompt.system_prompt
    assert "direct" in prompt.system_prompt
    assert "150 words" in prompt.system_prompt


def test_build_executive_summary_prompt_raises_for_invalid_max_words():
    with pytest.raises(ValueError):
        build_executive_summary_prompt(make_result(), max_words=0)
