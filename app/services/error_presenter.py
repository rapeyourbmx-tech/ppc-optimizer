"""Friendly command-line presentation of application errors."""

import difflib

from app.config import ConfigurationError
from app.loaders.google_ads_product_report_mapper import MissingColumnsError
from app.loaders.product_report_loader import UnsupportedReportFormatError

EXIT_SUCCESS = 0
EXIT_VALIDATION_ERROR = 1
EXIT_CONFIGURATION_ERROR = 2
EXIT_INTERNAL_ERROR = 3

_DISPLAY_COLUMN_NAMES: dict[str, str] = {
    "product_id": "Product ID",
    "conversion_value": "Conversion Value",
}
_NO_SIMILAR_COLUMN = "(no similar column)"


def present_error(error: Exception) -> tuple[int, str]:
    """Classify an error and build its friendly message.

    Returns:
        The exit code (1 validation, 2 configuration, 3 internal) and the
        message to print, never a Python traceback.
    """
    if isinstance(error, ConfigurationError):
        return EXIT_CONFIGURATION_ERROR, f"ERROR\nConfiguration problem.\n{error}"

    if isinstance(error, MissingColumnsError):
        return EXIT_VALIDATION_ERROR, _missing_columns_message(error)

    if isinstance(error, UnsupportedReportFormatError):
        return (
            EXIT_VALIDATION_ERROR,
            "ERROR\nUnsupported file type.\nExpected:\nCSV or XLSX",
        )

    if isinstance(error, FileNotFoundError):
        location = error.filename or str(error)
        return EXIT_VALIDATION_ERROR, f"ERROR\nFile not found: {location}"

    if isinstance(error, (OSError, ValueError)):
        return EXIT_VALIDATION_ERROR, f"ERROR\n{error}"

    return (
        EXIT_INTERNAL_ERROR,
        (f"ERROR\nInternal error: {type(error).__name__}: {error}\nPlease report this issue."),
    )


def _missing_columns_message(error: MissingColumnsError) -> str:
    """Build one Expected/Found block per missing column."""
    blocks = []
    for column_name in error.missing_columns:
        display_name = _display_column_name(column_name)
        blocks.append(
            f'Column "{display_name}" not found.\n'
            "Expected:\n"
            f"{display_name}\n"
            "Found:\n"
            f"{_closest_column(display_name, error.available_columns)}"
        )

    return "ERROR\n" + "\n\n".join(blocks)


def _display_column_name(column_name: str) -> str:
    """Return the human-readable header for one canonical column name."""
    if column_name in _DISPLAY_COLUMN_NAMES:
        return _DISPLAY_COLUMN_NAMES[column_name]

    return column_name.replace("_", " ").strip().title()


def _closest_column(display_name: str, available_columns: list[str]) -> str:
    """Return the most similar actual header, case-insensitively."""
    lowered_available = {column.casefold(): column for column in available_columns}
    matches = difflib.get_close_matches(
        display_name.casefold(),
        list(lowered_available),
        n=1,
        cutoff=0.6,
    )
    if not matches:
        return _NO_SIMILAR_COLUMN

    return lowered_available[matches[0]]
