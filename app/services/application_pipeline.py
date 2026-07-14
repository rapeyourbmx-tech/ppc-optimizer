"""Application pipeline that composes report processing components."""

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from app.analyzers.audit_engine import AuditEngine
from app.analyzers.product_analyzer import ProductAnalyzer
from app.loaders.product_report_loader import GoogleAdsProductReportLoader
from app.models.audit_report import AuditReport
from app.models.campaign_summary import CampaignSummary
from app.models.product_decision import ProductDecision
from app.services.recommendation_engine import RecommendationEngine
from app.utils.report_columns import (
    CLICK_COLUMNS,
    CONVERSION_COLUMNS,
    CONVERSION_VALUE_COLUMNS,
    COST_COLUMNS,
    SKU_COLUMNS,
    numeric_values,
    resolve_column,
)


@dataclass(frozen=True, slots=True)
class PipelineResult:
    """Plain-Python result of one complete product-report processing run."""

    decisions: list[ProductDecision]
    campaign_summary: CampaignSummary
    audit_report: AuditReport


class ApplicationPipeline:
    """Load, analyze, summarize, and audit a Google Ads product report."""

    def __init__(
        self,
        loader: GoogleAdsProductReportLoader | None = None,
        product_analyzer: ProductAnalyzer | None = None,
        recommendation_engine: RecommendationEngine | None = None,
        audit_engine: AuditEngine | None = None,
    ) -> None:
        """Initialize the pipeline with default or injected components."""
        self._loader = loader or GoogleAdsProductReportLoader()
        self._product_analyzer = product_analyzer or ProductAnalyzer()
        self._recommendation_engine = recommendation_engine or RecommendationEngine()
        self._audit_engine = audit_engine or AuditEngine()

    def run(self, source_path: Path) -> PipelineResult:
        """Process a CSV or XLSX product report from the supplied path."""
        products = self._loader.load(source_path)
        decisions = self._analyze_products(products)
        campaign_summary = self._recommendation_engine.summarize(decisions)
        audit_report = self._audit_engine.audit(products, campaign_summary)

        return PipelineResult(
            decisions=decisions,
            campaign_summary=campaign_summary,
            audit_report=audit_report,
        )

    def _analyze_products(self, products: pd.DataFrame) -> list[ProductDecision]:
        """Create one decision for every product report row."""
        sku_column = resolve_column(products, SKU_COLUMNS, "SKU")
        click_column = resolve_column(products, CLICK_COLUMNS, "clicks")
        cost_column = resolve_column(products, COST_COLUMNS, "cost")
        conversion_column = resolve_column(products, CONVERSION_COLUMNS, "conversions")
        revenue_column = resolve_column(
            products,
            CONVERSION_VALUE_COLUMNS,
            "conversion value",
        )

        sku = products[sku_column].fillna("").astype(str)
        clicks = numeric_values(products[click_column])
        cost = numeric_values(products[cost_column])
        conversions = numeric_values(products[conversion_column])
        conversion_value = numeric_values(products[revenue_column])

        return [
            self._product_analyzer.analyze(
                sku=product_sku,
                clicks=int(product_clicks),
                cost=float(product_cost),
                conversions=float(product_conversions),
                conversion_value=float(product_conversion_value),
            )
            for product_sku, product_clicks, product_cost, product_conversions, product_conversion_value in zip(
                sku,
                clicks,
                cost,
                conversions,
                conversion_value,
                strict=True,
            )
        ]
