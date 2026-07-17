"""Command-line entry point for PPC Optimizer."""

from pathlib import Path
from typing import Annotated

import typer

from app.analyzers.product_analyzer import ProductAnalyzer
from app.config import ConfigurationError, load_thresholds
from app.models.product_decision import ProductDecision
from app.models.report import ProductReport
from app.reporting.excel_workbook_exporter import ExcelWorkbookExporter
from app.services.application_pipeline import ApplicationPipeline, PipelineResult

_EXPLANATION_SEPARATOR = "-" * 32


def run(
    file_path: Path,
    pipeline: ApplicationPipeline | None = None,
    *,
    explain: bool = False,
    config_path: Path | None = None,
    output_path: Path = Path("report.xlsx"),
) -> int:
    """Run the pipeline, export the workbook, and print a console summary."""
    try:
        active_pipeline = pipeline or _build_pipeline(config_path)
        result = active_pipeline.run(file_path)
        _export_workbook(result, output_path)
    except (OSError, ValueError) as error:
        typer.echo(f"Error: {error}", err=True)
        return 2
    except Exception as error:
        typer.echo(f"Unexpected error: {error}", err=True)
        return 1

    typer.echo(_console_summary(result))
    typer.echo(f"Report saved: {output_path}")
    if explain:
        typer.echo(_decision_explanations(result.decisions))
    return 0


def main(
    file_path: Annotated[
        Path,
        typer.Argument(help="Path to a CSV or XLSX Google Ads product report."),
    ],
    explain: Annotated[
        bool,
        typer.Option("--explain", help="Print a metric-based explanation for every decision."),
    ] = False,
    config_path: Annotated[
        Path | None,
        typer.Option(
            "--config",
            help="Path to a YAML or JSON thresholds file (default: config.yaml).",
        ),
    ] = None,
    output_path: Annotated[
        Path,
        typer.Option("--output", help="Path of the generated Excel workbook."),
    ] = Path("report.xlsx"),
) -> None:
    """Accept a report path and exit with the pipeline status code."""
    exit_code = run(
        file_path,
        explain=explain,
        config_path=config_path,
        output_path=output_path,
    )
    if exit_code != 0:
        raise typer.Exit(code=exit_code)


def cli() -> None:
    """Run the Typer command-line interface."""
    typer.run(main)


def _export_workbook(result: PipelineResult, output_path: Path) -> None:
    """Export the pipeline result to the report workbook."""
    report = ProductReport(
        products=result.products,
        decisions=result.decisions,
        campaign_summary=result.campaign_summary,
        audit_report=result.audit_report,
    )
    ExcelWorkbookExporter().export(report, output_path)


def _build_pipeline(config_path: Path | None) -> ApplicationPipeline:
    """Build the pipeline with thresholds from the configuration file.

    Raises:
        ConfigurationError: If the configuration file cannot be used.
    """
    thresholds = load_thresholds(config_path)
    return ApplicationPipeline(product_analyzer=ProductAnalyzer(thresholds=thresholds))


def _console_summary(result: PipelineResult) -> str:
    """Format the single-line success summary for console output."""
    summary = result.campaign_summary
    health = result.audit_report.overall_health
    return (
        f"Health: {health} | Products: {summary.total_products} | Keep: {summary.keep} | "
        f"Watch: {summary.watch} | Pause: {summary.pause} | Scale: {summary.scale}"
    )


def _decision_explanations(decisions: list[ProductDecision]) -> str:
    """Format one explanation block per product decision."""
    blocks = [
        (
            f"SKU: {decision.sku}\n"
            f"Decision: {decision.status}\n"
            f"Reason:\n{decision.explanation}\n"
            f"{_EXPLANATION_SEPARATOR}"
        )
        for decision in decisions
    ]
    return "\n".join(blocks)


if __name__ == "__main__":
    cli()
