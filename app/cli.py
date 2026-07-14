"""Command-line interface definition."""

import typer


app = typer.Typer(
    help="Analyze Google Ads product reports and create Excel workbooks.",
    no_args_is_help=True,
)
