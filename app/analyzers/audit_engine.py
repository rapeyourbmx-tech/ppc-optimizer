"""Campaign-wide audit analysis for Google Ads product reports."""

import pandas as pd

from app.models.audit_report import AuditReport
from app.models.campaign_summary import CampaignSummary
from app.models.product_decision import ProductDecision
from app.utils.report_columns import (
    CLICK_COLUMNS,
    CONVERSION_COLUMNS,
    CONVERSION_VALUE_COLUMNS,
    COST_COLUMNS,
    IMPRESSION_COLUMNS,
    SKU_COLUMNS,
    numeric_values,
    resolve_column,
)


class AuditEngine:
    """Analyze all report products and produce practical recommendations."""

    _PROFITABLE_ROAS_THRESHOLD: float = 500.0
    _HIGH_ROAS_THRESHOLD: float = 1200.0
    _LOW_CTR_THRESHOLD: float = 1.0

    def audit(self, products: pd.DataFrame, summary: CampaignSummary) -> AuditReport:
        """Audit all products and return a plain-Python report.

        The DataFrame is expected to use the normalized column names produced
        by the report loader. Product lists in the result contain SKU strings.
        """
        sku_column = resolve_column(products, SKU_COLUMNS, "SKU")
        impression_column = resolve_column(
            products,
            IMPRESSION_COLUMNS,
            "impressions",
        )
        click_column = resolve_column(products, CLICK_COLUMNS, "clicks")
        cost_column = resolve_column(products, COST_COLUMNS, "cost")
        conversion_column = resolve_column(
            products,
            CONVERSION_COLUMNS,
            "conversions",
        )
        revenue_column = resolve_column(
            products,
            CONVERSION_VALUE_COLUMNS,
            "conversion value",
        )

        sku = products[sku_column].fillna("").astype(str)
        impressions = numeric_values(products[impression_column])
        clicks = numeric_values(products[click_column])
        cost = numeric_values(products[cost_column])
        conversions = numeric_values(products[conversion_column])
        revenue = numeric_values(products[revenue_column])

        ctr = clicks.divide(impressions.where(impressions != 0)).multiply(100).fillna(0.0)
        roas = revenue.divide(cost.where(cost != 0)).multiply(100).fillna(0.0)
        cpc = cost.divide(clicks.where(clicks != 0))
        total_clicks = clicks.sum()
        average_cpc = cost.sum() / total_clicks if total_clicks > 0 else 0.0

        without_impressions = impressions == 0
        without_clicks = (impressions > 0) & (clicks == 0)
        clicks_no_sales = (clicks > 0) & (conversions == 0)
        profitable = roas >= self._PROFITABLE_ROAS_THRESHOLD
        high_roas = roas > self._HIGH_ROAS_THRESHOLD
        low_ctr = (impressions > 0) & (ctr < self._LOW_CTR_THRESHOLD)
        expensive_clicks = (clicks > 0) & (cpc > average_cpc)

        budget_waste = cost.loc[clicks_no_sales].sum()
        potential_scaling = self._total_scale_revenue(summary.top_scale_products)
        product_count = len(products)
        products_without_impressions = self._sku_list(sku, without_impressions)
        products_without_clicks = self._sku_list(sku, without_clicks)
        products_with_clicks_no_sales = self._sku_list(sku, clicks_no_sales)
        products_profitable = self._sku_list(sku, profitable)
        products_high_roas = self._sku_list(sku, high_roas)
        products_low_ctr = self._sku_list(sku, low_ctr)
        products_expensive_clicks = self._sku_list(sku, expensive_clicks)

        if product_count == 0:
            return self._empty_report()

        recommendations = self._recommendations(
            budget_waste=budget_waste,
            products_without_impressions=products_without_impressions,
            products_without_clicks=products_without_clicks,
            products_low_ctr=products_low_ctr,
            products_expensive_clicks=products_expensive_clicks,
            scale_count=summary.scale,
        )

        return AuditReport(
            overall_health=self._overall_health(summary=summary, budget_waste=budget_waste),
            recommendations=recommendations,
            budget_waste=float(budget_waste),
            potential_scaling=potential_scaling,
            products_without_impressions=products_without_impressions,
            products_without_clicks=products_without_clicks,
            products_with_clicks_no_sales=products_with_clicks_no_sales,
            products_profitable=products_profitable,
            products_high_roas=products_high_roas,
            products_low_ctr=products_low_ctr,
            products_expensive_clicks=products_expensive_clicks,
            summary_text=self._summary_text(
                product_count=product_count,
                summary=summary,
                budget_waste=budget_waste,
                potential_scaling=potential_scaling,
            ),
        )

    @staticmethod
    def _sku_list(sku: pd.Series, condition: pd.Series) -> list[str]:
        """Return SKU strings for products matching an audit condition."""
        return list(sku.loc[condition])

    @staticmethod
    def _total_scale_revenue(decisions: list[ProductDecision]) -> float:
        """Return the conversion value represented by scale decisions."""
        return sum((decision.conversion_value for decision in decisions), start=0.0)

    @staticmethod
    def _empty_report() -> AuditReport:
        """Return the audit result for an empty product report."""
        message = "No product data is available to audit."
        return AuditReport(
            overall_health="No data",
            recommendations=[message],
            budget_waste=0.0,
            potential_scaling=0.0,
            products_without_impressions=[],
            products_without_clicks=[],
            products_with_clicks_no_sales=[],
            products_profitable=[],
            products_high_roas=[],
            products_low_ctr=[],
            products_expensive_clicks=[],
            summary_text=message,
        )

    @staticmethod
    def _overall_health(*, summary: CampaignSummary, budget_waste: float) -> str:
        """Derive a concise campaign health label."""
        if budget_waste > 0 or summary.pause > 0:
            return "Needs attention"
        if summary.watch > 0:
            return "Monitor"
        return "Healthy"

    @staticmethod
    def _recommendations(
        *,
        budget_waste: float,
        products_without_impressions: list[str],
        products_without_clicks: list[str],
        products_low_ctr: list[str],
        products_expensive_clicks: list[str],
        scale_count: int,
    ) -> list[str]:
        """Build concise actionable recommendations from audit findings."""
        recommendations: list[str] = []

        if budget_waste > 0:
            recommendations.append("Pause or fix products with clicks but no sales.")
        if products_without_impressions:
            recommendations.append("Review products without impressions for eligibility issues.")
        if products_without_clicks:
            recommendations.append("Improve titles, images, or bids for products without clicks.")
        if products_low_ctr:
            recommendations.append("Improve listings or targeting for low-CTR products.")
        if products_expensive_clicks:
            recommendations.append("Review bids for products with above-average CPC.")
        if scale_count > 0:
            recommendations.append("Consider increasing budget for high-ROAS products.")

        if not recommendations:
            recommendations.append("Maintain current settings and monitor performance.")

        return recommendations

    @staticmethod
    def _summary_text(
        *,
        product_count: int,
        summary: CampaignSummary,
        budget_waste: float,
        potential_scaling: float,
    ) -> str:
        """Create a concise human-readable campaign audit summary."""
        return (
            f"{product_count} products audited: {summary.keep} keep, {summary.watch} watch, "
            f"{summary.pause} pause, {summary.scale} scale. Budget waste: {budget_waste:.2f}. "
            f"Scaling revenue: {potential_scaling:.2f}."
        )
