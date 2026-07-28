"""Import of product statistics from Google Ads CSV/XLSX report files."""

from pathlib import Path

from app.loaders.google_ads_statistics_report_mapper import (
    GoogleAdsStatisticsReportMapper,
)
from app.loaders.product_report_loader import GoogleAdsProductReportLoader
from app.models.product_statistics import ProductStatistics

_REVENUE_COLUMNS: tuple[str, ...] = ("direct_revenue", "assist_revenue")


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
