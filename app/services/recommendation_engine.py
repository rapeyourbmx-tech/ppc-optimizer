"""Campaign recommendation aggregation."""

from collections import defaultdict
from collections.abc import Callable

from app.models.campaign_summary import CampaignSummary
from app.models.product_decision import ProductDecision, ProductStatus


class RecommendationEngine:
    """Aggregate product decisions into plain Python campaign statistics."""

    def summarize(self, decisions: list[ProductDecision]) -> CampaignSummary:
        """Return campaign statistics and priority recommendation lists.

        Scalable products are prioritized by ROAS. Paused products are
        prioritized by cost because they represent the greatest potential spend
        reduction.
        """
        decisions_by_status: dict[ProductStatus, list[ProductDecision]] = defaultdict(list)
        for decision in decisions:
            decisions_by_status[decision.status].append(decision)

        keep_decisions = decisions_by_status[ProductStatus.KEEP]
        pause_decisions = decisions_by_status[ProductStatus.PAUSE]
        scale_decisions = decisions_by_status[ProductStatus.SCALE]

        return CampaignSummary(
            total_products=len(decisions),
            keep=len(keep_decisions),
            watch=len(decisions_by_status[ProductStatus.WATCH]),
            pause=len(pause_decisions),
            scale=len(scale_decisions),
            cost_keep=self._total(keep_decisions, lambda decision: decision.cost),
            cost_pause=self._total(pause_decisions, lambda decision: decision.cost),
            revenue_keep=self._total(keep_decisions, lambda decision: decision.conversion_value),
            revenue_pause=self._total(pause_decisions, lambda decision: decision.conversion_value),
            top_scale_products=sorted(
                scale_decisions,
                key=lambda decision: decision.roas,
                reverse=True,
            ),
            top_pause_products=sorted(
                pause_decisions,
                key=lambda decision: decision.cost,
                reverse=True,
            ),
        )

    @staticmethod
    def _total(
        decisions: list[ProductDecision],
        value_getter: Callable[[ProductDecision], float],
    ) -> float:
        """Return the total for a numeric product-decision value."""
        return sum((value_getter(decision) for decision in decisions), start=0.0)
