"""Command-line entry point for PPC Optimizer."""

import logging
import time
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
from app.logging_setup import configure_logging, get_logger
from app.services.error_presenter import present_error
from app.services.report_validator import ReportValidator
from app.version import APP_NAME, __version__

# ConfigurationError subclasses ValueError, so run() maps it to exit code 2.

_EXPLANATION_SEPARATOR = "-" * 32


def run(
    file_paths: Path | Sequence[Path],
    pipeline: ApplicationPipeline | None = None,
    *,
    explain: bool = False,
    config_path: Path | None = None,
    output_path: Path | None = None,
    verbose: bool = False,
    dry_run: bool = False,
    validate: bool = False,
) -> int:
    """Analyze one or more reports, export the workbook, print a summary.

    The configuration is loaded once here and injected into every service.
    When no output path is given, the workbook path comes from the
    configuration's excel.output_file setting. Exit codes: 0 success,
    1 validation error, 2 configuration error, 3 internal error. Errors
    are printed as friendly messages, never as Python tracebacks.
    """
    source_paths = [file_paths] if isinstance(file_paths, Path) else list(file_paths)
    started_at = time.perf_counter()
    logger = _configure_run_logging(verbose)
    logger.info("%s v%s started", APP_NAME, __version__)

    if validate:
        return _run_validation(source_paths, logger)

    try:
        _progress(verbose, "Loading configuration...")
        configuration = load_configuration(config_path)
        logger.debug("Configuration source: %s", config_path or "config.yaml or defaults")
        resolved_output = output_path or Path(configuration.excel.output_file)
        analyzer = MultiCampaignAnalyzer(configuration=configuration, pipeline=pipeline)
        _progress(verbose, "Loading reports...")
        logger.info(
            "Loaded files: %s",
            ", ".join(str(source_path) for source_path in source_paths),
        )
        _progress(verbose, "Analyzing products...")
        report = analyzer.analyze(source_paths)
        logger.info(
            "Products analyzed: %d across %d campaign(s)",
            report.overall_summary.total_products,
            len(report.campaigns),
        )
        if report.overall_health != "Healthy":
            logger.warning("Overall campaign health: %s", report.overall_health)
        budget = BudgetOptimizer(configuration).optimize(report)
        if not dry_run:
            _progress(verbose, "Generating workbook...")
            ExcelWorkbookExporter(configuration).export(report, resolved_output, budget)
            logger.debug("Workbook written: %s", resolved_output)
    except Exception as error:  # noqa: BLE001 — classified by the presenter
        exit_code, message = present_error(error)
        logger.error("%s: %s (exit code %d)", type(error).__name__, error, exit_code)
        logger.debug("Stack trace:", exc_info=error)
        typer.echo(message, err=True)
        return exit_code

    typer.echo(_console_summary(report))
    if not dry_run:
        typer.echo(f"Report saved: {resolved_output}")
    if explain:
        typer.echo(_decision_explanations(report.decisions))
    logger.info("Execution time: %.2f s", time.perf_counter() - started_at)
    _progress(verbose, "Done.")
    return 0


def _configure_run_logging(verbose: bool) -> logging.Logger:
    """Configure file logging, degrading gracefully when it is unavailable."""
    try:
        return configure_logging(verbose=verbose)
    except OSError as error:
        typer.echo(f"Warning: file logging disabled ({error}).", err=True)
        logger = get_logger()
        logger.handlers.clear()
        logger.addHandler(logging.NullHandler())
        logger.propagate = False
        return logger


def _progress(verbose: bool, message: str) -> None:
    """Print one progress line when verbose mode is on."""
    if verbose:
        typer.echo(message)


def _run_validation(source_paths: list[Path], logger: logging.Logger) -> int:
    """Validate the input files and report every issue found."""
    logger.info(
        "Validating files: %s",
        ", ".join(str(source_path) for source_path in source_paths),
    )
    result = ReportValidator().validate(source_paths)
    if result.is_valid:
        logger.info("Validation passed: %d file(s) OK.", result.checked_files)
        typer.echo(f"Validation passed: {result.checked_files} file(s) OK.")
        return 0

    for issue in result.issues:
        logger.warning("%s: %s", issue.source_file, issue.message)
        typer.echo(f"{issue.source_file}: {issue.message}", err=True)
    typer.echo(
        f"Validation failed: {len(result.issues)} issue(s) "
        f"in {result.checked_files} file(s).",
        err=True,
    )
    return 1


def _version_callback(value: bool) -> None:
    """Print the application name and version, then exit."""
    if value:
        typer.echo(f"{APP_NAME}\nv{__version__}")
        raise typer.Exit()


application = typer.Typer(add_completion=False, pretty_exceptions_enable=False)


@application.command(
    epilog=(
        "Exit codes: 0 success | 1 validation error | "
        "2 configuration error | 3 internal error."
    ),
)
def main(
    file_paths: Annotated[
        list[Path],
        typer.Argument(
            help="One or more CSV or XLSX Google Ads product reports.",
            show_default=False,
        ),
    ],
    config_path: Annotated[
        Path | None,
        typer.Option(
            "--config",
            help="Load a custom YAML or JSON configuration file.",
            rich_help_panel="Input & Output",
        ),
    ] = None,
    output_path: Annotated[
        Path | None,
        typer.Option(
            "--output",
            help="Workbook path (default: excel.output_file from the configuration).",
            rich_help_panel="Input & Output",
        ),
    ] = None,
    explain: Annotated[
        bool,
        typer.Option(
            "--explain",
            help="Print a metric-based explanation for every decision.",
            rich_help_panel="Modes",
        ),
    ] = False,
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run",
            help="Run the full analysis without generating Excel; print the summary only.",
            rich_help_panel="Modes",
        ),
    ] = False,
    validate: Annotated[
        bool,
        typer.Option(
            "--validate",
            help=(
                "Validate the input files only (required columns, duplicated SKUs, "
                "invalid numeric values, unsupported file types) and exit 0/1."
            ),
            rich_help_panel="Modes",
        ),
    ] = False,
    verbose: Annotated[
        bool,
        typer.Option(
            "--verbose",
            help="Print progress messages for every stage.",
            rich_help_panel="Diagnostics",
        ),
    ] = False,
    version: Annotated[
        bool,
        typer.Option(
            "--version",
            help="Print the application version and exit.",
            callback=_version_callback,
            is_eager=True,
            rich_help_panel="Diagnostics",
        ),
    ] = False,
) -> None:
    """Analyze Google Ads product reports and build a formatted Excel workbook.

    Each input file is treated as one campaign; thresholds, campaign
    overrides, and workbook settings come from config.yaml.
    """
    exit_code = run(
        file_paths,
        explain=explain,
        config_path=config_path,
        output_path=output_path,
        verbose=verbose,
        dry_run=dry_run,
        validate=validate,
    )
    if exit_code != 0:
        raise typer.Exit(code=exit_code)


def cli() -> None:
    """Run the Typer command-line interface."""
    application()


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
