# PPC Optimizer

PPC Optimizer will analyze Google Ads product reports and produce a structured
Excel workbook named `report.xlsx`.

This repository loads CSV/XLSX Google Ads product reports, produces product
decisions, campaign recommendations, and audit findings. Excel workbook
generation is not implemented yet.

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

## Planned workbook sheets

- Dashboard
- SKU Manager
- High
- Average
- Low
- Brands
- Categories
- Watchlist
- Top Winners
- Top Losers

## Development

```powershell
pytest
```

Run the current console pipeline with a report file:

```powershell
python main.py path\to\product_report.csv
```

## Input reports

`GoogleAdsProductReportLoader` accepts CSV and XLSX product reports, detects
the format from the file extension, and returns a pandas `DataFrame` with
canonical internal column names. It recognizes the supported Google Ads Product
export headers in English and Ukrainian and reports missing required metrics
before analysis begins.
