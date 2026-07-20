"""Tests for production packaging and installation."""

import os
import subprocess
import sys
import tomllib
import venv
from pathlib import Path

import pytest

from app.version import __version__

_PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _pyproject() -> dict:
    """Load the project's pyproject.toml."""
    return tomllib.loads((_PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8"))


def test_pyproject_declares_required_metadata() -> None:
    """The package metadata matches the packaging requirements."""
    project = _pyproject()["project"]

    assert project["name"] == "ppc-optimizer"
    assert project["description"] == "Google Ads Product Performance Optimizer"
    assert project["license"] == {"text": "MIT"}
    assert project["requires-python"] == ">=3.11"
    assert project["authors"]
    assert project["scripts"]["ppc-optimizer"] == "main:cli"
    assert "version" in project["dynamic"]


def test_version_is_sourced_from_the_application() -> None:
    """The dynamic version points at the single source of truth."""
    dynamic_version = _pyproject()["tool"]["setuptools"]["dynamic"]["version"]

    assert dynamic_version == {"attr": "app.version.__version__"}
    assert __version__ == "1.0.0"


def test_console_entry_point_target_is_callable() -> None:
    """The declared entry point resolves to a callable."""
    from main import cli

    assert callable(cli)


def test_license_file_is_mit() -> None:
    """The repository ships an MIT license file."""
    license_text = (_PROJECT_ROOT / "LICENSE").read_text(encoding="utf-8")

    assert license_text.startswith("MIT License")


@pytest.mark.slow
def test_pip_install_provides_working_console_script(tmp_path: Path) -> None:
    """pip install . creates a runnable ppc-optimizer console script."""
    venv_dir = tmp_path / "venv"
    venv.create(venv_dir, with_pip=True, system_site_packages=True)
    scripts_dir = venv_dir / ("Scripts" if os.name == "nt" else "bin")
    python_path = scripts_dir / ("python.exe" if os.name == "nt" else "python")

    install = subprocess.run(
        [
            str(python_path),
            "-m",
            "pip",
            "install",
            "--quiet",
            "--no-deps",
            str(_PROJECT_ROOT),
        ],
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )
    assert install.returncode == 0, install.stderr

    script_path = next(
        path
        for path in (
            scripts_dir / "ppc-optimizer",
            scripts_dir / "ppc-optimizer.exe",
        )
        if path.exists()
    )
    result = subprocess.run(
        [str(script_path), "--version"],
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "PPC Optimizer" in result.stdout
    assert f"v{__version__}" in result.stdout


if sys.version_info < (3, 11):  # pragma: no cover
    message = "The test suite itself requires Python 3.11+ (tomllib)."
    raise RuntimeError(message)
