"""Numeric normalization for Google Ads report metric columns."""

import re

import pandas as pd


_METRIC_COLUMNS: tuple[str, ...] = (
    "clicks",
    "impressions",
    "ctr",
    "average_cpc",
    "cost",
    "conversions",
    "conversion_value",
    "cost_per_conversion",
    "all_conversions",
    "all_conversion_value",
)
_NON_NUMERIC_CHARACTERS = re.compile(r"[^\d,.\-]")


def normalize_metric_values(report: pd.DataFrame) -> pd.DataFrame:
    """Convert locale-formatted metric columns to plain numeric values.

    Google Ads exports may format metrics with currency prefixes, percent
    signs, thousands separators (regular or non-breaking spaces), and comma
    decimal separators (for example "грн34\u00a0034,00" or "0,29%"). Metric
    columns that are already numeric are returned unchanged.
    """
    normalized_report = report.copy()

    for column_name in _METRIC_COLUMNS:
        if column_name in normalized_report.columns:
            normalized_report[column_name] = _to_numeric(normalized_report[column_name])

    return normalized_report


def _to_numeric(values: pd.Series) -> pd.Series:
    """Convert one metric column to numeric values."""
    if pd.api.types.is_numeric_dtype(values):
        return values

    return pd.to_numeric(values.map(_clean_value), errors="coerce")


def _clean_value(value: object) -> str | None:
    """Strip locale formatting from one metric value.

    Removes every character except digits, separators, and the minus sign,
    then resolves the decimal separator: when both "," and "." are present
    the rightmost one is treated as decimal; a single "," is treated as a
    decimal comma; repeated commas are treated as thousands separators.
    """
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None

    stripped_value = _NON_NUMERIC_CHARACTERS.sub("", str(value))
    if not stripped_value:
        return None

    if "," in stripped_value and "." in stripped_value:
        if stripped_value.rfind(",") > stripped_value.rfind("."):
            stripped_value = stripped_value.replace(".", "").replace(",", ".")
        else:
            stripped_value = stripped_value.replace(",", "")
    elif stripped_value.count(",") > 1:
        stripped_value = stripped_value.replace(",", "")
    elif "," in stripped_value:
        stripped_value = stripped_value.replace(",", ".")

    return stripped_value
