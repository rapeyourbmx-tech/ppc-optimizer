"""Tests for the production command-line interface."""

from pathlib import Path

import pandas as pd
import pytest
from typer.testing import CliRunner

from app.version import __version__
from main import application

runner = CliRunner()


@pytest.fixture
def report_file(tmp_path: Path) -> Path:
    """One valid single-product report file."""
    source_path = tmp_path / "campaign.csv"
    pd.DataFrame(
        [
            {
                "Item ID": "CLI-1",
                "Impressions": 1000,
                "Clicks": 10,
                "Cost": 350.0,
                "Conversions": 2.0,
                "Conversion Value": 700.0,
            }
        ]
    ).to_csv(source_path, index=False)
    return source_path


def test_version_prints_name_and_version_on_separate_lines() -> None:
    """--version prints the name and the v-prefixed version, then exits 0."""
    result = runner.invoke(application, ["--version"])

    assert result.exit_code == 0
    assert "PPC Optimizer\nv" + __version__ in result.output


def test_backward_compatible_invocation(report_file: Path, tmp_path: Path) -> None:
    """A bare file argument analyzes and writes the workbook as before."""
    output_path = tmp_path / "report.xlsx"

    result = runner.invoke(
        application,
        [str(report_file), "--output", str(output_path)],
    )

    assert result.exit_code == 0
    assert "Health:" in result.output
    assert output_path.is_file()


def test_dry_run_skips_workbook(report_file: Path, tmp_path: Path) -> None:
    """--dry-run prints the summary without creating the workbook."""
    output_path = tmp_path / "report.xlsx"

    result = runner.invoke(
        application,
        [str(report_file), "--output", str(output_path), "--dry-run"],
    )

    assert result.exit_code == 0
    assert "Health:" in result.output
    assert "Report saved" not in result.output
    assert not output_path.exists()


def test_verbose_prints_progress_stages(report_file: Path, tmp_path: Path) -> None:
    """--verbose prints every progress stage in order."""
    result = runner.invoke(
        application,
        [str(report_file), "--output", str(tmp_path / "report.xlsx"), "--verbose"],
    )

    stages = [
        "Loading configuration...",
        "Loading reports...",
        "Analyzing products...",
        "Generating workbook...",
        "Done.",
    ]
    positions = [result.output.find(stage) for stage in stages]
    assert result.exit_code == 0
    assert all(position >= 0 for position in positions)
    assert positions == sorted(positions)


def test_validate_passes_for_clean_file(report_file: Path) -> None:
    """--validate exits 0 for a well-formed report."""
    result = runner.invoke(application, [str(report_file), "--validate"])

    assert result.exit_code == 0
    assert "Validation passed" in result.output


def test_validate_fails_with_exit_code_one(tmp_path: Path) -> None:
    """--validate exits 1 and names the problems."""
    bad_path = tmp_path / "bad.csv"
    bad_path.write_text("Product,Clicks\nA,10\n", encoding="utf-8")

    result = runner.invoke(application, [str(bad_path), "--validate"])

    assert result.exit_code == 1
    assert "Missing required columns" in result.output
    assert "Validation failed" in result.output


def test_help_groups_options(report_file: Path) -> None:
    """--help shows the grouped options and the exit-code epilog."""
    result = runner.invoke(application, ["--help"])

    assert result.exit_code == 0
    for expected in (
        "Input & Output",
        "Modes",
        "Diagnostics",
        "--dry-run",
        "--validate",
        "--version",
        "Exit codes",
    ):
        assert expected in result.output
