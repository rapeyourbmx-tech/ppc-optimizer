"""Tests for the Google Ads statistics report importer."""

from pathlib import Path

import pandas as pd
import pytest

from app.importers import GoogleAdsReportImporter
from app.loaders.google_ads_product_report_mapper import MissingColumnsError

_NBSP = "\u00a0"


def _statistics_rows() -> list[dict]:
    """Two well-formed statistics rows with English headers."""
    return [
        {
            "Offer ID": "SKU-100",
            "Cost": 1250.5,
            "Clicks": 12,
            "Impressions": 3400,
            "Direct Revenue": 10000.0,
            "Cross-sell Revenue": 2500.25,
            "Conversions": 1.5,
        },
        {
            "Offer ID": "SKU-200",
            "Cost": 80.0,
            "Clicks": 4,
            "Impressions": 900,
            "Direct Revenue": 0.0,
            "Cross-sell Revenue": 0.0,
            "Conversions": 0.0,
        },
    ]


def test_import_reads_every_field_from_csv(tmp_path: Path) -> None:
    """CSV exports produce one record per row with every field populated."""
    source_path = tmp_path / "statistics.csv"
    pd.DataFrame(_statistics_rows()).to_csv(source_path, index=False)

    records = GoogleAdsReportImporter().import_report(source_path)

    assert len(records) == 2
    first = records[0]
    assert first.offer_id == "SKU-100"
    assert first.cost == 1250.5
    assert first.clicks == 12
    assert first.impressions == 3400
    assert first.direct_revenue == 10000.0
    assert first.assist_revenue == 2500.25
    assert first.conversions == 1.5


def test_import_reads_xlsx_exports(tmp_path: Path) -> None:
    """XLSX exports import identically to CSV."""
    source_path = tmp_path / "statistics.xlsx"
    pd.DataFrame(_statistics_rows()).to_excel(source_path, index=False)

    records = GoogleAdsReportImporter().import_report(source_path)

    assert [record.offer_id for record in records] == ["SKU-100", "SKU-200"]
    assert records[0].effective_revenue == 12500.25


def test_effective_revenue_is_direct_plus_assist(tmp_path: Path) -> None:
    """effectiveRevenue equals directRevenue plus assistRevenue."""
    source_path = tmp_path / "statistics.csv"
    pd.DataFrame(_statistics_rows()).to_csv(source_path, index=False)

    records = GoogleAdsReportImporter().import_report(source_path)

    for record in records:
        assert record.effective_revenue == (record.direct_revenue + record.assist_revenue)


def test_import_normalizes_locale_formatted_numbers(tmp_path: Path) -> None:
    """Currency prefixes, NBSP separators, and decimal commas are parsed."""
    source_path = tmp_path / "statistics.csv"
    pd.DataFrame(
        [
            {
                "Offer ID": "SKU-UA",
                "Cost": f"грн1{_NBSP}250,50",
                "Clicks": "12",
                "Impressions": f"3{_NBSP}400",
                "Direct Revenue": f"грн10{_NBSP}000,00",
                "Cross-sell Revenue": "2 500,25",
                "Conversions": "1,5",
            }
        ]
    ).to_csv(source_path, index=False)

    records = GoogleAdsReportImporter().import_report(source_path)

    record = records[0]
    assert record.cost == 1250.5
    assert record.impressions == 3400
    assert record.effective_revenue == 12500.25


def test_import_rejects_export_without_cross_sell_revenue(tmp_path: Path) -> None:
    """A missing statistics column raises the enriched mapping error."""
    rows = [
        {key: value for key, value in row.items() if key != "Cross-sell Revenue"}
        for row in _statistics_rows()
    ]
    source_path = tmp_path / "statistics.csv"
    pd.DataFrame(rows).to_csv(source_path, index=False)

    with pytest.raises(MissingColumnsError) as error_info:
        GoogleAdsReportImporter().import_report(source_path)

    assert "assist_revenue" in error_info.value.missing_columns


def test_import_accepts_base_report_identifier_aliases(tmp_path: Path) -> None:
    """Item ID exports import as well as Offer ID exports."""
    rows = _statistics_rows()
    for row in rows:
        row["Item ID"] = row.pop("Offer ID")
    source_path = tmp_path / "statistics.csv"
    pd.DataFrame(rows).to_csv(source_path, index=False)

    records = GoogleAdsReportImporter().import_report(source_path)

    assert records[0].offer_id == "SKU-100"
