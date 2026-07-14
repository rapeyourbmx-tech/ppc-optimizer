"""Report generation orchestration contract."""

from typing import Protocol

from app.config import ReportRequest


class ReportService(Protocol):
    """Coordinates report loading, analysis, and export."""

    def generate(self, request: ReportRequest) -> None:
        """Generate a report for the supplied request."""
