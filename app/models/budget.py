"""Domain models for campaign budget optimization."""

from dataclasses import dataclass
from enum import StrEnum


class BudgetAction(StrEnum):
    """Recommended budget action for one campaign."""

    INCREASE = "INCREASE"
    KEEP = "KEEP"
    DECREASE = "DECREASE"


@dataclass(frozen=True, slots=True)
class CampaignBudgetAssessment:
    """Budget efficiency assessment of one campaign.

    The current budget equals the observed spend for the analyzed period,
    because Google Ads product exports carry no budget column.
    """

    campaign_name: str
    current_budget: float
    current_spend: float
    current_roas: float
    marginal_efficiency: float
    saturation: float
    conversions: float
    action: BudgetAction


@dataclass(frozen=True, slots=True)
class BudgetTransfer:
    """One recommended budget move between two campaigns."""

    source_campaign: str
    destination_campaign: str
    amount: float
    expected_revenue_increase: float
    confidence: float


@dataclass(frozen=True, slots=True)
class BudgetOptimizationReport:
    """Complete budget redistribution recommendation."""

    assessments: list[CampaignBudgetAssessment]
    transfers: list[BudgetTransfer]
    total_expected_gain: float
