"""Tests for friendly command-line error handling."""

from pathlib import Path

import pandas as pd
import pytest
from typer.testing import CliRunner

from main import application, run

runner = CliRunner()


def test_missing_column_prints_expected_and_found(tmp_path: Path) -> None:
    """A misspelled column produces the Expected/Found suggestion block."""
    source_path = tmp_path / "campaign.csv"
    pd.DataFrame(
        [
            {
                "Item ID": "SKU-1",
                "Impressions": 1000,
                "Clicks": 10,
                "Cost": 350.0,
                "Conversion": 2.0,
                "Conversion Value": 700.0,
            }
        ]
    ).to_csv(source_path, index=False)

    result = runner.invoke(application, [str(source_path)])

    assert result.exit_code == 1
    assert "ERROR" in result.output
    assert 'Column "Conversions" not found.' in result.output
    assert "Expected:\nConversions" in result.output
    assert "Found:\nConversion" in result.output
    assert "Traceback" not in result.output


def test_unsupported_file_type_prints_expected_formats(tmp_path: Path) -> None:
    """A non-CSV/XLSX input produces the friendly format message."""
    source_path = tmp_path / "report.txt"
    source_path.write_text("data", encoding="utf-8")

    result = runner.invoke(application, [str(source_path)])

    assert result.exit_code == 1
    assert "Unsupported file type." in result.output
    assert "Expected:\nCSV or XLSX" in result.output
    assert "Traceback" not in result.output


def test_configuration_error_exits_with_code_two(tmp_path: Path) -> None:
    """A broken configuration file is a configuration error."""
    source_path = tmp_path / "campaign.csv"
    pd.DataFrame(
        [
            {
                "Item ID": "SKU-1",
                "Impressions": 1000,
                "Clicks": 10,
                "Cost": 350.0,
                "Conversions": 2.0,
                "Conversion Value": 700.0,
            }
        ]
    ).to_csv(source_path, index=False)
    config_path = tmp_path / "config.yaml"
    config_path.write_text("pasue:\n  min_cost: 300\n", encoding="utf-8")

    result = runner.invoke(
        application,
        [str(source_path), "--config", str(config_path)],
    )

    assert result.exit_code == 2
    assert "Configuration problem." in result.output
    assert "Traceback" not in result.output


def test_internal_error_exits_with_code_three(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """An unexpected exception becomes a friendly internal error."""

    class ExplodingPipeline:
        def run(self, source_path: Path) -> None:
            message = "unexpected failure"
            raise RuntimeError(message)

    source_path = tmp_path / "campaign.csv"
    source_path.write_text("Item ID\nSKU-1\n", encoding="utf-8")

    exit_code = run(source_path, pipeline=ExplodingPipeline())

    captured = capsys.readouterr()
    assert exit_code == 3
    assert "Internal error: RuntimeError: unexpected failure" in captured.err
    assert "Please report this issue." in captured.err
    assert "Traceback" not in captured.err
