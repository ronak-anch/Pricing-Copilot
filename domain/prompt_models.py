"""Domain layer: framework-agnostic representation of an LLM prompt.

No dependency on any specific LLM SDK — just a system/user prompt pair
and the two shapes callers commonly need it in.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ExecutiveSummaryPrompt:
    """A prompt that asks an LLM to turn KPIs into an executive summary.

    Attributes:
        system_prompt: Role, tone, audience, and the anti-hallucination
            ground rules the model must follow.
        user_prompt: The KPI figures themselves plus the concrete ask.
    """

    system_prompt: str
    user_prompt: str

    def as_messages(self) -> list[dict[str, str]]:
        """Chat-style message list containing just the user turn.

        The system prompt is kept separate (`system_prompt`) rather than
        folded into this list because most chat APIs — including
        Anthropic's — take system instructions as a distinct top-level
        parameter, not a message with role "system".
        """
        return [{"role": "user", "content": self.user_prompt}]

    def combined(self) -> str:
        """Single flattened string, for tools that take one prompt blob."""
        return f"{self.system_prompt}\n\n{self.user_prompt}"
