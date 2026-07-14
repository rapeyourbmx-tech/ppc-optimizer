"""Loader for Google Ads product reports stored in CSV or XLSX files."""

from pathlib import Path

import pandas as pd

from app.loaders.google_ads_product_report_mapper import GoogleAdsProductReportMapper


class UnsupportedReportFormatError(ValueError):
    """Raised when a report file is not a supported CSV or XLSX file."""


class GoogleAdsProductReportLoader:
    """Load a Google Ads product report into a normalized data frame."""

    _CSV_SUFFIX = ".csv"
    _XLSX_SUFFIX = ".xlsx"

    def __init__(self, mapper: GoogleAdsProductReportMapper | None = None) -> None:
        """Initialize the loader with the Google Ads export header mapper."""
        self._mapper = mapper or GoogleAdsProductReportMapper()

    def load(self, source_path: Path) -> pd.DataFrame:
        """Load a CSV or XLSX report and normalize its column names.

        Args:
            source_path: Path to the Google Ads product report export.

        Returns:
            A pandas data frame with normalized column names.

        Raises:
            UnsupportedReportFormatError: If the file is not CSV or XLSX.
        """
        suffix = source_path.suffix.casefold()

        if suffix == self._CSV_SUFFIX:
            report = pd.read_csv(source_path)
        elif suffix == self._XLSX_SUFFIX:
            report = pd.read_excel(source_path)
        else:
            message = "Only CSV and XLSX Google Ads product reports are supported."
            raise UnsupportedReportFormatError(message)

        return self._mapper.map(report)
