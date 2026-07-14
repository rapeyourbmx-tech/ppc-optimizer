"""Excel workbook export contract."""

from pathlib import Path
from typing import Protocol

from app.models.report import ProductReport


class WorkbookExporter(Protocol):
    """Exports a product report to an Excel workbook."""

    def export(self, report: ProductReport, output_path: Path) -> None:
        """Export the supplied report to the requested path."""
