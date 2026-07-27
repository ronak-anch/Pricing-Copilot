import pytest

from application.prompt_builder import ExecutiveSummaryPromptBuilder
from domain.kpi_models import KPIResult


def make_result(**overrides) -> KPIResult:
    defaults = dict(
        policy_count=12480,
        total_premium=8_240_500.75,
        total_exposure=11832.5,
        total_losses=4_910_200.10,
        claim_count=612,
        loss_ratio=0.5959,
        frequency=0.05173,
        severity=8023.20,
        average_premium=660.30,
        burning_cost=414.98,
    )
    defaults.update(overrides)
    return KPIResult(**defaults)


def test_rejects_non_positive_max_words():
    with pytest.raises(ValueError):
        ExecutiveSummaryPromptBuilder(max_words=0)
    with pytest.raises(ValueError):
        ExecutiveSummaryPromptBuilder(max_words=-10)


def test_system_prompt_states_audience_tone_and_word_limit():
    builder = ExecutiveSummaryPromptBuilder(target_audience="Pricing Director", tone="professional", max_words=250)
    prompt = builder.build(make_result())

    assert "Pricing Director" in prompt.system_prompt
    assert "professional" in prompt.system_prompt
    assert "250 words" in prompt.system_prompt


def test_system_prompt_forbids_hallucination():
    builder = ExecutiveSummaryPromptBuilder()
    prompt = builder.build(make_result())

    lowered = prompt.system_prompt.lower()
    assert "never invent" in lowered
    assert "not available" in lowered
    assert "do not fabricate" in lowered


def test_custom_audience_tone_and_word_limit_are_respected():
    builder = ExecutiveSummaryPromptBuilder(target_audience="Chief Underwriting Officer", tone="candid", max_words=100)
    prompt = builder.build(make_result())

    assert "Chief Underwriting Officer" in prompt.system_prompt
    assert "Chief Underwriting Officer" in prompt.user_prompt
    assert "candid" in prompt.system_prompt
    assert "100 words" in prompt.system_prompt
    assert "100" in prompt.user_prompt


def test_user_prompt_contains_every_kpi_figure_from_the_result():
    result = make_result()
    prompt = ExecutiveSummaryPromptBuilder().build(result)

    assert "12,480" in prompt.user_prompt
    assert "$8,240,500.75" in prompt.user_prompt
    assert "11,832.50" in prompt.user_prompt
    assert "$4,910,200.10" in prompt.user_prompt
    assert "612" in prompt.user_prompt
    assert "59.59%" in prompt.user_prompt
    assert "5.17%" in prompt.user_prompt
    assert "$8,023.20" in prompt.user_prompt
    assert "$660.30" in prompt.user_prompt
    assert "$414.98" in prompt.user_prompt


def test_different_results_produce_different_user_prompts():
    prompt_a = ExecutiveSummaryPromptBuilder().build(make_result(total_premium=100_000.0))
    prompt_b = ExecutiveSummaryPromptBuilder().build(make_result(total_premium=500_000.0))
    assert prompt_a.user_prompt != prompt_b.user_prompt


def test_none_ratios_render_as_not_available_not_a_guess():
    result = make_result(loss_ratio=None, frequency=None, severity=None, average_premium=None, burning_cost=None)
    prompt = ExecutiveSummaryPromptBuilder().build(result)

    assert prompt.user_prompt.count("not available") == 5


def test_user_prompt_ends_with_the_concrete_task():
    prompt = ExecutiveSummaryPromptBuilder(target_audience="Pricing Director", max_words=250).build(make_result())
    assert "write an executive summary" in prompt.user_prompt.lower()
    assert prompt.user_prompt.strip().endswith("Maximum 250 words.")
