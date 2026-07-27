import pytest

from application.claude_summary_service import ClaudeExecutiveSummaryService
from application.prompt_builder import ExecutiveSummaryPromptBuilder
from domain.kpi_models import KPIResult
from domain.prompt_models import ExecutiveSummary, ExecutiveSummaryRefusedError


class _StubTextBlock:
    def __init__(self, text: str) -> None:
        self.type = "text"
        self.text = text


class _StubThinkingBlock:
    def __init__(self, thinking: str = "") -> None:
        self.type = "thinking"
        self.thinking = thinking


class _StubMessage:
    def __init__(self, content, stop_reason="end_turn", model="claude-opus-4-8"):
        self.content = content
        self.stop_reason = stop_reason
        self.model = model


class _StubMessagesResource:
    def __init__(self, response=None):
        self.response = response
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return self.response


class _StubAnthropicClient:
    def __init__(self, response=None):
        self.messages = _StubMessagesResource(response=response)


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


def test_generate_returns_executive_summary_from_text_block():
    stub_client = _StubAnthropicClient(
        response=_StubMessage(content=[_StubTextBlock("Loss ratio is healthy at 48%.")])
    )
    service = ClaudeExecutiveSummaryService(client=stub_client)

    summary = service.generate(make_result())

    assert isinstance(summary, ExecutiveSummary)
    assert summary.text == "Loss ratio is healthy at 48%."
    assert summary.model == "claude-opus-4-8"
    assert summary.stop_reason == "end_turn"


def test_generate_concatenates_multiple_text_blocks_and_skips_thinking():
    stub_client = _StubAnthropicClient(
        response=_StubMessage(
            content=[
                _StubThinkingBlock("internal reasoning, never shown"),
                _StubTextBlock("Part one. "),
                _StubTextBlock("Part two."),
            ]
        )
    )
    service = ClaudeExecutiveSummaryService(client=stub_client)

    summary = service.generate(make_result())

    assert summary.text == "Part one. Part two."


def test_generate_uses_default_model_and_adaptive_thinking():
    stub_client = _StubAnthropicClient(response=_StubMessage(content=[_StubTextBlock("summary")]))
    service = ClaudeExecutiveSummaryService(client=stub_client)

    service.generate(make_result())

    call = stub_client.messages.calls[0]
    assert call["model"] == "claude-opus-4-8"
    assert call["thinking"] == {"type": "adaptive"}


def test_generate_respects_custom_model_and_max_tokens():
    stub_client = _StubAnthropicClient(response=_StubMessage(content=[_StubTextBlock("summary")], model="claude-sonnet-5"))
    service = ClaudeExecutiveSummaryService(client=stub_client, model="claude-sonnet-5", max_tokens=512)

    summary = service.generate(make_result())

    call = stub_client.messages.calls[0]
    assert call["model"] == "claude-sonnet-5"
    assert call["max_tokens"] == 512
    assert summary.model == "claude-sonnet-5"


def test_generate_sends_prompt_system_and_user_content():
    stub_client = _StubAnthropicClient(response=_StubMessage(content=[_StubTextBlock("summary")]))
    builder = ExecutiveSummaryPromptBuilder(target_audience="CFO", tone="direct", max_words=100)
    service = ClaudeExecutiveSummaryService(client=stub_client, prompt_builder=builder)

    service.generate(make_result())

    call = stub_client.messages.calls[0]
    assert "CFO" in call["system"]
    assert call["messages"] == [{"role": "user", "content": call["messages"][0]["content"]}]
    assert "Policy count: 100" in call["messages"][0]["content"]


def test_generate_raises_on_refusal_stop_reason():
    stub_client = _StubAnthropicClient(response=_StubMessage(content=[], stop_reason="refusal"))
    service = ClaudeExecutiveSummaryService(client=stub_client)

    with pytest.raises(ExecutiveSummaryRefusedError):
        service.generate(make_result())


def test_generate_from_prompt_bypasses_the_configured_builder():
    stub_client = _StubAnthropicClient(response=_StubMessage(content=[_StubTextBlock("summary")]))
    service = ClaudeExecutiveSummaryService(client=stub_client)
    from domain.prompt_models import ExecutiveSummaryPrompt

    custom_prompt = ExecutiveSummaryPrompt(system_prompt="SYSTEM", user_prompt="USER")
    service.generate_from_prompt(custom_prompt)

    call = stub_client.messages.calls[0]
    assert call["system"] == "SYSTEM"
    assert call["messages"] == [{"role": "user", "content": "USER"}]
