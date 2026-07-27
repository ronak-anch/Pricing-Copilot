"""Executive summary module: calls Claude to turn KPI output into an executive summary.

Public API:
    ExecutiveSummary            - re-exported from the domain layer.
    ExecutiveSummaryRefusedError - re-exported from the domain layer.
    ClaudeExecutiveSummaryService - re-exported from the application layer.
    generate_executive_summary  - convenience function: KPIResult -> ExecutiveSummary.
    main - CLI demo (CSV -> KPIs -> printed summary), run via
        `python summary.py [path/to/policies.csv]`.

This module wires `prompts.py` (prompt construction) to a live call
against the Claude Messages API. It requires Anthropic credentials to
be available in the environment (`ANTHROPIC_API_KEY`, `ANTHROPIC_AUTH_TOKEN`,
or an `ant auth login` profile) — none are hardcoded here.
"""

from __future__ import annotations

import argparse

import anthropic
import pandas as pd
from dotenv import load_dotenv

from application.claude_summary_service import DEFAULT_MODEL, ClaudeExecutiveSummaryService
from application.prompt_builder import ExecutiveSummaryPromptBuilder
from domain.kpi_models import KPIResult
from domain.prompt_models import ExecutiveSummary, ExecutiveSummaryRefusedError
from kpis import calculate_kpis

__all__ = [
    "ExecutiveSummary",
    "ExecutiveSummaryRefusedError",
    "ClaudeExecutiveSummaryService",
    "generate_executive_summary",
    "main",
]

DEFAULT_CSV_PATH = "Inputs/sample_policies.csv"


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


def main() -> None:
    """CLI demo: compute KPIs from a CSV and print Claude's executive summary.

    Usage: `python summary.py [path/to/policies.csv]` — defaults to
    `Inputs/sample_policies.csv`. Requires an Anthropic credential
    (`ANTHROPIC_API_KEY`, `ANTHROPIC_AUTH_TOKEN`, or an `ant auth login`
    profile) to be available in the environment. If a `.env` file exists
    in the current or a parent directory, it is loaded automatically —
    this makes the credential available regardless of how the script is
    launched (VS Code's Run button, a fresh terminal, etc.), unlike
    relying on an editor's own `.env` auto-loading.

    `--prompt-only` skips the API call entirely: it just prints the
    prompt Claude would receive, so it can be pasted into the free
    claude.ai chat instead — no API key and no API cost required.
    """
    load_dotenv()

    parser = argparse.ArgumentParser(description="Compute KPIs from a CSV and generate an executive summary.")
    parser.add_argument(
        "csv_path", nargs="?", default=DEFAULT_CSV_PATH, help=f"Path to the policies CSV (default: {DEFAULT_CSV_PATH})"
    )
    parser.add_argument(
        "--prompt-only",
        action="store_true",
        help="Print the prompt instead of calling the API — no key or cost required. Paste the output into claude.ai.",
    )
    args = parser.parse_args()

    df = pd.read_csv(args.csv_path)
    result = calculate_kpis(df)

    print(f"Computed KPIs from {args.csv_path} ({result.policy_count} policies).")

    if args.prompt_only:
        prompt = ExecutiveSummaryPromptBuilder().build(result)
        print("\n--- Paste everything below into claude.ai (no API key needed) ---\n")
        print(prompt.combined())
        return

    print("Calling Claude for an executive summary...\n")

    try:
        executive_summary = generate_executive_summary(result)
    except ExecutiveSummaryRefusedError as exc:
        print(str(exc))
        return
    except anthropic.APIConnectionError as exc:
        print(f"Could not reach the Claude API: {exc}")
        return
    except anthropic.APIStatusError as exc:
        print(f"Claude API request failed ({exc.status_code}): {exc.message}")
        if exc.status_code == 401:
            print("Set ANTHROPIC_API_KEY (or run `ant auth login`) and try again.")
        return
    except TypeError as exc:
        if "authentication" not in str(exc).lower():
            raise
        print("No Anthropic credentials found. Set ANTHROPIC_API_KEY (or run `ant auth login`) and try again.")
        return

    print(f"--- Executive summary ({executive_summary.model}) ---")
    print(executive_summary.text)


if __name__ == "__main__":
    main()
