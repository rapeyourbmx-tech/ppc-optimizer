"""Header mapping for Google Ads statistics exports."""

import pandas as pd

from app.loaders.google_ads_product_report_mapper import (
    GoogleAdsProductReportMapper,
    MissingColumnsError,
)


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
