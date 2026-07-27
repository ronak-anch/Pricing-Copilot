"""AI prompt module: turns KPI output into an executive-summary prompt.

Public API:
    ExecutiveSummaryPrompt        - re-exported from the domain layer.
    ExecutiveSummaryPromptBuilder - re-exported from the application layer.
    build_executive_summary_prompt - convenience function:
        KPIResult -> ExecutiveSummaryPrompt.

This module only *builds the prompt* — it does not call an LLM. Feed the
result's `.system_prompt` / `.user_prompt` (or `.combined()`) to whichever
model you use.
"""

from __future__ import annotations

from application.prompt_builder import ExecutiveSummaryPromptBuilder
from domain.kpi_models import KPIResult
from domain.prompt_models import ExecutiveSummaryPrompt

__all__ = ["ExecutiveSummaryPrompt", "ExecutiveSummaryPromptBuilder", "build_executive_summary_prompt"]


def build_executive_summary_prompt(
    result: KPIResult,
    target_audience: str = "Pricing Director",
    tone: str = "professional",
    max_words: int = 250,
) -> ExecutiveSummaryPrompt:
    """Build the executive-summary prompt for `result`.

    Thin convenience wrapper around `ExecutiveSummaryPromptBuilder`,
    exposed at module level so callers don't need to know the
    application layer exists.
    """
    builder = ExecutiveSummaryPromptBuilder(target_audience=target_audience, tone=tone, max_words=max_words)
    return builder.build(result)
