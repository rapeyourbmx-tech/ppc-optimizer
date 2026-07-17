# PPC Optimizer

PPC Optimizer will analyze Google Ads product reports and produce a structured
Excel workbook named `report.xlsx`.

This repository loads CSV/XLSX Google Ads product reports, produces product
decisions, campaign recommendations, and audit findings, and exports a
formatted `report.xlsx` workbook.

## Requirements

- Python 3.12 or newer

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

Decision thresholds live in `config.yaml` in the project root and can be
edited without touching the code. A custom YAML or JSON file can be passed
with `--config`:

```powershell
python main.py data\product_report.csv --config my_thresholds.yaml
```

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
