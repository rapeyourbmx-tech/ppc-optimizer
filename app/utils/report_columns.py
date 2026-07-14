"""Shared column definitions and access helpers for product reports."""

import pandas as pd


SKU_COLUMNS: tuple[str, ...] = ("sku", "item_id", "product_id", "id")
IMPRESSION_COLUMNS: tuple[str, ...] = ("impressions",)
CLICK_COLUMNS: tuple[str, ...] = ("clicks",)
COST_COLUMNS: tuple[str, ...] = ("cost",)
CONVERSION_COLUMNS: tuple[str, ...] = ("conversions",)
CONVERSION_VALUE_COLUMNS: tuple[str, ...] = ("conversion_value", "conversion_value_value")


class ReportColumnError(ValueError):
    """Raised when a product report lacks a required column."""


def resolve_column(
    products: pd.DataFrame,
    candidates: tuple[str, ...],
    metric_name: str,
) -> str:
    """Return the first supported column name for a report metric."""
    for column_name in candidates:
        if column_name in products.columns:
            return column_name

    message = f"The product report is missing a {metric_name} column."
    raise ReportColumnError(message)


def numeric_values(values: pd.Series) -> pd.Series:
    """Convert a report metric to numeric values and replace blanks with zero."""
    return pd.to_numeric(values, errors="coerce").fillna(0.0)
