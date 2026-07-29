"""Analysis of multiple Google Ads product reports in one run."""

from collections.abc import Sequence
from pathlib import Path

import pandas as pd

from app.analyzers.audit_engine import AuditEngine
from app.analyzers.product_analyzer import ProductAnalyzer
from app.config import ThresholdConfiguration
from app.loaders.product_report_loader import GoogleAdsProductReportLoader
from app.models.campaign import (
    CampaignMetadata,
    CampaignReport,
    MultiCampaignReport,
    OverallSummary,
)
from app.models.product_decision import ProductDecision, ProductStatus
from app.models.report import ProductReport
from app.services.application_pipeline import ApplicationPipeline, PipelineResult

_HEALTHY = "Healthy"
_NEEDS_ATTENTION = "Needs attention"
_CAMPAIGN_TYPE_KEYWORDS: tuple[tuple[str, str], ...] = (
    ("high", "High priority"),
    ("хай", "High priority"),
    ("висок", "High priority"),
    ("average", "Medium priority"),
    ("аверейдж", "Medium priority"),
    ("середн", "Medium priority"),
    ("medium", "Medium priority"),
    ("low", "Low priority"),
    ("лоу", "Low priority"),
    ("лов", "Low priority"),
    ("низьк", "Low priority"),
)
_DEFAULT_CAMPAIGN_TYPE = "Standard"
_CAMPAIGN_NAME_COLUMNS: tuple[str, ...] = (
    "кампанія",
    "campaign",
    "назва_кампанії",
    "campaign_name",
)
_METADATA_COLUMNS: tuple[str, ...] = ("campaign_name", "campaign_type", "source_file")


class MultiCampaignAnalyzer:
    """Analyze several product reports and combine them into one report."""

    def __init__(
        self,
        configuration: ThresholdConfiguration | None = None,
        pipeline: ApplicationPipeline | None = None,
    ) -> None:
        """Initialize the analyzer.

        Args:
            configuration: Thresholds with optional per-campaign overrides,
                used to build one pipeline per campaign.
            pipeline: Explicit pipeline reused for every campaign; overrides
                the configuration when provided.
        """
        self._configuration = configuration or ThresholdConfiguration()
        self._shared_pipeline = pipeline
        self._loader = GoogleAdsProductReportLoader()

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
            for metadata, result in self._campaign_segments(source_path):
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

    def _campaign_segments(
        self,
        source_path: Path,
    ) -> list[tuple[CampaignMetadata, PipelineResult]]:
        """Split one report file into campaigns and analyze each of them.

        When the export carries a campaign column, every distinct value
        becomes its own campaign with the matching thresholds; otherwise
        the whole file is one campaign identified by its file name.
        """
        if self._shared_pipeline is not None:
            metadata = _derive_campaign_metadata(source_path)
            return [(metadata, self._shared_pipeline.run(source_path))]

        products = self._loader.load(source_path)
        campaign_column = next(
            (
                column_name
                for column_name in _CAMPAIGN_NAME_COLUMNS
                if column_name in products.columns
            ),
            None,
        )
        if campaign_column is None:
            metadata = _derive_campaign_metadata(source_path)
            pipeline = self._pipeline_for(metadata.name)
            return [(metadata, pipeline.run_products(products))]

        segments: list[tuple[CampaignMetadata, PipelineResult]] = []
        for campaign_value, campaign_products in products.groupby(
            campaign_column, sort=False, dropna=False
        ):
            campaign_name = (
                str(campaign_value) if not pd.isna(campaign_value) else source_path.stem
            )
            metadata = CampaignMetadata(
                name=campaign_name,
                campaign_type=_campaign_type_for(campaign_name),
                source_file=source_path.name,
            )
            pipeline = self._pipeline_for(campaign_name)
            segments.append(
                (metadata, pipeline.run_products(campaign_products.reset_index(drop=True)))
            )

        return segments

    def _pipeline_for(self, campaign_name: str) -> ApplicationPipeline:
        """Return the pipeline for one campaign with its effective thresholds."""
        if self._shared_pipeline is not None:
            return self._shared_pipeline

        thresholds = self._configuration.thresholds_for_campaign(campaign_name)
        return ApplicationPipeline(
            product_analyzer=ProductAnalyzer(thresholds=thresholds),
            audit_engine=AuditEngine(thresholds=self._configuration.audit),
        )


def _derive_campaign_metadata(source_path: Path) -> CampaignMetadata:
    """Derive a campaign identity from one report file path."""
    stem = source_path.stem

    return CampaignMetadata(
        name=stem,
        campaign_type=_campaign_type_for(stem),
        source_file=source_path.name,
    )


def _campaign_type_for(campaign_name: str) -> str:
    """Derive the campaign type from a campaign or file name."""
    lowered_name = campaign_name.casefold()
    return next(
        (
            derived_type
            for keyword, derived_type in _CAMPAIGN_TYPE_KEYWORDS
            if keyword in lowered_name
        ),
        _DEFAULT_CAMPAIGN_TYPE,
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
