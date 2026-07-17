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
                "Cost": 350.0,
                "Conversions": 2.0,
                "Conversion Value": 700.0,
            },
            {
                "Item ID": "PAUSE-1",
                "Impressions": 1000,
                "Clicks": 10,
                "Cost": 450.0,
                "Conversions": 0.0,
                "Conversion Value": 0.0,
            },
        ]
    ).to_csv(source_path, index=False)

    exit_code = run(source_path, output_path=tmp_path / "report.xlsx")

    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.err == ""
    assert captured.out.startswith(
        "Health: Needs attention | Products: 2 | Keep: 1 | Watch: 0 | Pause: 1 | Scale: 0\n"
    )
    assert "Report saved:" in captured.out
    assert (tmp_path / "report.xlsx").is_file()


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

    exit_code = run(source_path, explain=True, output_path=tmp_path / "report.xlsx")

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


def test_run_applies_custom_threshold_configuration(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A custom --config file changes the decision outcome."""
    source_path = tmp_path / "product_report.csv"
    pd.DataFrame(
        [
            {
                "Item ID": "LOW-SPEND-1",
                "Impressions": 1000,
                "Clicks": 10,
                "Cost": 150.0,
                "Conversions": 0.0,
                "Conversion Value": 0.0,
            }
        ]
    ).to_csv(source_path, index=False)
    config_path = tmp_path / "strict.yaml"
    config_path.write_text("watch:\n  max_cost: 10\npause:\n  min_cost: 10\n", encoding="utf-8")

    default_exit_code = run(source_path, output_path=tmp_path / "report.xlsx")
    default_output = capsys.readouterr().out
    strict_exit_code = run(source_path, config_path=config_path, output_path=tmp_path / "report.xlsx")
    strict_output = capsys.readouterr().out

    assert default_exit_code == 0
    assert strict_exit_code == 0
    assert "Watch: 1 | Pause: 0" in default_output
    assert "Watch: 0 | Pause: 1" in strict_output
