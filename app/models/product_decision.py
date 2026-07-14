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
    """The recommended action for one advertised product."""

    sku: str
    clicks: int
    cost: float
    conversions: float
    conversion_value: float
    roas: float
    status: ProductStatus
    reason: str

    def __post_init__(self) -> None:
        """Reject values outside the supported product statuses."""
        if not isinstance(self.status, ProductStatus):
            message = "status must be a ProductStatus value."
            raise ValueError(message)
