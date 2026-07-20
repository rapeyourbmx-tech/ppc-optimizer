# PPC Optimizer

PPC Optimizer will analyze Google Ads product reports and produce a structured
Excel workbook named `report.xlsx`.

This repository loads CSV/XLSX Google Ads product reports, produces product
decisions, campaign recommendations, and audit findings, and exports a
formatted `report.xlsx` workbook.

## Requirements

- Python 3.11 or newer

## Setup

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## Project layout

```text
.
├── app/
│   ├── cli.py                 # Command-line interface boundary
│   ├── config.py              # Application configuration models
│   ├── loaders/               # Input report loaders
│   ├── analyzers/             # Future performance analysis components
│   ├── core/                  # Shared constants and infrastructure helpers
│   ├── models/                # Typed domain and request models
│   ├── repositories/          # Source data access contracts
│   ├── services/              # Analysis and orchestration contracts
│   └── reporting/             # Excel workbook export contracts
├── data/                      # Local input data (not committed)
├── examples/                  # Usage examples
├── reports/                   # Report-facing package boundary
├── templates/                 # Workbook templates
├── tests/                     # Automated tests
└── main.py                    # Application entry point
```

## Workbook sheets

- Dashboard — formula-backed KPI cards
- Executive Summary — key metrics and recommended actions
- Products — every source column plus Status, ROAS, Recommendation, Reason
- KEEP / WATCH / PAUSE / SCALE — one sheet per decision
- Top Winners — highest-ROAS products with revenue
- Top Losers — largest spend with zero conversions

Brands and Categories sheets are planned for a future release. Use
`--output` to change the workbook path (default: `report.xlsx`).

## Development

```powershell
pytest
```

Run the current console pipeline with a report file:

```powershell
python main.py path\to\product_report.csv
```

## Configuration

The whole application is configured through `config.yaml` in the project
root: decision thresholds, per-campaign overrides, budget optimization,
audit thresholds (`audit`), Excel rendering (`excel`: font, column widths,
top-list size, default output file), and dashboard rendering
(`dashboard`: title, colors, ROAS color scale). The configuration is
loaded once on startup and injected into every service; there are no
hardcoded thresholds in the code.

Decision thresholds can be
edited without touching the code. A custom YAML or JSON file can be passed
with `--config`:

```powershell
python main.py data\product_report.csv --config my_thresholds.yaml
```

## Installation

Install the application with pip from the project root:

```powershell
pip install .
```

This provides the `ppc-optimizer` console command:

```powershell
ppc-optimizer high.csv average.csv low.csv
```

For development, use an editable install: `pip install -e .[dev]`.

### Building distributions

```powershell
pip install build
python -m build
```

The wheel and source distribution appear in `dist/`. The package version
comes from `app/version.py` (single source of truth); the license is MIT
(see `LICENSE`), and the author field in `pyproject.toml` is a
placeholder to configure before publishing.

## Command line

```powershell
python main.py report.csv                # analyze and build the workbook
python main.py report.csv --dry-run      # summary only, no Excel
python main.py report.csv --validate     # check the file, exit 0/1
python main.py report.csv --verbose      # print progress stages
python main.py --version                 # print the application version
```

Options are grouped in `--help` (Input & Output, Modes, Diagnostics).
Errors are printed as friendly messages (with Expected/Found suggestions
for misspelled columns), never as Python tracebacks. Exit codes:
0 success, 1 validation error, 2 configuration error, 3 internal error.

## Multiple campaigns

Pass several report files to analyze them as separate campaigns in one run:

```powershell
python main.py data\high.csv data\average.csv data\low.csv
```

Each file becomes one campaign (name and type are derived from the file
name), every product keeps its campaign_name, campaign_type, and
source_file, the Dashboard gains a campaign comparison table, and the
Executive Summary lists recommendations per campaign.

### Per-campaign thresholds

Add a `campaigns` section to `config.yaml` to override thresholds for
specific campaigns. A section applies when its key equals the campaign
name or is contained in it (`low` matches `low_price`):

```yaml
campaigns:
  low:
    pause_spend: 220   # overrides pause.min_cost
    watch_spend: 120   # overrides watch.max_cost
    scale_roas: 700    # overrides scale.min_roas (percent)
```

Thresholds not listed in a campaign section keep the global values.

### Budget optimization

The workbook includes a budget redistribution recommendation built from
per-campaign efficiency scores. Marginal efficiency is the campaign ROAS
multiplied by its growth share (spend in SCALE products or below the
watch threshold); saturation is the complement of the growth share. The
`budget` section of `config.yaml` controls the INCREASE and DECREASE
efficiency thresholds, the share of spend to move, and the conversions
required for full confidence. Results appear in the Budget Optimization
table on the Dashboard and the Action Plan in the Executive Summary.

Rules are checked in order: watch (`max_cost`), pause (`min_cost`,
`max_conversions`), scale (`min_roas` in percent, `min_conversion_value`),
keep (`min_conversions`). Products that match no rule stay on the watch
list. When no configuration file is present, built-in defaults matching
`config.yaml` are used.

## Input reports

`GoogleAdsProductReportLoader` accepts CSV and XLSX product reports, detects
the format from the file extension, and returns a pandas `DataFrame` with
canonical internal column names. It recognizes the supported Google Ads Product
export headers in English and Ukrainian and reports missing required metrics
before analysis begins.
