"""Tests for Google Ads Product report loading and header mapping."""

from pathlib import Path

import pandas as pd
import pytest

from app.loaders.google_ads_product_report_mapper import (
    GOOGLE_ADS_PRODUCT_SCHEMA,
    GoogleAdsProductReportMappingError,
)
from app.loaders.product_report_loader import (
    GoogleAdsProductReportLoader,
    UnsupportedReportFormatError,
)


FIXTURES_DIRECTORY = Path(__file__).parent / "fixtures"
@pytest.fixture
def ukrainian_xlsx_report(tmp_path: Path) -> Path:
    """Create a Ukrainian Google Ads XLSX export fixture."""
    source_path = tmp_path / "google_ads_product_uk.xlsx"
    pd.DataFrame(
        [
            {
                "Ідентифікатор товару": "SKU-UA-001",
                "Товар": "Український товар",
                "Кліки": 12,
                "Покази": 800,
                "CTR": "1.5%",
                "Сер. ціна за клік": 8.5,
                "Вартість": 102.0,
                "Конверсії": 2.0,
                "Цінність конверсії": 700.0,
                "Вартість/конв.": 51.0,
                "Усі конверсії": 3.0,
                "Цінність усіх конв.": 850.0,
            }
        ]
    ).to_excel(source_path, index=False)
    return source_path


def test_load_maps_english_csv_fixture_to_internal_schema() -> None:
    """English Google Ads CSV exports map to the canonical internal headers."""
    source_path = FIXTURES_DIRECTORY / "google_ads_product_en.csv"

    report = GoogleAdsProductReportLoader().load(source_path)

    assert report.columns.tolist() == list(GOOGLE_ADS_PRODUCT_SCHEMA)
    assert report.loc[0, "product_id"] == "SKU-EN-001"
    assert report.loc[0, "conversion_value"] == 700.0
    assert report.loc[0, "all_conversion_value"] == 850.0


def test_load_maps_ukrainian_xlsx_fixture_to_internal_schema(
    ukrainian_xlsx_report: Path,
) -> None:
    """Ukrainian Google Ads XLSX exports map to the canonical internal headers."""
    report = GoogleAdsProductReportLoader().load(ukrainian_xlsx_report)

    assert report.columns.tolist() == list(GOOGLE_ADS_PRODUCT_SCHEMA)
    assert report.loc[0, "product_id"] == "SKU-UA-001"
    assert report.loc[0, "average_cpc"] == 8.5
    assert report.loc[0, "cost_per_conversion"] == 51.0


def test_load_reports_missing_required_google_ads_columns(tmp_path: Path) -> None:
    """Incomplete exports produce an informative missing-column error."""
    source_path = tmp_path / "incomplete_google_ads_report.csv"
    pd.DataFrame(
        {
            "Product ID": ["SKU-001"],
            "Clicks": [10],
            "Impressions": [100],
            "Cost": [50.0],
        }
    ).to_csv(source_path, index=False)

    with pytest.raises(GoogleAdsProductReportMappingError) as error:
        GoogleAdsProductReportLoader().load(source_path)

    assert "Missing required columns: conversion_value, conversions." in str(error.value)


def test_load_rejects_unsupported_file_types(tmp_path: Path) -> None:
    """Files other than CSV and XLSX are rejected."""
    source_path = tmp_path / "product_report.txt"
    source_path.write_text("Product ID,Clicks\nSKU-003,4\n", encoding="utf-8")

    with pytest.raises(UnsupportedReportFormatError, match="Only CSV and XLSX"):
        GoogleAdsProductReportLoader().load(source_path)
