"""Models for campaign-wide audit results."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AuditReport:
    """Plain-Python findings and recommendations for a product campaign."""

    overall_health: str
    recommendations: list[str]
    budget_waste: float
    potential_scaling: float
    products_without_impressions: list[str]
    products_without_clicks: list[str]
    products_with_clicks_no_sales: list[str]
    products_profitable: list[str]
    products_high_roas: list[str]
    products_low_ctr: list[str]
    products_expensive_clicks: list[str]
    summary_text: str
