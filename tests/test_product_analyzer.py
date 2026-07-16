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


def test_scale_decision_stores_performance_explanation() -> None:
    """SCALE decisions explain themselves with ROAS, cost, revenue, and conversions."""
    decision = ProductAnalyzer().analyze(
        sku="SKU-EXPLAIN-SCALE",
        clicks=30,
        cost=112.25,
        conversions=1.0,
        conversion_value=49095.0,
    )

    assert decision.status is ProductStatus.SCALE
    assert decision.explanation == (
        "ROAS = 43737.19\nCost = 112.25\nRevenue = 49095\nConversions = 1"
    )


def test_pause_decision_stores_spend_explanation() -> None:
    """PAUSE decisions explain themselves with cost, clicks, and conversions."""
    decision = ProductAnalyzer().analyze(
        sku="SKU-EXPLAIN-PAUSE",
        clicks=104,
        cost=450.0,
        conversions=0.0,
        conversion_value=0.0,
    )

    assert decision.status is ProductStatus.PAUSE
    assert decision.explanation == "Cost = 450\nClicks = 104\nConversions = 0"


def test_low_cost_watch_decision_stores_insufficient_data_explanation() -> None:
    """Low-spend WATCH decisions explain that more data is needed."""
    decision = ProductAnalyzer().analyze(
        sku="SKU-EXPLAIN-WATCH",
        clicks=3,
        cost=45.0,
        conversions=0.0,
        conversion_value=0.0,
    )

    assert decision.status is ProductStatus.WATCH
    assert decision.explanation == "Cost below pause threshold.\nNeed more data."


def test_keep_and_low_roas_watch_decisions_store_performance_explanations() -> None:
    """KEEP and low-ROAS WATCH decisions carry the same metric-based explanation."""
    keep_decision = ProductAnalyzer().analyze(
        sku="SKU-EXPLAIN-KEEP",
        clicks=10,
        cost=100.0,
        conversions=2.0,
        conversion_value=700.0,
    )
    watch_decision = ProductAnalyzer().analyze(
        sku="SKU-EXPLAIN-LOW-ROAS",
        clicks=10,
        cost=200.0,
        conversions=1.0,
        conversion_value=400.0,
    )

    assert keep_decision.status is ProductStatus.KEEP
    assert keep_decision.explanation == "ROAS = 700\nCost = 100\nRevenue = 700\nConversions = 2"
    assert watch_decision.status is ProductStatus.WATCH
    assert watch_decision.explanation == "ROAS = 200\nCost = 200\nRevenue = 400\nConversions = 1"
