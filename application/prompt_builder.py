"""Application layer: builds the executive-summary prompt from a KPIResult.

This is the only place that knows how to turn `KPIResult` fields into
the exact wording sent to an LLM. It has no dependency on any LLM SDK —
it only produces the prompt text.
"""

from __future__ import annotations

from domain.kpi_models import KPIResult
from domain.prompt_models import ExecutiveSummaryPrompt

_NOT_AVAILABLE = "not available"


def _format_currency(value: float | None) -> str:
    if value is None:
        return _NOT_AVAILABLE
    return f"${value:,.2f}"


def _format_number(value: float | None) -> str:
    if value is None:
        return _NOT_AVAILABLE
    return f"{value:,.2f}"


def _format_percent(value: float | None) -> str:
    if value is None:
        return _NOT_AVAILABLE
    return f"{value * 100:.2f}%"


def _format_count(value: int) -> str:
    return f"{value:,}"


class ExecutiveSummaryPromptBuilder:
    """Builds an LLM prompt that turns a `KPIResult` into an executive summary.

    Args:
        target_audience: Who the summary is written for.
        tone: The tone the summary should be written in.
        max_words: Hard word-count ceiling stated in the prompt.

    Raises:
        ValueError: If `max_words` is not positive.
    """

    def __init__(
        self,
        target_audience: str = "Pricing Director",
        tone: str = "professional",
        max_words: int = 250,
    ) -> None:
        if max_words <= 0:
            raise ValueError(f"max_words must be positive, got {max_words}.")
        self.target_audience = target_audience
        self.tone = tone
        self.max_words = max_words

    def build(self, result: KPIResult) -> ExecutiveSummaryPrompt:
        """Build the prompt for `result`.

        Every figure in the returned prompt comes from `result` — the
        builder never inserts a sample or placeholder number.
        """
        return ExecutiveSummaryPrompt(
            system_prompt=self._build_system_prompt(),
            user_prompt=self._build_user_prompt(result),
        )

    def _build_system_prompt(self) -> str:
        return (
            f"You are a senior insurance pricing analyst preparing a briefing for a "
            f"{self.target_audience}. Write in a {self.tone} tone suitable for an executive "
            "audience.\n\n"
            "Ground rules:\n"
            "- Use only the KPI figures given in the user message. Never invent, estimate, "
            "guess, or infer any number, trend, or comparison that is not explicitly provided.\n"
            "- If a figure is marked 'not available', state plainly that it is not available "
            "for this period — do not substitute a guess and do not omit it silently.\n"
            "- Do not fabricate context such as prior-period comparisons, market benchmarks, "
            "or causes for the results unless that context is explicitly supplied.\n"
            f"- Keep the summary to at most {self.max_words} words."
        )

    def _build_user_prompt(self, result: KPIResult) -> str:
        lines = [
            "Here are this period's pricing KPIs for a single book of business:",
            "",
            f"- Policy count: {_format_count(result.policy_count)}",
            f"- Premium: {_format_currency(result.total_premium)}",
            f"- Exposure: {_format_number(result.total_exposure)}",
            f"- Incurred losses: {_format_currency(result.total_losses)}",
            f"- Claim count: {_format_count(result.claim_count)}",
            f"- Loss ratio: {_format_percent(result.loss_ratio)}",
            f"- Frequency: {_format_percent(result.frequency)}",
            f"- Severity: {_format_currency(result.severity)}",
            f"- Average premium: {_format_currency(result.average_premium)}",
            f"- Burning cost: {_format_currency(result.burning_cost)}",
            "",
            "Using only the figures above, write an executive summary of this book's pricing "
            f"performance for the {self.target_audience}. Maximum {self.max_words} words.",
        ]
        return "\n".join(lines)
