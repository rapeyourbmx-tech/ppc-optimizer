"""Models that describe product advertising decisions."""

from dataclasses import dataclass
from enum import StrEnum


class ProductStatus(StrEnum):
    """Allowed optimization statuses for a product."""

    KEEP = "KEEP"
    WATCH = "WATCH"
    PAUSE = "PAUSE"
    SCALE = "SCALE"


@dataclass(frozen=True, slots=True)
class ProductDecision:
    """The recommended action for one advertised product.

    conversion_value is the revenue behind ROAS and every performance
    rule. assist_revenue (Cross-sell Revenue) never enters those
    calculations; it is a separate business signal that can protect a
    product from an automatic PAUSE and is available for reporting.
    """

    sku: str
    clicks: int
    cost: float
    conversions: float
    conversion_value: float
    roas: float
    status: ProductStatus
    reason: str
    explanation: str = ""
    assist_revenue: float = 0.0

    def __post_init__(self) -> None:
        """Reject values outside the supported product statuses."""
        if not isinstance(self.status, ProductStatus):
            message = "status must be a ProductStatus value."
            raise ValueError(message)
