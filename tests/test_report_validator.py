"""Tests for report file validation."""

from pathlib import Path

import pandas as pd

from app.services.report_validator import ReportValidator


def _rows(sku: str, cost: object = 100.0) -> dict:
    """One well-formed product row."""
    return {
        "Item ID": sku,
        "Impressions": 1000,
        "Clicks": 10,
        "Cost": cost,
        "Conversions": 1.0,
        "Conversion Value": 500.0,
    }


def test_valid_file_produces_no_issues(tmp_path: Path) -> None:
    """A clean report validates successfully."""
    source_path = tmp_path / "clean.csv"
    pd.DataFrame([_rows("SKU-1"), _rows("SKU-2")]).to_csv(source_path, index=False)

    result = ReportValidator().validate([source_path])

    assert result.is_valid
    assert result.checked_files == 1


def test_unsupported_file_type_is_reported(tmp_path: Path) -> None:
    """Non-CSV/XLSX files are rejected without loading."""
    source_path = tmp_path / "report.txt"
    source_path.write_text("whatever", encoding="utf-8")

    result = ReportValidator().validate([source_path])

    assert not result.is_valid
    assert "Unsupported file type" in result.issues[0].message


def test_missing_required_columns_are_reported(tmp_path: Path) -> None:
    """A report without required columns fails validation."""
    source_path = tmp_path / "partial.csv"
    source_path.write_text("Product,Clicks\nA,10\n", encoding="utf-8")

    result = ReportValidator().validate([source_path])

    assert not result.is_valid
    assert "Missing required columns" in result.issues[0].message


def test_duplicated_skus_are_reported(tmp_path: Path) -> None:
    """Duplicate product identifiers are listed."""
    source_path = tmp_path / "duplicates.csv"
    pd.DataFrame([_rows("SKU-DUP"), _rows("SKU-DUP")]).to_csv(source_path, index=False)

    result = ReportValidator().validate([source_path])

    assert not result.is_valid
    assert "Duplicated SKUs (1): SKU-DUP" in result.issues[0].message


def test_invalid_numeric_values_are_reported(tmp_path: Path) -> None:
    """Metric cells that cannot be parsed as numbers are counted."""
    source_path = tmp_path / "invalid.csv"
    pd.DataFrame([_rows("SKU-1", cost="not-a-number")]).to_csv(source_path, index=False)

    result = ReportValidator().validate([source_path])

    assert not result.is_valid
    assert "invalid or missing numeric value(s) in column 'cost'" in result.issues[0].message


def test_missing_file_is_reported(tmp_path: Path) -> None:
    """A path that does not exist is a validation issue, not a crash."""
    result = ReportValidator().validate([tmp_path / "absent.csv"])

    assert not result.is_valid
    assert result.issues[0].message == "File not found."
