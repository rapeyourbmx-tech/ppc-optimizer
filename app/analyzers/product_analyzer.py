"""Product-level advertising performance analysis."""

from app.analyzers.decision_explainer import DecisionExplainer
from app.config import DecisionThresholds
from app.models.product_decision import ProductDecision, ProductStatus


class ProductAnalyzer:
    """Classify a product according to configurable performance thresholds."""

    def __init__(
        self,
        thresholds: DecisionThresholds | None = None,
        explainer: DecisionExplainer | None = None,
    ) -> None:
        """Initialize the analyzer with decision thresholds and an explainer."""
        self._thresholds = thresholds or DecisionThresholds()
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
        watch = self._thresholds.watch
        pause = self._thresholds.pause
        scale = self._thresholds.scale
        keep = self._thresholds.keep

        if cost < watch.max_cost:
            return (
                ProductStatus.WATCH,
                f"Cost is below the {watch.max_cost:g} watch threshold.",
                self._explainer.insufficient_data(),
            )

        if cost >= pause.min_cost and conversions <= pause.max_conversions:
            return (
                ProductStatus.PAUSE,
                (
                    f"Cost of at least {pause.min_cost:g} with no more than "
                    f"{pause.max_conversions:g} conversions."
                ),
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

        if roas >= scale.min_roas and conversion_value >= scale.min_conversion_value:
            return (
                ProductStatus.SCALE,
                (
                    f"ROAS of at least {scale.min_roas:g}% with conversion value "
                    f"of at least {scale.min_conversion_value:g}."
                ),
                performance_explanation,
            )

        if conversions >= keep.min_conversions:
            return (
                ProductStatus.KEEP,
                f"At least {keep.min_conversions:g} conversions.",
                performance_explanation,
            )

        return (
            ProductStatus.WATCH,
            "Performance is below the scale and keep thresholds.",
            performance_explanation,
        )
