"""Campaign-level recommendation summary models."""

from dataclasses import dataclass

from app.models.product_decision import ProductDecision


@dataclass(frozen=True, slots=True)
class CampaignSummary:
    """Aggregated statistics and priority products for one campaign."""

    total_products: int
    keep: int
    watch: int
    pause: int
    scale: int
    cost_keep: float
    cost_pause: float
    revenue_keep: float
    revenue_pause: float
    top_scale_products: list[ProductDecision]
    top_pause_products: list[ProductDecision]
