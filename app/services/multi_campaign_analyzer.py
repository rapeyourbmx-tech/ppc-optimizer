"""Analysis of multiple Google Ads product reports in one run."""

from collections.abc import Sequence
from pathlib import Path

import pandas as pd

from app.models.campaign import (
    CampaignMetadata,
    CampaignReport,
    MultiCampaignReport,
    OverallSummary,
)
from app.models.product_decision import ProductDecision, ProductStatus
from app.models.report import ProductReport
from app.services.application_pipeline import ApplicationPipeline

_HEALTHY = "Healthy"
_NEEDS_ATTENTION = "Needs attention"
_CAMPAIGN_TYPE_KEYWORDS: tuple[tuple[str, str], ...] = (
    ("high", "High priority"),
    ("average", "Medium priority"),
    ("medium", "Medium priority"),
    ("low", "Low priority"),
)
_DEFAULT_CAMPAIGN_TYPE = "Standard"
_METADATA_COLUMNS: tuple[str, ...] = ("campaign_name", "campaign_type", "source_file")


class MultiCampaignAnalyzer:
    """Analyze several product reports and combine them into one report."""

    def __init__(self, pipeline: ApplicationPipeline | None = None) -> None:
        """Initialize the analyzer with the single-report pipeline it reuses."""
        self._pipeline = pipeline or ApplicationPipeline()

    def analyze(self, source_paths: Sequence[Path]) -> MultiCampaignReport:
        """Run the pipeline for every source file and combine the results.

        Args:
            source_paths: One or more report files, each treated as a campaign.

        Returns:
            A combined multi-campaign report.

        Raises:
            ValueError: If no source files are supplied.
        """
        if not source_paths:
            message = "At least one report file is required."
            raise ValueError(message)

        campaigns: list[CampaignReport] = []
        campaign_frames: list[pd.DataFrame] = []
        combined_decisions: list[ProductDecision] = []

        for source_path in source_paths:
            result = self._pipeline.run(source_path)
            metadata = _derive_campaign_metadata(source_path)
            campaigns.append(
                CampaignReport(
                    metadata=metadata,
                    report=ProductReport(
                        products=result.products,
                        decisions=result.decisions,
                        campaign_summary=result.campaign_summary,
                        audit_report=result.audit_report,
                    ),
                )
            )
            campaign_frames.append(_with_campaign_columns(result.products, metadata))
            combined_decisions.extend(result.decisions)

        return MultiCampaignReport(
            campaigns=campaigns,
            overall_summary=_build_overall_summary(combined_decisions),
            overall_health=_derive_overall_health(campaigns),
            products=pd.concat(campaign_frames, ignore_index=True, sort=False),
            decisions=combined_decisions,
        )


def _derive_campaign_metadata(source_path: Path) -> CampaignMetadata:
    """Derive a campaign identity from one report file path."""
    stem = source_path.stem
    lowered_stem = stem.casefold()
    campaign_type = next(
        (
            derived_type
            for keyword, derived_type in _CAMPAIGN_TYPE_KEYWORDS
            if keyword in lowered_stem
        ),
        _DEFAULT_CAMPAIGN_TYPE,
    )

    return CampaignMetadata(
        name=stem,
        campaign_type=campaign_type,
        source_file=source_path.name,
    )


def _with_campaign_columns(
    products: pd.DataFrame,
    metadata: CampaignMetadata,
) -> pd.DataFrame:
    """Return a copy of the products frame with campaign identity columns first."""
    frame = products.copy()
    metadata_values = (metadata.name, metadata.campaign_type, metadata.source_file)
    for position, (column_name, value) in enumerate(
        zip(_METADATA_COLUMNS, metadata_values, strict=True)
    ):
        frame.insert(position, column_name, value)

    return frame


def _build_overall_summary(decisions: Sequence[ProductDecision]) -> OverallSummary:
    """Aggregate every campaign's decisions into one overall summary."""
    status_counts = {status: 0 for status in ProductStatus}
    for decision in decisions:
        status_counts[decision.status] += 1

    return OverallSummary(
        total_cost=sum(decision.cost for decision in decisions),
        total_revenue=sum(decision.conversion_value for decision in decisions),
        total_conversions=sum(decision.conversions for decision in decisions),
        total_products=len(decisions),
        keep=status_counts[ProductStatus.KEEP],
        watch=status_counts[ProductStatus.WATCH],
        pause=status_counts[ProductStatus.PAUSE],
        scale=status_counts[ProductStatus.SCALE],
    )


def _derive_overall_health(campaigns: Sequence[CampaignReport]) -> str:
    """Return the combined health across every campaign."""
    if all(campaign.health == _HEALTHY for campaign in campaigns):
        return _HEALTHY

    return _NEEDS_ATTENTION
