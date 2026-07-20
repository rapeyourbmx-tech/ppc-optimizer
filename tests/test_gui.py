"""Tests for the desktop interface (headless-safe)."""

import tomllib
from pathlib import Path

import pandas as pd
import pytest

from app.gui import execute_analysis


def test_gui_module_imports_without_a_display() -> None:
    """The module must be importable on machines without tkinter or X."""
    import app.gui  # noqa: F401 — the import itself is the assertion


def test_execute_analysis_returns_summary_and_creates_workbook(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The GUI bridge runs the full pipeline and captures its output."""
    monkeypatch.chdir(tmp_path)
    source_path = tmp_path / "campaign.csv"
    pd.DataFrame(
        [
            {
                "Item ID": "GUI-1",
                "Impressions": 1000,
                "Clicks": 10,
                "Cost": 350.0,
                "Conversions": 2.0,
                "Conversion Value": 700.0,
            }
        ]
    ).to_csv(source_path, index=False)
    output_path = tmp_path / "report.xlsx"

    exit_code, output = execute_analysis([source_path], output_path)

    assert exit_code == 0
    assert "Health:" in output
    assert output_path.is_file()


def test_execute_analysis_surfaces_friendly_errors(tmp_path: Path) -> None:
    """Failures come back as the friendly text, not exceptions."""
    exit_code, output = execute_analysis([tmp_path / "missing.csv"], tmp_path / "r.xlsx")

    assert exit_code == 1
    assert "File not found" in output
    assert "Traceback" not in output


def test_gui_entry_point_is_declared() -> None:
    """The package installs the ppc-optimizer-gui console script."""
    pyproject = tomllib.loads(
        (Path(__file__).resolve().parent.parent / "pyproject.toml").read_text(encoding="utf-8")
    )

    assert pyproject["project"]["scripts"]["ppc-optimizer-gui"] == "app.gui:main"
