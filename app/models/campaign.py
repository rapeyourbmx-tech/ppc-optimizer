"""Domain models for multi-campaign product report analysis."""

from dataclasses import dataclass

import pandas as pd

from app.models.campaign_summary import CampaignSummary
from app.models.product_decision import ProductDecision
from app.models.report import ProductReport


@dataclass(frozen=True, slots=True)
class CampaignMetadata:
    """Identity of one analyzed campaign derived from its source file."""

    name: str
    campaign_type: str
    source_file: str


@dataclass(frozen=True, slots=True)
class CampaignReport:
    """One fully analyzed campaign with its identity."""

    metadata: CampaignMetadata
    report: ProductReport

    @property
    def campaign_summary(self) -> CampaignSummary:
        """Return the campaign-level summary of this campaign."""
        return self.report.campaign_summary

    @property
    def health(self) -> str:
        """Return the audited overall health of this campaign."""
        return self.report.audit_report.overall_health


@dataclass(frozen=True, slots=True)
class OverallSummary:
    """Aggregated statistics across every analyzed campaign."""

    total_cost: float
    total_revenue: float
    total_conversions: float
    total_products: int
    keep: int
    watch: int
    pause: int
    scale: int


@dataclass(frozen=True, slots=True)
class MultiCampaignReport:
    """Combined result of analyzing one or more product reports.

    The products data frame contains every campaign's rows with
    campaign_name, campaign_type, and source_file columns, aligned
    row-by-row with the decisions list.
    """

    campaigns: list[CampaignReport]
    overall_summary: OverallSummary
    overall_health: str
    products: pd.DataFrame
    decisions: list[ProductDecision]
