"""Tests for the Excel workbook exporter."""

from pathlib import Path

import pandas as pd
import pytest
from openpyxl import load_workbook

from app.core.workbook import WorkbookSheet
from app.models.report import ProductReport
from app.reporting.excel_workbook_exporter import ExcelWorkbookExporter
from app.services.application_pipeline import ApplicationPipeline


@pytest.fixture
def exported_workbook_path(tmp_path: Path) -> Path:
    """Run the pipeline on a small report and export the workbook."""
    source_path = tmp_path / "product_report.csv"
    pd.DataFrame(
        [
            {
                "Item ID": "SCALE-1",
                "Item title": "Scaling product",
                "Impressions": 5000,
                "Clicks": 30,
                "Cost": 350.0,
                "Conversions": 1.0,
                "Conversion Value": 49095.0,
            },
            {
                "Item ID": "PAUSE-1",
                "Item title": "Wasting product",
                "Impressions": 1000,
                "Clicks": 104,
                "Cost": 450.0,
                "Conversions": 0.0,
                "Conversion Value": 0.0,
            },
            {
                "Item ID": "WATCH-1",
                "Item title": "Young product",
                "Impressions": 200,
                "Clicks": 3,
                "Cost": 45.0,
                "Conversions": 0.0,
                "Conversion Value": 0.0,
            },
        ]
    ).to_csv(source_path, index=False)

    result = ApplicationPipeline().run(source_path)
    report = ProductReport(
        products=result.products,
        decisions=result.decisions,
        campaign_summary=result.campaign_summary,
        audit_report=result.audit_report,
    )
    output_path = tmp_path / "report.xlsx"
    ExcelWorkbookExporter().export(report, output_path)
    return output_path


def test_export_creates_every_required_sheet(exported_workbook_path: Path) -> None:
    """The workbook contains exactly the required sheets in order."""
    workbook = load_workbook(exported_workbook_path)

    assert workbook.sheetnames == [str(sheet) for sheet in WorkbookSheet]


def test_products_sheet_has_decision_columns_and_layout(
    exported_workbook_path: Path,
) -> None:
    """The Products sheet appends decision columns and sets layout features."""
    sheet = load_workbook(exported_workbook_path)[str(WorkbookSheet.PRODUCTS)]
    headers = [cell.value for cell in sheet[1]]

    assert headers[-4:] == ["Status", "ROAS", "Recommendation", "Reason"]
    assert sheet.freeze_panes == "A2"
    assert sheet.auto_filter.ref is not None
    status_column = headers.index("Status") + 1
    statuses = {
        sheet.cell(row=row_number, column=status_column).value
        for row_number in range(2, 5)
    }
    assert statuses == {"SCALE", "PAUSE", "WATCH"}


def test_products_sheet_roas_is_a_formula(exported_workbook_path: Path) -> None:
    """ROAS cells recalculate from cost and conversion value."""
    sheet = load_workbook(exported_workbook_path)[str(WorkbookSheet.PRODUCTS)]
    headers = [cell.value for cell in sheet[1]]
    roas_column = headers.index("ROAS") + 1

    roas_value = sheet.cell(row=2, column=roas_column).value

    assert isinstance(roas_value, str)
    assert roas_value.startswith("=IFERROR(")


def test_status_sheets_contain_matching_products(exported_workbook_path: Path) -> None:
    """Each status sheet lists only the products with that status."""
    workbook = load_workbook(exported_workbook_path)

    assert workbook[str(WorkbookSheet.SCALE)].cell(row=2, column=1).value == "SCALE-1"
    assert workbook[str(WorkbookSheet.PAUSE)].cell(row=2, column=1).value == "PAUSE-1"
    assert workbook[str(WorkbookSheet.WATCH)].cell(row=2, column=1).value == "WATCH-1"
    keep_note = workbook[str(WorkbookSheet.KEEP)].cell(row=2, column=1).value
    assert keep_note == "No products with the KEEP status."


def test_top_sheets_rank_winners_and_losers(exported_workbook_path: Path) -> None:
    """Top Winners lists revenue products; Top Losers lists wasted spend."""
    workbook = load_workbook(exported_workbook_path)

    assert workbook[str(WorkbookSheet.TOP_WINNERS)].cell(row=2, column=1).value == "SCALE-1"
    assert workbook[str(WorkbookSheet.TOP_LOSERS)].cell(row=2, column=1).value == "PAUSE-1"


def test_dashboard_kpis_are_formula_backed(exported_workbook_path: Path) -> None:
    """Dashboard KPI values are formulas over the Products sheet."""
    sheet = load_workbook(exported_workbook_path)[str(WorkbookSheet.DASHBOARD)]
    formulas = [
        cell.value
        for row in sheet.iter_rows()
        for cell in row
        if isinstance(cell.value, str) and cell.value.startswith("=")
    ]

    assert any("COUNTA(Products!" in formula for formula in formulas)
    assert any('COUNTIF(' in formula and '"KEEP"' in formula for formula in formulas)
    assert any("SUMIFS(" in formula and '"PAUSE"' in formula for formula in formulas)
