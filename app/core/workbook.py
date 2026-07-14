"""Workbook structure definitions."""

from enum import StrEnum


class WorkbookSheet(StrEnum):
    """Sheets required in every generated report workbook."""

    DASHBOARD = "Dashboard"
    SKU_MANAGER = "SKU Manager"
    HIGH = "High"
    AVERAGE = "Average"
    LOW = "Low"
    BRANDS = "Brands"
    CATEGORIES = "Categories"
    WATCHLIST = "Watchlist"
    TOP_WINNERS = "Top Winners"
    TOP_LOSERS = "Top Losers"
