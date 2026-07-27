"""Executive summary module: calls Claude to turn KPI output into an executive summary.

Public API:
    ExecutiveSummary            - re-exported from the domain layer.
    ExecutiveSummaryRefusedError - re-exported from the domain layer.
    ClaudeExecutiveSummaryService - re-exported from the application layer.
    generate_executive_summary  - convenience function: KPIResult -> ExecutiveSummary.

This module wires `prompts.py` (prompt construction) to a live call
against the Claude Messages API. It requires Anthropic credentials to
be available in the environment (`ANTHROPIC_API_KEY`, `ANTHROPIC_AUTH_TOKEN`,
or an `ant auth login` profile) — none are hardcoded here.
"""

from __future__ import annotations

from application.claude_summary_service import DEFAULT_MODEL, ClaudeExecutiveSummaryService
from application.prompt_builder import ExecutiveSummaryPromptBuilder
from domain.kpi_models import KPIResult
from domain.prompt_models import ExecutiveSummary, ExecutiveSummaryRefusedError

__all__ = [
    "ExecutiveSummary",
    "ExecutiveSummaryRefusedError",
    "ClaudeExecutiveSummaryService",
    "generate_executive_summary",
]


def generate_executive_summary(
    result: KPIResult,
    target_audience: str = "Pricing Director",
    tone: str = "professional",
    max_words: int = 250,
    model: str = DEFAULT_MODEL,
) -> ExecutiveSummary:
    """Generate an executive summary of `result` by calling Claude.

    Thin convenience wrapper around `ClaudeExecutiveSummaryService`,
    exposed at module level so callers don't need to know the
    application layer exists.

    Raises:
        ExecutiveSummaryRefusedError: If Claude declines to respond.
        anthropic.APIStatusError / anthropic.APIConnectionError: On
            API or network failures — propagated unchanged from the SDK.
    """
    service = ClaudeExecutiveSummaryService(
        model=model,
        prompt_builder=ExecutiveSummaryPromptBuilder(target_audience=target_audience, tone=tone, max_words=max_words),
    )
    return service.generate(result)
