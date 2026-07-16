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
    file_path: Path,
    explain: Annotated[
        bool,
        typer.Option("--explain", help="Print a metric-based explanation for every decision."),
    ] = False,
) -> None:
    """Analyze one CSV or XLSX Google Ads product report."""
    exit_code = run(file_path, explain=explain)
    if exit_code != 0:
        raise typer.Exit(code=exit_code)
