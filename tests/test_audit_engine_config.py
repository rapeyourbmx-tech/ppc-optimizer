"""Tests for configurable audit engine thresholds."""

import pandas as pd

from app.analyzers.audit_engine import AuditEngine
from app.config import AuditThresholds
from app.services.recommendation_engine import RecommendationEngine


def _audit(thresholds: AuditThresholds | None = None):
    """Audit one small product frame with the supplied thresholds."""
    products = pd.DataFrame(
        [
            {
                "product_id": "CTR-LOW",
                "impressions": 1000,
                "clicks": 15,
                "cost": 30.0,
                "conversions": 1.0,
                "conversion_value": 120.0,
            }
        ]
    )
    summary = RecommendationEngine().summarize([])
    return AuditEngine(thresholds=thresholds).audit(products, summary)


def test_audit_thresholds_default_matches_previous_behavior() -> None:
    """With default thresholds the 1.5% CTR product is not low-CTR."""
    report = _audit()

    assert report.products_low_ctr == []
    assert report.products_low_ctr is not None


def test_audit_low_ctr_threshold_comes_from_configuration() -> None:
    """Raising the low-CTR threshold flags the same product."""
    report = _audit(AuditThresholds(low_ctr=2.0))

    assert report.products_low_ctr == ["CTR-LOW"]


def test_audit_profitable_threshold_comes_from_configuration() -> None:
    """Lowering the profitable-ROAS threshold flags the product as profitable."""
    default_report = _audit()
    lowered_report = _audit(AuditThresholds(profitable_roas=300.0))

    assert default_report.products_profitable == []
    assert lowered_report.products_profitable == ["CTR-LOW"]
