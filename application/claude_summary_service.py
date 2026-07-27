"""Application layer: calls Claude to turn a KPIResult into an executive summary.

This is the only place that talks to the Anthropic SDK. It builds the
prompt via `ExecutiveSummaryPromptBuilder`, sends it to the Messages API,
and turns the response into the domain's `ExecutiveSummary`. SDK-level
errors (rate limits, connection failures, etc.) are not caught here —
they propagate as the SDK's own typed exceptions so callers can handle
them with the usual `except anthropic.RateLimitError` / `except
anthropic.APIStatusError` chain.
"""

from __future__ import annotations

import anthropic

from application.prompt_builder import ExecutiveSummaryPromptBuilder
from domain.kpi_models import KPIResult
from domain.prompt_models import ExecutiveSummary, ExecutiveSummaryPrompt, ExecutiveSummaryRefusedError

DEFAULT_MODEL = "claude-opus-4-8"
DEFAULT_MAX_TOKENS = 2048


class ClaudeExecutiveSummaryService:
    """Generates executive summaries from `KPIResult`s via the Claude API.

    Args:
        client: An Anthropic client (or a stand-in exposing the same
            `client.messages.create(...)` surface, for testing). Defaults
            to `anthropic.Anthropic()`, which resolves credentials from
            the environment (`ANTHROPIC_API_KEY`, `ANTHROPIC_AUTH_TOKEN`,
            or an `ant auth login` profile) — no key is hardcoded here.
        model: The Claude model to call.
        max_tokens: Output token ceiling, covering both the summary text
            and any thinking tokens.
        prompt_builder: Builder used by `generate()` to turn a `KPIResult`
            into a prompt. Configure audience/tone/word-limit here.
    """

    def __init__(
        self,
        client: anthropic.Anthropic | None = None,
        model: str = DEFAULT_MODEL,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        prompt_builder: ExecutiveSummaryPromptBuilder | None = None,
    ) -> None:
        self._client = client if client is not None else anthropic.Anthropic()
        self._model = model
        self._max_tokens = max_tokens
        self._prompt_builder = prompt_builder if prompt_builder is not None else ExecutiveSummaryPromptBuilder()

    def generate(self, result: KPIResult) -> ExecutiveSummary:
        """Build the prompt for `result` and generate its executive summary."""
        prompt = self._prompt_builder.build(result)
        return self.generate_from_prompt(prompt)

    def generate_from_prompt(self, prompt: ExecutiveSummaryPrompt) -> ExecutiveSummary:
        """Send an already-built prompt to Claude and return the summary.

        Raises:
            ExecutiveSummaryRefusedError: If Claude declines to respond
                (`stop_reason == "refusal"`).
        """
        response = self._client.messages.create(
            model=self._model,
            max_tokens=self._max_tokens,
            thinking={"type": "adaptive"},
            system=prompt.system_prompt,
            messages=prompt.as_messages(),
        )

        if response.stop_reason == "refusal":
            raise ExecutiveSummaryRefusedError(response.model)

        text = "".join(block.text for block in response.content if block.type == "text")
        return ExecutiveSummary(text=text, model=response.model, stop_reason=response.stop_reason)
