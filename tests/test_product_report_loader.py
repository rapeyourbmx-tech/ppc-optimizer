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


def test_load_detects_ukrainian_header_row_after_preamble() -> None:
    """Rows before the "Зображення" header row are skipped automatically."""
    source_path = FIXTURES_DIRECTORY / "google_ads_product_uk.csv"

    report = GoogleAdsProductReportLoader().load(source_path)

    assert len(report) == 2
    assert report.loc[0, "product_id"] == "SKU-UA-001"
    assert report.loc[1, "product_id"] == "SKU-UA-002"
    assert report.loc[0, "conversion_value"] == 700.0


def test_load_detects_english_image_header_and_semicolon_delimiter() -> None:
    """The "Image" header row and a semicolon delimiter are detected automatically."""
    source_path = FIXTURES_DIRECTORY / "google_ads_product_en_semicolon.csv"

    report = GoogleAdsProductReportLoader().load(source_path)

    assert len(report) == 1
    assert report.loc[0, "product_id"] == "SKU-EN-100"
    assert report.loc[0, "clicks"] == 20
    assert report.loc[0, "all_conversion_value"] == 850.0


def test_load_preserves_commas_inside_quoted_product_names() -> None:
    """Commas inside quoted product names do not split the row into extra cells."""
    ukrainian_report = GoogleAdsProductReportLoader().load(
        FIXTURES_DIRECTORY / "google_ads_product_uk.csv"
    )
    english_report = GoogleAdsProductReportLoader().load(
        FIXTURES_DIRECTORY / "google_ads_product_en_semicolon.csv"
    )

    assert ukrainian_report.loc[0, "product"] == "Ноутбук Lenovo, 15,6 дюйма"
    assert english_report.loc[0, "product"] == "Laptop, 15 inch"


def test_load_reads_utf8_sig_export_without_bom_artifacts() -> None:
    """The UTF-8 BOM does not leak into the first mapped column name."""
    source_path = FIXTURES_DIRECTORY / "google_ads_product_uk.csv"
    raw_bytes = source_path.read_bytes()

    report = GoogleAdsProductReportLoader().load(source_path)

    assert raw_bytes.startswith(b"\xef\xbb\xbf")
    assert all(not str(column).startswith("\ufeff") for column in report.columns)


def test_load_detects_tab_delimited_export(tmp_path: Path) -> None:
    """Tab-delimited exports load through the same delimiter detection."""
    source_path = tmp_path / "google_ads_product_tab.csv"
    lines = [
        "Product report",
        "Image\tProduct ID\tProduct\tClicks\tImpressions\tCTR\tAverage CPC\tCost"
        "\tConversions\tConversion value\tCost / conv.\tAll conversions\tAll conv. value",
        "-\tSKU-EN-200\tTablet\t5\t500\t1.0%\t2.0\t10.0\t1.0\t90.0\t10.0\t1.0\t90.0",
    ]
    source_path.write_text("\n".join(lines) + "\n", encoding="utf-8-sig")

    report = GoogleAdsProductReportLoader().load(source_path)

    assert report.loc[0, "product_id"] == "SKU-EN-200"
    assert report.loc[0, "conversion_value"] == 90.0


def test_load_unwraps_fully_quoted_data_rows() -> None:
    """Exports whose data rows are wrapped in one extra quoting layer are unwrapped."""
    source_path = FIXTURES_DIRECTORY / "google_ads_product_uk_wrapped.csv"

    report = GoogleAdsProductReportLoader().load(source_path)

    assert len(report) == 2
    assert report.loc[0, "product_id"] == "SKU-WRAP-001"
    assert report.loc[1, "product"] == "Тестовий товар Б, варіант 570, 650"


def test_load_maps_item_and_title_ukrainian_header_variants() -> None:
    """"Ідентифікатор елемента" and "Назва" map to product_id and product."""
    source_path = FIXTURES_DIRECTORY / "google_ads_product_uk_wrapped.csv"

    report = GoogleAdsProductReportLoader().load(source_path)

    assert "product_id" in report.columns
    assert "product" in report.columns
    assert report.loc[0, "product"] == "Тестовий товар А"


def test_load_normalizes_ukrainian_locale_metric_values() -> None:
    """Currency prefixes, NBSP thousands separators, and decimal commas parse to floats."""
    source_path = FIXTURES_DIRECTORY / "google_ads_product_uk_wrapped.csv"

    report = GoogleAdsProductReportLoader().load(source_path)

    assert report.loc[0, "clicks"] == 38
    assert report.loc[0, "impressions"] == 13300
    assert report.loc[0, "cost"] == 276.76
    assert report.loc[0, "conversions"] == 0.96
    assert report.loc[0, "conversion_value"] == 4201.38
    assert report.loc[0, "all_conversion_value"] == 4201.38


def test_load_falls_back_to_first_row_without_image_header() -> None:
    """Plain exports without an image column keep loading from the first row."""
    source_path = FIXTURES_DIRECTORY / "google_ads_product_en.csv"

    report = GoogleAdsProductReportLoader().load(source_path)

    assert report.loc[0, "product_id"] == "SKU-EN-001"
    assert report.columns.tolist() == list(GOOGLE_ADS_PRODUCT_SCHEMA)


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
