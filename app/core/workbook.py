"""Workbook structure definitions."""

from enum import StrEnum


class WorkbookSheet(StrEnum):
    """Sheets required in every generated report workbook."""

    DASHBOARD = "Dashboard"
    EXECUTIVE_SUMMARY = "Executive Summary"
    PRODUCTS = "Products"
    KEEP = "KEEP"
    WATCH = "WATCH"
    PAUSE = "PAUSE"
    SCALE = "SCALE"
    TOP_WINNERS = "Top Winners"
    TOP_LOSERS = "Top Losers"
