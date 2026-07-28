"""Import of product statistics from Google Ads CSV/XLSX report files."""

from pathlib import Path

import pandas as pd

from app.loaders import metric_normalizer
from app.loaders.google_ads_product_report_mapper import (
    GoogleAdsProductReportMapper,
    MissingColumnsError,
)
from app.loaders.product_report_loader import GoogleAdsProductReportLoader
from app.models.product_statistics import ProductStatistics

_REVENUE_COLUMNS: tuple[str, ...] = ("direct_revenue", "assist_revenue")


class GoogleAdsStatisticsReportMapper(GoogleAdsProductReportMapper):
    """Header mapping for statistics exports with revenue split columns.

    Extends the base export mapper with Offer ID, Direct Revenue, and
    Cross-sell Revenue headers (the last one maps to the internal
    assist_revenue field) and requires the statistics field set instead
    of the base report field set.
    """

    _COLUMN_ALIASES: dict[str, tuple[str, ...]] = {
        **GoogleAdsProductReportMapper._COLUMN_ALIASES,
        "product_id": (
            *GoogleAdsProductReportMapper._COLUMN_ALIASES["product_id"],
            "offer_id",
            "ідентифікатор_пропозиції",
        ),
        "direct_revenue": (
            "direct_revenue",
            "прямий_дохід",
            "дохід_від_прямих_продажів",
        ),
        "assist_revenue": (
            "cross_sell_revenue",
            "assist_revenue",
            "дохід_від_перехресних_продажів",
            "перехресний_дохід",
        ),
    }
    _REQUIRED_STATISTICS_COLUMNS: tuple[str, ...] = (
        "product_id",
        "cost",
        "clicks",
        "impressions",
        "direct_revenue",
        "assist_revenue",
        "conversions",
    )

    def _validate_required_columns(
        self,
        report: pd.DataFrame,
        original_columns: list[str],
    ) -> None:
        """Ensure the export carries every statistics field."""
        missing_columns = sorted(set(self._REQUIRED_STATISTICS_COLUMNS) - set(report.columns))
        if missing_columns:
            names = ", ".join(missing_columns)
            message = (
                "The file is not a complete Google Ads statistics report. "
                f"Missing required columns: {names}."
            )
            raise MissingColumnsError(
                message,
                missing_columns=missing_columns,
                available_columns=original_columns,
            )


class GoogleAdsReportImporter:
    """Import product statistics from a Google Ads CSV or XLSX export.

    The importer is file-based by design and never talks to the
    Google Ads API. It reuses the existing report loader (header
    detection, delimiter sniffing, locale-aware numbers) with a
    statistics-specific header mapping.
    """

    def __init__(self, loader: GoogleAdsProductReportLoader | None = None) -> None:
        """Initialize the importer with a statistics-aware report loader."""
        self._loader = loader or GoogleAdsProductReportLoader(
            mapper=GoogleAdsStatisticsReportMapper()
        )

    def import_report(self, source_path: Path) -> list[ProductStatistics]:
        """Read one CSV or XLSX export into product statistics records.

        Args:
            source_path: Path to the Google Ads statistics export.

        Returns:
            One ProductStatistics record per export row, in file order.

        Raises:
            MissingColumnsError: If a required statistics column is absent.
            UnsupportedReportFormatError: If the file is not CSV or XLSX.
        """
        frame = self._loader.load(source_path)
        frame = self._normalize_revenue_columns(frame)

        return [
            ProductStatistics(
                offer_id=str(row.product_id),
                cost=float(row.cost),
                clicks=int(row.clicks),
                impressions=int(row.impressions),
                direct_revenue=float(row.direct_revenue),
                assist_revenue=float(row.assist_revenue),
                conversions=float(row.conversions),
            )
            for row in frame.fillna({"product_id": "", "cost": 0.0, "clicks": 0, "impressions": 0})
            .fillna(0.0)
            .itertuples(index=False)
        ]

    @staticmethod
    def _normalize_revenue_columns(frame: pd.DataFrame) -> pd.DataFrame:
        """Convert the revenue split columns to numeric values.

        The shared loader normalizes only the base metric columns, so the
        statistics-specific revenue columns are normalized here with the
        same locale-aware routine (module-internal by design).
        """
        normalized_frame = frame.copy()
        for column_name in _REVENUE_COLUMNS:
            normalized_frame[column_name] = metric_normalizer._to_numeric(  # noqa: SLF001
                normalized_frame[column_name]
            )

        return normalized_frame
