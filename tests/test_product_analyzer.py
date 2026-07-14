"""Tests for product performance analysis."""

from app.analyzers.product_analyzer import ProductAnalyzer
from app.models.product_decision import ProductStatus


def test_analyze_marks_low_cost_product_for_watch() -> None:
    """Cost below 100 takes priority over otherwise strong performance."""
    decision = ProductAnalyzer().analyze(
        sku="SKU-001",
        clicks=10,
        cost=99.0,
        conversions=2.0,
        conversion_value=1500.0,
    )

    assert decision.status is ProductStatus.WATCH
    assert decision.roas > 1200.0


def test_analyze_pauses_product_with_cost_and_no_conversions() -> None:
    """Products with material spend and no conversions are paused."""
    decision = ProductAnalyzer().analyze(
        sku="SKU-002",
        clicks=20,
        cost=100.0,
        conversions=0.0,
        conversion_value=0.0,
    )

    assert decision.status is ProductStatus.PAUSE


def test_analyze_scales_product_above_roas_threshold() -> None:
    """ROAS above 1200 percent is eligible to scale."""
    decision = ProductAnalyzer().analyze(
        sku="SKU-003",
        clicks=30,
        cost=100.0,
        conversions=4.0,
        conversion_value=1200.01,
    )

    assert decision.status is ProductStatus.SCALE


def test_analyze_keeps_product_at_inclusive_roas_boundaries() -> None:
    """ROAS values from 500 through 1200 percent are kept."""
    analyzer = ProductAnalyzer()

    low_boundary_decision = analyzer.analyze(
        sku="SKU-004",
        clicks=25,
        cost=100.0,
        conversions=1.0,
        conversion_value=500.0,
    )
    high_boundary_decision = analyzer.analyze(
        sku="SKU-005",
        clicks=25,
        cost=100.0,
        conversions=1.0,
        conversion_value=1200.0,
    )

    assert low_boundary_decision.status is ProductStatus.KEEP
    assert high_boundary_decision.status is ProductStatus.KEEP


def test_analyze_watches_product_below_roas_threshold_with_conversions() -> None:
    """Products with conversions but ROAS below 500 percent are watched."""
    decision = ProductAnalyzer().analyze(
        sku="SKU-006",
        clicks=16,
        cost=100.0,
        conversions=1.0,
        conversion_value=499.99,
    )

    assert decision.status is ProductStatus.WATCH
