"""Architecture-level smoke tests."""

from app.cli import app
from app.core.workbook import WorkbookSheet


def test_cli_application_is_defined() -> None:
    """The command-line application is importable."""
    assert app is not None


def test_required_workbook_sheets_are_declared() -> None:
    """The workbook structure includes every required sheet."""
    assert len(WorkbookSheet) == 10
