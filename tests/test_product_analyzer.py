"""Tests for product performance analysis."""

from app.analyzers.product_analyzer import ProductAnalyzer
from app.config import DecisionThresholds
from app.models.product_decision import ProductStatus


def test_analyze_marks_low_cost_product_for_watch() -> None:
    """Cost below the watch threshold takes priority over strong performance."""
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
        cost=350.0,
        conversions=0.0,
        conversion_value=0.0,
    )

    assert decision.status is ProductStatus.PAUSE


def test_analyze_scales_product_meeting_roas_and_revenue_thresholds() -> None:
    """Meeting both the ROAS and revenue thresholds marks the product SCALE."""
    decision = ProductAnalyzer().analyze(
        sku="SKU-003",
        clicks=30,
        cost=350.0,
        conversions=1.0,
        conversion_value=49095.0,
    )

    assert decision.status is ProductStatus.SCALE


def test_analyze_does_not_scale_without_enough_revenue() -> None:
    """High ROAS without enough conversion value stays below SCALE."""
    decision = ProductAnalyzer().analyze(
        sku="SKU-004",
        clicks=30,
        cost=350.0,
        conversions=3.0,
        conversion_value=4999.0,
    )

    assert decision.status is ProductStatus.KEEP


def test_analyze_keeps_product_with_enough_conversions() -> None:
    """Products at the keep conversion threshold are kept."""
    decision = ProductAnalyzer().analyze(
        sku="SKU-005",
        clicks=25,
        cost=300.0,
        conversions=2.0,
        conversion_value=700.0,
    )

    assert decision.status is ProductStatus.KEEP


def test_analyze_watches_converting_product_below_keep_threshold() -> None:
    """Products converting below the keep threshold stay on the watch list."""
    decision = ProductAnalyzer().analyze(
        sku="SKU-006",
        clicks=16,
        cost=400.0,
        conversions=1.0,
        conversion_value=400.0,
    )

    assert decision.status is ProductStatus.WATCH
    assert decision.reason == "Performance is below the scale and keep thresholds."


def test_analyze_uses_injected_custom_thresholds() -> None:
    """Custom thresholds replace the built-in decision defaults."""
    thresholds = DecisionThresholds.model_validate(
        {
            "watch": {"max_cost": 50},
            "pause": {"min_cost": 50, "max_conversions": 0},
            "scale": {"min_roas": 100, "min_conversion_value": 100},
            "keep": {"min_conversions": 1},
        }
    )

    decision = ProductAnalyzer(thresholds=thresholds).analyze(
        sku="SKU-CUSTOM",
        clicks=5,
        cost=60.0,
        conversions=1.0,
        conversion_value=120.0,
    )

    assert decision.status is ProductStatus.SCALE


def test_scale_decision_stores_performance_explanation() -> None:
    """SCALE decisions explain themselves with ROAS, cost, revenue, and conversions."""
    decision = ProductAnalyzer().analyze(
        sku="SKU-EXPLAIN-SCALE",
        clicks=30,
        cost=350.0,
        conversions=1.0,
        conversion_value=49095.0,
    )

    assert decision.status is ProductStatus.SCALE
    assert decision.explanation == ("ROAS = 14027.14\nCost = 350\nRevenue = 49095\nConversions = 1")


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


def test_keep_and_low_performance_watch_decisions_store_performance_explanations() -> None:
    """KEEP and low-performance WATCH decisions carry metric-based explanations."""
    keep_decision = ProductAnalyzer().analyze(
        sku="SKU-EXPLAIN-KEEP",
        clicks=10,
        cost=300.0,
        conversions=2.0,
        conversion_value=700.0,
    )
    watch_decision = ProductAnalyzer().analyze(
        sku="SKU-EXPLAIN-LOW",
        clicks=10,
        cost=400.0,
        conversions=1.0,
        conversion_value=400.0,
    )

    assert keep_decision.status is ProductStatus.KEEP
    assert keep_decision.explanation == "ROAS = 233.33\nCost = 300\nRevenue = 700\nConversions = 2"
    assert watch_decision.status is ProductStatus.WATCH
    assert watch_decision.explanation == "ROAS = 100\nCost = 400\nRevenue = 400\nConversions = 1"
