"""Automatic detection of the Google Ads report type by its columns."""

from enum import StrEnum

import pandas as pd

from app.loaders.google_ads_product_report_mapper import (
    _REQUIRED_COLUMNS as _BASE_REQUIRED_COLUMNS,
)
from app.loaders.google_ads_product_report_mapper import (
    GoogleAdsProductReportMapper,
    MissingColumnsError,
)
from app.loaders.google_ads_statistics_report_mapper import (
    GoogleAdsStatisticsReportMapper,
)
from app.utils.column_names import normalize_column_names


class ReportType(StrEnum):
    """Supported Google Ads report formats."""

    BASE = "base"
    STATISTICS = "statistics"


class AutoDetectingReportMapper:
    """Route a report to the base or statistics mapper by its columns.

    A report with the revenue split (Direct Revenue and Cross-sell
    Revenue, in any supported locale) is mapped as a statistics report,
    even when a conversion value column is also present. A report with a
    conversion value column and no split is mapped as a base report.
    """

    def __init__(
        self,
        base_mapper: GoogleAdsProductReportMapper | None = None,
        statistics_mapper: GoogleAdsStatisticsReportMapper | None = None,
    ) -> None:
        """Initialize the detector with both concrete mappers."""
        self._base_mapper = base_mapper or GoogleAdsProductReportMapper()
        self._statistics_mapper = statistics_mapper or GoogleAdsStatisticsReportMapper()

    def map(self, report: pd.DataFrame) -> pd.DataFrame:
        """Map the report with the mapper matching its detected type."""
        if self.detect(report) is ReportType.STATISTICS:
            return self._statistics_mapper.map(report)

        return self._base_mapper.map(report)

    def detect(self, report: pd.DataFrame) -> ReportType:
        """Detect the report type from the columns present.

        Raises:
            MissingColumnsError: If the columns match neither format; the
                error lists the missing required columns of the closest
                format and names both formats in the message.
        """
        normalized_columns = set(normalize_column_names(report.head(0)).columns)
        statistics_aliases = self._statistics_mapper._COLUMN_ALIASES  # noqa: SLF001

        has_revenue_split = all(
            self._is_derivable(canonical, statistics_aliases, normalized_columns)
            for canonical in ("direct_revenue", "assist_revenue")
        )
        if has_revenue_split:
            return ReportType.STATISTICS

        base_aliases = self._base_mapper._COLUMN_ALIASES  # noqa: SLF001
        if self._is_derivable("conversion_value", base_aliases, normalized_columns):
            return ReportType.BASE

        raise self._unrecognized_format_error(report, normalized_columns)

    @staticmethod
    def _is_derivable(
        canonical_name: str,
        aliases: dict[str, tuple[str, ...]],
        normalized_columns: set[str],
    ) -> bool:
        """Return True when a canonical column can be derived from the report."""
        candidate_names = (canonical_name, *aliases.get(canonical_name, ()))
        return any(name in normalized_columns for name in candidate_names)

    def _unrecognized_format_error(
        self,
        report: pd.DataFrame,
        normalized_columns: set[str],
    ) -> MissingColumnsError:
        """Build the error for a report matching neither format."""
        base_missing = self._missing_columns(
            _BASE_REQUIRED_COLUMNS,
            self._base_mapper._COLUMN_ALIASES,  # noqa: SLF001
            normalized_columns,
        )
        statistics_missing = self._missing_columns(
            self._statistics_mapper._REQUIRED_STATISTICS_COLUMNS,  # noqa: SLF001
            self._statistics_mapper._COLUMN_ALIASES,  # noqa: SLF001
            normalized_columns,
        )
        closest_missing = (
            statistics_missing
            if len(statistics_missing) < len(base_missing)
            else base_missing
        )
        message = (
            "The file matches neither a base Google Ads product report nor a "
            "statistics report. "
            f"Base report is missing: {', '.join(base_missing)}. "
            f"Statistics report is missing: {', '.join(statistics_missing)}."
        )
        return MissingColumnsError(
            message,
            missing_columns=closest_missing,
            available_columns=[str(column) for column in report.columns],
        )

    def _missing_columns(
        self,
        required_columns: tuple[str, ...],
        aliases: dict[str, tuple[str, ...]],
        normalized_columns: set[str],
    ) -> list[str]:
        """Return the required columns a report cannot provide."""
        return sorted(
            canonical
            for canonical in required_columns
            if not self._is_derivable(canonical, aliases, normalized_columns)
        )
