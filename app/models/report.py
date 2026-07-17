"""Domain model for a fully analyzed Google Ads product report."""

from dataclasses import dataclass

import pandas as pd

from app.models.audit_report import AuditReport
from app.models.campaign_summary import CampaignSummary
from app.models.product_decision import ProductDecision


@dataclass(frozen=True, slots=True)
class ProductReport:
    """Everything required to export one analyzed product report.

    The decisions list is aligned row-by-row with the products data frame.
    """

    products: pd.DataFrame
    decisions: list[ProductDecision]
    campaign_summary: CampaignSummary
    audit_report: AuditReport
