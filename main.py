"""Command-line entry point for PPC Optimizer."""

from collections.abc import Sequence
from pathlib import Path
from typing import Annotated

import typer

from app.config import ConfigurationError, load_configuration
from app.models.campaign import MultiCampaignReport
from app.models.product_decision import ProductDecision
from app.reporting.excel_workbook_exporter import ExcelWorkbookExporter
from app.services.application_pipeline import ApplicationPipeline
from app.services.budget_optimizer import BudgetOptimizer
from app.services.multi_campaign_analyzer import MultiCampaignAnalyzer

# ConfigurationError subclasses ValueError, so run() maps it to exit code 2.

_EXPLANATION_SEPARATOR = "-" * 32


def run(
    file_paths: Path | Sequence[Path],
    pipeline: ApplicationPipeline | None = None,
    *,
    explain: bool = False,
    config_path: Path | None = None,
    output_path: Path | None = None,
) -> int:
    """Analyze one or more reports, export the workbook, print a summary.

    The configuration is loaded once here and injected into every service.
    When no output path is given, the workbook path comes from the
    configuration's excel.output_file setting.
    """
    source_paths = [file_paths] if isinstance(file_paths, Path) else list(file_paths)

    try:
        configuration = load_configuration(config_path)
        resolved_output = output_path or Path(configuration.excel.output_file)
        analyzer = MultiCampaignAnalyzer(configuration=configuration, pipeline=pipeline)
        report = analyzer.analyze(source_paths)
        budget = BudgetOptimizer(configuration).optimize(report)
        ExcelWorkbookExporter(configuration).export(report, resolved_output, budget)
    except (OSError, ValueError) as error:
        typer.echo(f"Error: {error}", err=True)
        return 2
    except Exception as error:
        typer.echo(f"Unexpected error: {error}", err=True)
        return 1

    typer.echo(_console_summary(report))
    typer.echo(f"Report saved: {resolved_output}")
    if explain:
        typer.echo(_decision_explanations(report.decisions))
    return 0


def main(
    file_paths: Annotated[
        list[Path],
        typer.Argument(help="One or more CSV or XLSX Google Ads product reports."),
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
        Path | None,
        typer.Option(
            "--output",
            help="Path of the workbook (default: excel.output_file from config).",
        ),
    ] = None,
) -> None:
    """Accept report paths and exit with the pipeline status code."""
    exit_code = run(
        file_paths,
        explain=explain,
        config_path=config_path,
        output_path=output_path,
    )
    if exit_code != 0:
        raise typer.Exit(code=exit_code)


def cli() -> None:
    """Run the Typer command-line interface."""
    typer.run(main)


def _console_summary(report: MultiCampaignReport) -> str:
    """Format the success summary for one or more analyzed campaigns."""
    if len(report.campaigns) == 1:
        campaign = report.campaigns[0]
        return _campaign_summary_line(
            campaign.campaign_summary,
            campaign.health,
        )

    lines = [
        f"{campaign.metadata.name}: "
        + _campaign_summary_line(campaign.campaign_summary, campaign.health)
        for campaign in report.campaigns
    ]
    overall = report.overall_summary
    lines.append(
        f"Overall: Health: {report.overall_health} | "
        f"Products: {overall.total_products} | "
        f"Cost: {overall.total_cost:,.2f} | Revenue: {overall.total_revenue:,.2f} | "
        f"Conversions: {overall.total_conversions:,.2f} | Keep: {overall.keep} | "
        f"Watch: {overall.watch} | Pause: {overall.pause} | Scale: {overall.scale}"
    )
    return "\n".join(lines)


def _campaign_summary_line(summary: object, health: str) -> str:
    """Format the classic single-campaign summary line."""
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
