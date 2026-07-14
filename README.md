# PPC Optimizer

PPC Optimizer will analyze Google Ads product reports and produce a structured
Excel workbook named `report.xlsx`.

This repository currently contains the initial application architecture only.
Business rules, source parsing, analysis, and workbook generation are not yet
implemented.

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
│   ├── core/                  # Shared constants and infrastructure helpers
│   ├── models/                # Typed domain and request models
│   ├── repositories/          # Source data access contracts
│   ├── services/              # Analysis and orchestration contracts
│   └── reporting/             # Excel workbook export contracts
├── data/                      # Local input data (not committed)
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
