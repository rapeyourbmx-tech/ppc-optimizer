"""Application configuration models."""

from pathlib import Path

from pydantic import BaseModel


class ReportRequest(BaseModel):
    """Paths required to build a product performance report."""

    source_path: Path
    output_path: Path
