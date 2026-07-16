"""Product-level advertising performance analysis."""

from app.analyzers.decision_explainer import DecisionExplainer
from app.models.product_decision import ProductDecision, ProductStatus


class ProductAnalyzer:
    """Classify a product according to its advertising performance."""

    _LOW_COST_THRESHOLD: float = 100.0
    _KEEP_ROAS_THRESHOLD: float = 500.0
    _SCALE_ROAS_THRESHOLD: float = 1200.0

    def __init__(self, explainer: DecisionExplainer | None = None) -> None:
        """Initialize the analyzer with a decision explainer."""
        self._explainer = explainer or DecisionExplainer()

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
        status, reason, explanation = self._decide(
            clicks=clicks,
            cost=cost,
            conversions=conversions,
            conversion_value=conversion_value,
            roas=roas,
        )

        return ProductDecision(
            sku=sku,
            clicks=clicks,
            cost=cost,
            conversions=conversions,
            conversion_value=conversion_value,
            roas=roas,
            status=status,
            reason=reason,
            explanation=explanation,
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
        clicks: int,
        cost: float,
        conversions: float,
        conversion_value: float,
        roas: float,
    ) -> tuple[ProductStatus, str, str]:
        """Select the status, reason, and explanation for one product's metrics."""
        if cost < self._LOW_COST_THRESHOLD:
            return (
                ProductStatus.WATCH,
                "Cost is below the 100 threshold.",
                self._explainer.insufficient_data(),
            )

        if conversions == 0:
            return (
                ProductStatus.PAUSE,
                "No conversions at or above the 100 cost threshold.",
                self._explainer.spend_without_conversions(
                    cost=cost,
                    clicks=clicks,
                    conversions=conversions,
                ),
            )

        performance_explanation = self._explainer.performance_summary(
            roas=roas,
            cost=cost,
            conversion_value=conversion_value,
            conversions=conversions,
        )

        if roas > self._SCALE_ROAS_THRESHOLD:
            return ProductStatus.SCALE, "ROAS is above 1200%.", performance_explanation

        if roas >= self._KEEP_ROAS_THRESHOLD:
            return (
                ProductStatus.KEEP,
                "ROAS is between 500% and 1200%.",
                performance_explanation,
            )

        return (
            ProductStatus.WATCH,
            "ROAS is below 500% with conversions.",
            performance_explanation,
        )
