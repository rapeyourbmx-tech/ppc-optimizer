"""Tests for automatic Google Ads report type detection."""

from pathlib import Path

import pandas as pd
import pytest

from app.loaders.google_ads_product_report_mapper import MissingColumnsError
from app.loaders.report_type_detection import AutoDetectingReportMapper, ReportType
from app.services.multi_campaign_analyzer import MultiCampaignAnalyzer
from main import run

_NBSP = "\u00a0"


def _base_frame() -> pd.DataFrame:
    """A report with the conversion value column only."""
    return pd.DataFrame(
        [
            {
                "Item ID": "BASE-1",
                "Impressions": 1000,
                "Clicks": 10,
                "Cost": 100.0,
                "Conversions": 1.0,
                "Conversion Value": 500.0,
            }
        ]
    )


def _statistics_frame(**overrides: float) -> pd.DataFrame:
    """A report with the revenue split columns."""
    row = {
        "Offer ID": "STAT-1",
        "Impressions": 1000,
        "Clicks": 10,
        "Cost": 100.0,
        "Conversions": 1.0,
        "Direct Revenue": 800.0,
        "Cross-sell Revenue": 200.0,
    }
    row.update(overrides)
    return pd.DataFrame([row])


def test_detects_base_report() -> None:
    """A conversion value column selects the base mode."""
    assert AutoDetectingReportMapper().detect(_base_frame()) is ReportType.BASE


def test_detects_statistics_report() -> None:
    """The revenue split columns select the statistics mode."""
    detected = AutoDetectingReportMapper().detect(_statistics_frame())

    assert detected is ReportType.STATISTICS


def test_statistics_mode_wins_when_both_sets_present() -> None:
    """A file with both column sets is treated as a statistics report."""
    frame = _statistics_frame()
    frame["Conversion Value"] = 100.0

    assert AutoDetectingReportMapper().detect(frame) is ReportType.STATISTICS


def test_unrecognized_format_lists_missing_columns_of_both_formats() -> None:
    """A file matching neither format names both missing column sets."""
    frame = pd.DataFrame([{"Item ID": "X-1", "Clicks": 5}])

    with pytest.raises(MissingColumnsError) as error_info:
        AutoDetectingReportMapper().detect(frame)

    message = str(error_info.value)
    assert "matches neither" in message
    assert "Base report is missing" in message
    assert "Statistics report is missing" in message
    assert "conversion_value" in message
    assert "direct_revenue" in message
    assert error_info.value.missing_columns


def test_statistics_file_flows_through_the_analyzer_without_flags(
    tmp_path: Path,
) -> None:
    """A statistics export is analyzed end to end; decisions use the split sum."""
    source_path = tmp_path / "statistics.csv"
    _statistics_frame().to_csv(source_path, index=False)

    report = MultiCampaignAnalyzer().analyze([source_path])

    decision = report.decisions[0]
    assert decision.effective_revenue == 1000.0
    assert report.overall_summary.total_products == 1


def test_split_columns_override_conversion_value_in_decisions(
    tmp_path: Path,
) -> None:
    """With both sets present the decision revenue is direct plus assist."""
    frame = _statistics_frame()
    frame["Conversion Value"] = 100.0
    source_path = tmp_path / "mixed.csv"
    frame.to_csv(source_path, index=False)

    report = MultiCampaignAnalyzer().analyze([source_path])

    assert report.decisions[0].effective_revenue == 1000.0


def test_statistics_file_with_locale_numbers_via_cli(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The CLI analyzes a locale-formatted statistics export without flags."""
    monkeypatch.chdir(tmp_path)
    source_path = tmp_path / "statistics.csv"
    _statistics_frame(
        **{
            "Cost": f"грн1{_NBSP}250,50",
            "Direct Revenue": f"грн10{_NBSP}000,00",
            "Cross-sell Revenue": "2 500,25",
        }
    ).to_csv(source_path, index=False)

    exit_code = run(source_path, dry_run=True)

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Products: 1" in captured.out


def test_validate_accepts_statistics_exports(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """--validate recognizes statistics files automatically."""
    monkeypatch.chdir(tmp_path)
    source_path = tmp_path / "statistics.csv"
    _statistics_frame().to_csv(source_path, index=False)

    exit_code = run(source_path, validate=True)

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Validation passed" in captured.out


def test_statistics_file_generates_a_workbook(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A statistics export produces a workbook with effective revenue."""
    monkeypatch.chdir(tmp_path)
    source_path = tmp_path / "statistics.csv"
    _statistics_frame().to_csv(source_path, index=False)
    output_path = tmp_path / "report.xlsx"

    exit_code = run(source_path, output_path=output_path)

    assert exit_code == 0
    assert output_path.is_file()
    from openpyxl import load_workbook

    workbook = load_workbook(output_path)
    header_values = [cell.value for cell in workbook["Products"][1]]
    assert "Effective Revenue" in header_values
    watch_values = [cell.value for cell in workbook["WATCH"][2]]
    assert 1000.0 in watch_values
