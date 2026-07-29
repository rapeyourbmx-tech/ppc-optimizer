"""Tests for campaign-wide audit analysis."""

import pandas as pd

from app.analyzers.audit_engine import AuditEngine
from app.models.campaign_summary import CampaignSummary
from app.models.product_decision import ProductDecision, ProductStatus


def _summary() -> CampaignSummary:
    """Build a campaign summary containing one scale recommendation."""
    scale_product = ProductDecision(
        sku="HIGH-ROAS",
        clicks=20,
        cost=100.0,
        conversions=1.0,
        conversion_value=1300.0,
        roas=1300.0,
        status=ProductStatus.SCALE,
        reason="ROAS is above 1200%.",
    )
    return CampaignSummary(
        total_products=6,
        keep=1,
        watch=2,
        pause=2,
        scale=1,
        cost_keep=100.0,
        cost_pause=210.0,
        revenue_keep=700.0,
        revenue_pause=0.0,
        top_scale_products=[scale_product],
        top_pause_products=[],
    )


def _products() -> pd.DataFrame:
    """Build representative normalized product report data."""
    return pd.DataFrame(
        [
            {
                "sku": "NO-IMPRESSION",
                "impressions": 0,
                "clicks": 0,
                "cost": 0.0,
                "conversions": 0.0,
                "conversion_value": 0.0,
            },
            {
                "sku": "NO-CLICK",
                "impressions": 100,
                "clicks": 0,
                "cost": 10.0,
                "conversions": 0.0,
                "conversion_value": 0.0,
            },
            {
                "sku": "WASTE",
                "impressions": 1000,
                "clicks": 20,
                "cost": 200.0,
                "conversions": 0.0,
                "conversion_value": 0.0,
            },
            {
                "sku": "PROFITABLE",
                "impressions": 1000,
                "clicks": 50,
                "cost": 100.0,
                "conversions": 1.0,
                "conversion_value": 700.0,
            },
            {
                "sku": "HIGH-ROAS",
                "impressions": 1000,
                "clicks": 20,
                "cost": 100.0,
                "conversions": 1.0,
                "conversion_value": 1300.0,
            },
            {
                "sku": "LOW-CTR",
                "impressions": 1000,
                "clicks": 5,
                "cost": 50.0,
                "conversions": 1.0,
                "conversion_value": 100.0,
            },
        ]
    )


def test_audit_generates_campaign_findings_and_recommendations() -> None:
    """The audit identifies practical report-wide optimization opportunities."""
    report = AuditEngine().audit(_products(), _summary())

    assert report.overall_health == "Needs attention"
    assert report.budget_waste == 200.0
    assert report.potential_scaling == 1300.0
    assert report.products_without_impressions == ["NO-IMPRESSION"]
    assert report.products_without_clicks == ["NO-CLICK"]
    assert report.products_with_clicks_no_sales == ["WASTE"]
    assert report.products_profitable == ["PROFITABLE", "HIGH-ROAS"]
    assert report.products_high_roas == ["HIGH-ROAS"]
    assert report.products_low_ctr == ["NO-CLICK", "LOW-CTR"]
    assert report.products_expensive_clicks == ["WASTE", "HIGH-ROAS", "LOW-CTR"]
    assert "Pause or fix products with clicks but no sales." in report.recommendations
    assert "Consider increasing budget for high-ROAS products." in report.recommendations
    assert report.summary_text == (
        "6 products audited: 1 keep, 2 watch, 2 pause, 1 scale. Budget waste: 200.00. "
        "Scaling revenue: 1300.00."
    )


def test_audit_returns_empty_report_for_empty_product_data() -> None:
    """An empty report returns a plain dataclass without recommendations noise."""
    products = pd.DataFrame(
        columns=[
            "sku",
            "impressions",
            "clicks",
            "cost",
            "conversions",
            "conversion_value",
        ]
    )
    empty_summary = CampaignSummary(
        total_products=0,
        keep=0,
        watch=0,
        pause=0,
        scale=0,
        cost_keep=0.0,
        cost_pause=0.0,
        revenue_keep=0.0,
        revenue_pause=0.0,
        top_scale_products=[],
        top_pause_products=[],
    )

    report = AuditEngine().audit(products, empty_summary)

    assert report.overall_health == "No data"
    assert report.recommendations == ["No product data is available to audit."]
    assert report.budget_waste == 0.0
    assert report.potential_scaling == 0.0
    assert report.summary_text == "No product data is available to audit."
