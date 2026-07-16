"""Integration tests for the complete application pipeline."""

from pathlib import Path

import pandas as pd
import pytest

from main import run


def test_run_processes_csv_and_prints_summary(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The CLI pipeline loads, analyzes, summarizes, audits, and reports."""
    source_path = tmp_path / "product_report.csv"
    pd.DataFrame(
        [
            {
                "Item ID": "KEEP-1",
                "Impressions": 1000,
                "Clicks": 10,
                "Cost": 100.0,
                "Conversions": 1.0,
                "Conversion Value": 700.0,
            },
            {
                "Item ID": "PAUSE-1",
                "Impressions": 1000,
                "Clicks": 10,
                "Cost": 150.0,
                "Conversions": 0.0,
                "Conversion Value": 0.0,
            },
        ]
    ).to_csv(source_path, index=False)

    exit_code = run(source_path)

    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.err == ""
    assert captured.out == (
        "Health: Needs attention | Products: 2 | Keep: 1 | Watch: 0 | Pause: 1 | Scale: 0\n"
    )


def test_run_returns_input_error_for_missing_file(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A missing report path produces a non-zero input-error status."""
    exit_code = run(tmp_path / "missing.csv")

    captured = capsys.readouterr()
    assert exit_code == 2
    assert captured.out == ""
    assert captured.err.startswith("Error:")


def test_run_with_explain_prints_decision_blocks(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The --explain mode prints one formatted explanation block per product."""
    source_path = tmp_path / "product_report.csv"
    pd.DataFrame(
        [
            {
                "Item ID": "PAUSE-1",
                "Impressions": 1000,
                "Clicks": 104,
                "Cost": 450.0,
                "Conversions": 0.0,
                "Conversion Value": 0.0,
            }
        ]
    ).to_csv(source_path, index=False)

    exit_code = run(source_path, explain=True)

    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.out.endswith(
        "SKU: PAUSE-1\n"
        "Decision: PAUSE\n"
        "Reason:\n"
        "Cost = 450\n"
        "Clicks = 104\n"
        "Conversions = 0\n"
        + "-" * 32
        + "\n"
    )
