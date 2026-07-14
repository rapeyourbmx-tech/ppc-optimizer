"""Source product report access contract."""

from pathlib import Path
from typing import Protocol

from app.models.report import ProductReport


class ProductReportRepository(Protocol):
    """Loads a normalized product report from a source file."""

    def load(self, source_path: Path) -> ProductReport:
        """Load a product report from the supplied source path."""
