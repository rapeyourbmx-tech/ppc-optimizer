"""Tests for application logging."""

from datetime import date
from pathlib import Path

import logging
import pandas as pd
import pytest

from app.logging_setup import configure_logging, get_logger
from app.version import __version__
from main import run


@pytest.fixture
def report_file(tmp_path: Path) -> Path:
    """One valid single-product report file."""
    source_path = tmp_path / "campaign.csv"
    pd.DataFrame(
        [
            {
                "Item ID": "LOG-1",
                "Impressions": 1000,
                "Clicks": 10,
                "Cost": 350.0,
                "Conversions": 2.0,
                "Conversion Value": 700.0,
            }
        ]
    ).to_csv(source_path, index=False)
    return source_path


def _log_text(base_path: Path) -> str:
    """Read today's log file from a working directory."""
    return (base_path / "logs" / f"{date.today().isoformat()}.log").read_text(
        encoding="utf-8"
    )


def test_configure_logging_creates_directory_and_daily_file(tmp_path: Path) -> None:
    """The logs directory and the dated file are created automatically."""
    logger = configure_logging(logs_directory=tmp_path / "logs")
    logger.info("hello")

    log_path = tmp_path / "logs" / f"{date.today().isoformat()}.log"
    assert log_path.is_file()
    assert "hello" in log_path.read_text(encoding="utf-8")


def test_configure_logging_levels_follow_verbose_flag(tmp_path: Path) -> None:
    """DEBUG records are written only in verbose mode."""
    quiet = configure_logging(logs_directory=tmp_path / "logs")
    assert quiet.level == logging.INFO
    verbose = configure_logging(verbose=True, logs_directory=tmp_path / "logs")
    assert verbose.level == logging.DEBUG


def test_reconfiguring_does_not_duplicate_handlers(tmp_path: Path) -> None:
    """Repeated configuration replaces the handler instead of stacking."""
    configure_logging(logs_directory=tmp_path / "logs")
    configure_logging(logs_directory=tmp_path / "logs")

    assert len(get_logger().handlers) == 1


def test_run_logs_version_files_products_and_time(
    report_file: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A successful run logs every required fact."""
    monkeypatch.chdir(tmp_path)

    exit_code = run(report_file, dry_run=True)

    log_text = _log_text(tmp_path)
    assert exit_code == 0
    assert f"v{__version__} started" in log_text
    assert f"Loaded files: {report_file}" in log_text
    assert "Products analyzed: 1 across 1 campaign(s)" in log_text
    assert "Execution time:" in log_text


def test_run_logs_errors_without_traceback_by_default(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Errors are logged as one line; stack traces stay out of the log."""
    monkeypatch.chdir(tmp_path)

    exit_code = run(tmp_path / "missing.csv")

    log_text = _log_text(tmp_path)
    assert exit_code == 1
    assert "ERROR ppc_optimizer" in log_text
    assert "Traceback" not in log_text


def test_run_logs_traceback_only_in_verbose_mode(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """--verbose adds the stack trace as a DEBUG record."""
    monkeypatch.chdir(tmp_path)

    exit_code = run(tmp_path / "missing.csv", verbose=True)

    log_text = _log_text(tmp_path)
    assert exit_code == 1
    assert "Traceback" in log_text


def test_validation_issues_are_logged_as_warnings(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """--validate records every issue with the WARNING level."""
    monkeypatch.chdir(tmp_path)
    bad_path = tmp_path / "bad.csv"
    bad_path.write_text("Product,Clicks\nA,10\n", encoding="utf-8")

    exit_code = run(bad_path, validate=True)

    log_text = _log_text(tmp_path)
    assert exit_code == 1
    assert "WARNING ppc_optimizer: bad.csv" in log_text
    assert "Missing required columns" in log_text
