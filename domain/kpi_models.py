"""Domain layer: framework-agnostic KPI result for a book of business.

No dependency on pandas or Streamlit — just the vocabulary of pricing
KPIs and how they relate to one another.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class KPIResult:
    """Aggregate pricing KPIs computed over a set of policy records.

    Ratio fields are `None` when their denominator is zero, rather than
    raising or silently producing `inf`/`nan`.

    Attributes:
        policy_count: Number of rows (policy records) the KPIs were
            computed over.
        total_premium: Sum of premium across all rows.
        total_exposure: Sum of exposure across all rows.
        total_losses: Sum of incurred losses across all rows.
        claim_count: Number of claims. Either the sum of a claim-count
            column, or, when none is supplied, the number of rows with
            a strictly positive loss.
        loss_ratio: total_losses / total_premium.
        frequency: claim_count / total_exposure — claims per unit of
            exposure.
        severity: total_losses / claim_count — average cost per claim.
        average_premium: total_premium / policy_count — average
            premium per policy.
        burning_cost: total_losses / total_exposure — pure loss cost
            rate per unit of exposure.
    """

    policy_count: int
    total_premium: float
    total_exposure: float
    total_losses: float
    claim_count: int
    loss_ratio: float | None
    frequency: float | None
    severity: float | None
    average_premium: float | None
    burning_cost: float | None

    def to_dict(self) -> dict[str, object]:
        """Plain-data representation, convenient for logging or display."""
        return {
            "policy_count": self.policy_count,
            "total_premium": self.total_premium,
            "total_exposure": self.total_exposure,
            "total_losses": self.total_losses,
            "claim_count": self.claim_count,
            "loss_ratio": self.loss_ratio,
            "frequency": self.frequency,
            "severity": self.severity,
            "average_premium": self.average_premium,
            "burning_cost": self.burning_cost,
        }
