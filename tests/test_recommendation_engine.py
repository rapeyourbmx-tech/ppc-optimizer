"""Tests for campaign recommendation aggregation."""

from app.models.product_decision import ProductDecision, ProductStatus
from app.services.recommendation_engine import RecommendationEngine


def _decision(
    *,
    sku: str,
    status: ProductStatus,
    cost: float,
    effective_revenue: float,
    roas: float,
) -> ProductDecision:
    """Build a product decision for recommendation engine tests."""
    return ProductDecision(
        sku=sku,
        clicks=10,
        cost=cost,
        conversions=0.0 if status is ProductStatus.PAUSE else 1.0,
        effective_revenue=effective_revenue,
        roas=roas,
        status=status,
        reason="Test decision.",
    )


def test_summarize_calculates_campaign_statistics_and_priorities() -> None:
    """The engine aggregates counts, amounts, and ordered priority lists."""
    decisions = [
        _decision(
            sku="KEEP-1",
            status=ProductStatus.KEEP,
            cost=100.0,
            effective_revenue=800.0,
            roas=800.0,
        ),
        _decision(
            sku="WATCH-1",
            status=ProductStatus.WATCH,
            cost=80.0,
            effective_revenue=240.0,
            roas=300.0,
        ),
        _decision(
            sku="PAUSE-LOW",
            status=ProductStatus.PAUSE,
            cost=200.0,
            effective_revenue=50.0,
            roas=0.0,
        ),
        _decision(
            sku="PAUSE-HIGH",
            status=ProductStatus.PAUSE,
            cost=300.0,
            effective_revenue=75.0,
            roas=0.0,
        ),
        _decision(
            sku="SCALE-LOW",
            status=ProductStatus.SCALE,
            cost=100.0,
            effective_revenue=1300.0,
            roas=1300.0,
        ),
        _decision(
            sku="SCALE-HIGH",
            status=ProductStatus.SCALE,
            cost=100.0,
            effective_revenue=1500.0,
            roas=1500.0,
        ),
    ]

    summary = RecommendationEngine().summarize(decisions)

    assert summary.total_products == 6
    assert summary.keep == 1
    assert summary.watch == 1
    assert summary.pause == 2
    assert summary.scale == 2
    assert summary.cost_keep == 100.0
    assert summary.cost_pause == 500.0
    assert summary.revenue_keep == 800.0
    assert summary.revenue_pause == 125.0
    assert [decision.sku for decision in summary.top_scale_products] == [
        "SCALE-HIGH",
        "SCALE-LOW",
    ]
    assert [decision.sku for decision in summary.top_pause_products] == [
        "PAUSE-HIGH",
        "PAUSE-LOW",
    ]


def test_summarize_returns_zeroed_statistics_for_no_decisions() -> None:
    """The engine returns an empty plain-object summary for an empty campaign."""
    summary = RecommendationEngine().summarize([])

    assert summary.total_products == 0
    assert summary.keep == 0
    assert summary.watch == 0
    assert summary.pause == 0
    assert summary.scale == 0
    assert summary.cost_keep == 0.0
    assert summary.cost_pause == 0.0
    assert summary.revenue_keep == 0.0
    assert summary.revenue_pause == 0.0
    assert summary.top_scale_products == []
    assert summary.top_pause_products == []
