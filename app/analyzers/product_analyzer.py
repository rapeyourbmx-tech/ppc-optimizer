"""Product-level advertising performance analysis."""

from app.models.product_decision import ProductDecision, ProductStatus


class ProductAnalyzer:
    """Classify a product according to its advertising performance."""

    _LOW_COST_THRESHOLD: float = 100.0
    _KEEP_ROAS_THRESHOLD: float = 500.0
    _SCALE_ROAS_THRESHOLD: float = 1200.0

    def analyze(
        self,
        *,
        sku: str,
        clicks: int,
        cost: float,
        conversions: float,
        conversion_value: float,
    ) -> ProductDecision:
        """Create a decision using the configured product performance rules."""
        roas = self._calculate_roas(cost=cost, conversion_value=conversion_value)
        status, reason = self._decide(cost=cost, conversions=conversions, roas=roas)

        return ProductDecision(
            sku=sku,
            clicks=clicks,
            cost=cost,
            conversions=conversions,
            conversion_value=conversion_value,
            roas=roas,
            status=status,
            reason=reason,
        )

    @staticmethod
    def _calculate_roas(*, cost: float, conversion_value: float) -> float:
        """Calculate ROAS as a percentage without dividing by zero."""
        if cost == 0:
            return 0.0

        return (conversion_value / cost) * 100

    def _decide(
        self,
        *,
        cost: float,
        conversions: float,
        roas: float,
    ) -> tuple[ProductStatus, str]:
        """Select the status and reason for one product's metrics."""
        if cost < self._LOW_COST_THRESHOLD:
            return ProductStatus.WATCH, "Cost is below the 100 threshold."

        if conversions == 0:
            return ProductStatus.PAUSE, "No conversions at or above the 100 cost threshold."

        if roas > self._SCALE_ROAS_THRESHOLD:
            return ProductStatus.SCALE, "ROAS is above 1200%."

        if roas >= self._KEEP_ROAS_THRESHOLD:
            return ProductStatus.KEEP, "ROAS is between 500% and 1200%."

        return ProductStatus.WATCH, "ROAS is below 500% with conversions."
