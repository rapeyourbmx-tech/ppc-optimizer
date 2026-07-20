"""Alternative Typer command interface for PPC Optimizer."""

from pathlib import Path
from typing import Annotated

import typer

from main import run

app = typer.Typer(
    help="Analyze Google Ads product reports.",
    no_args_is_help=True,
)


@app.command()
def analyze(
    file_paths: list[Path],
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
    """Analyze one CSV or XLSX Google Ads product report."""
    exit_code = run(
        file_paths,
        explain=explain,
        config_path=config_path,
        output_path=output_path,
    )
    if exit_code != 0:
        raise typer.Exit(code=exit_code)
