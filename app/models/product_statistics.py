"""Internal model of imported product advertising statistics."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ProductStatistics:
    """Advertising statistics of one product from a Google Ads export.

    assist_revenue is the internal business name of the value sourced
    from the Google Ads "Cross-sell Revenue" column. If a separate
    Assisted Revenue metric appears later, the model will be extended;
    for now this is the only assist field.
    """

    offer_id: str
    cost: float
    clicks: int
    impressions: int
    direct_revenue: float
    assist_revenue: float
    conversions: float

    @property
    def effective_revenue(self) -> float:
        """Direct revenue plus assist revenue."""
        return self.direct_revenue + self.assist_revenue
