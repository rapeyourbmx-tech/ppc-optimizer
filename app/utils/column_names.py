"""Utilities for normalizing tabular column names."""

import re

import pandas as pd


def normalize_column_name(column_name: object) -> str:
    """Convert a tabular column name to lowercase snake_case."""
    normalized_name = str(column_name).strip().casefold()
    normalized_name = re.sub(r"[^\w]+", "_", normalized_name)
    return normalized_name.strip("_")


def normalize_column_names(data_frame: pd.DataFrame) -> pd.DataFrame:
    """Return a data frame with normalized column names."""
    return data_frame.rename(columns=normalize_column_name)
