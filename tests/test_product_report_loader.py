"""Tests for the Google Ads product report loader."""

from pathlib import Path

import pandas as pd
import pytest

from app.loaders.product_report_loader import (
    GoogleAdsProductReportLoader,
    UnsupportedReportFormatError,
)


def test_load_reads_csv_and_normalizes_column_names(tmp_path: Path) -> None:
    """CSV reports are returned with snake_case column names."""
    source_path = tmp_path / "product_report.csv"
    expected_report = pd.DataFrame(
        {"item_id": ["SKU-001"], "product_title": ["Example product"], "cost_usd": [12.5]}
    )
    expected_report.rename(
        columns={"item_id": "Item ID", "product_title": "Product Title", "cost_usd": "Cost (USD)"}
    ).to_csv(source_path, index=False)

    report = GoogleAdsProductReportLoader().load(source_path)

    pd.testing.assert_frame_equal(report, expected_report)


def test_load_reads_xlsx_and_normalizes_column_names(tmp_path: Path) -> None:
    """XLSX reports are returned with snake_case column names."""
    source_path = tmp_path / "product_report.xlsx"
    expected_report = pd.DataFrame({"item_id": ["SKU-002"], "clicks": [14]})
    expected_report.rename(columns={"item_id": "Item ID", "clicks": "Clicks"}).to_excel(
        source_path,
        index=False,
    )

    report = GoogleAdsProductReportLoader().load(source_path)

    pd.testing.assert_frame_equal(report, expected_report)


def test_load_rejects_unsupported_file_types(tmp_path: Path) -> None:
    """Files other than CSV and XLSX are rejected."""
    source_path = tmp_path / "product_report.txt"
    source_path.write_text("Item ID,Clicks\nSKU-003,4\n", encoding="utf-8")

    with pytest.raises(UnsupportedReportFormatError, match="Only CSV and XLSX"):
        GoogleAdsProductReportLoader().load(source_path)
