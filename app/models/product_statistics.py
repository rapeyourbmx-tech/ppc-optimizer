"""Internal model of imported product advertising statistics."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ProductStatistics:
    """Advertising statistics of one product from a Google Ads export.

    assist_revenue is the internal business name of the value sourced
    from the Google Ads "Cross-sell Revenue" column. It is a separate
    analytical metric: it is never added to the conversion revenue and
    never enters ROAS.
    """

    offer_id: str
    cost: float
    clicks: int
    impressions: int
    direct_revenue: float
    assist_revenue: float
    conversions: float
