# PPC Optimizer

**Google Ads Product Performance Optimizer** — turn raw product report
exports into decisions: what to scale, what to pause, and where to move
your budget.

![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Tests](https://img.shields.io/badge/tests-99%20passing-brightgreen)

![Dashboard](docs/screenshots/dashboard.png)
*<!-- Screenshot placeholder: Dashboard sheet -->*

---

## Overview

PPC Optimizer analyzes Google Ads product reports (CSV or XLSX), classifies
every product as **KEEP / WATCH / PAUSE / SCALE** with a metric-based
explanation, compares campaigns side by side, recommends budget
redistribution, and exports everything into a formatted Excel workbook with
live formulas.

It is built for real-world exports: Ukrainian and English headers, preamble
rows, double-quoted rows, currency prefixes (`грн34 034,00`), non-breaking
thousands separators, and decimal commas are handled out of the box.

## Features

- **Robust report loader** — auto-detects the header row, delimiter, and
  encoding; unwraps double-quoted exports; normalizes locale-formatted
  numbers; maps Ukrainian and English column names to one schema
- **Decision engine** — configurable rules classify each product and store
  a human-readable explanation (`--explain`)
- **Multi-campaign analysis** — pass several files, each becomes a campaign;
  every product keeps its campaign name, type, and source file
- **Per-campaign thresholds** — one `config.yaml` section per campaign
  (`low` matches `low_price`), the rest inherits the global values
- **Budget optimizer** — marginal efficiency and saturation scores per
  campaign, INCREASE / KEEP / DECREASE actions, and a concrete transfer
  plan with expected gain and confidence
- **Excel workbook** — 9 sheets, KPI cards, campaign comparison, budget
  table, conditional formatting, frozen headers, autofilters, and
  formula-backed values that recalculate in Excel
- **Production CLI** — `--validate`, `--dry-run`, `--verbose`, `--version`,
  friendly errors with *Expected/Found* suggestions, proper exit codes
- **Daily file logging** — `logs/YYYY-MM-DD.log` with version, inputs,
  product counts, warnings, and execution time
- **Fully configuration-driven** — no hardcoded thresholds anywhere

## Installation

Requires **Python 3.11+**.

```bash
git clone https://github.com/rapeyourbmx-tech/ppc-optimizer.git
cd ppc-optimizer
pip install .
```

This installs the `ppc-optimizer` console command. For development:

```bash
pip install -e .[dev]
```

## Quick Start

1. In Google Ads, export a product report (CSV or XLSX).
2. Run the analysis:

```bash
ppc-optimizer report.csv
```

3. Open the generated `report.xlsx`.

```
Health: Needs attention | Products: 130 | Keep: 0 | Watch: 120 | Pause: 7 | Scale: 3
Report saved: report.xlsx
```

## Examples

**Analyze several campaigns together** (one file = one campaign):

```bash
ppc-optimizer high_price.csv average_price.csv low_price.csv --output combined.xlsx
```

**Print an explanation for every product decision:**

```bash
ppc-optimizer report.csv --explain
```

```
SKU: 703501019
Decision: SCALE
Reason:
ROAS = 43737.19
Cost = 112.25
Revenue = 49095
Conversions = 1
```

**Validate exports before analyzing** (broken files fail fast):

```bash
ppc-optimizer report.csv --validate
```

**Experiment with thresholds without touching the workbook:**

```bash
ppc-optimizer report.csv --config strict.yaml --dry-run --verbose
```

## Configuration

Everything lives in `config.yaml` next to where you run the command
(or pass `--config path.yaml`). Missing keys fall back to built-in
defaults; misspelled keys fail with a clear error.

```yaml
watch:
  max_cost: 300          # below this spend a product is only watched
pause:
  min_cost: 300          # spend at or above this with no conversions -> PAUSE
  max_conversions: 0
scale:
  min_roas: 100          # ROAS threshold in percent
  min_conversion_value: 5000
keep:
  min_conversions: 2

campaigns:               # per-campaign overrides ("low" matches "low_price")
  low:
    pause_spend: 220
    watch_spend: 120
    scale_roas: 700

budget:                  # budget optimizer
  increase_efficiency: 10
  decrease_efficiency: 3
  shift_share: 0.15
  confidence_conversions: 30

audit:                   # audit engine
  profitable_roas: 500
  high_roas: 1200
  low_ctr: 1.0

excel:                   # workbook rendering
  font_name: Arial
  top_list_size: 10
  output_file: report.xlsx

dashboard:               # dashboard rendering
  title: "PPC Optimizer — Campaign Dashboard"
  header_color: "1F3864"
```

## CLI options

```
ppc-optimizer FILE [FILE ...] [OPTIONS]
```

| Option | Group | Description |
| --- | --- | --- |
| `--config PATH` | Input & Output | Load a custom YAML or JSON configuration |
| `--output PATH` | Input & Output | Workbook path (default: `excel.output_file`) |
| `--explain` | Modes | Print an explanation for every decision |
| `--dry-run` | Modes | Full analysis, summary only, no Excel |
| `--validate` | Modes | Check input files only, exit 0/1 |
| `--verbose` | Diagnostics | Progress stages and debug logging |
| `--version` | Diagnostics | Print `PPC Optimizer` / `v1.0.0` and exit |

**Exit codes:** `0` success · `1` validation error · `2` configuration
error · `3` internal error. Errors are printed as friendly messages —
never Python tracebacks.

## Output workbook

![Executive Summary](docs/screenshots/executive-summary.png)
*<!-- Screenshot placeholder: Executive Summary sheet -->*

| Sheet | Contents |
| --- | --- |
| **Dashboard** | KPI cards, campaign comparison, budget optimization table |
| **Executive Summary** | Key metrics, per-campaign recommendations, action plan |
| **Products** | Every source column + Status, ROAS, Recommendation, Reason |
| **KEEP / WATCH / PAUSE / SCALE** | One sheet per decision, with campaign |
| **Top Winners** | Highest-ROAS products with revenue |
| **Top Losers** | Largest spend with zero conversions |

KPI values, ROAS, and comparison tables are Excel formulas — edit the
Products sheet and the workbook recalculates.

## Troubleshooting

**`Permission denied: 'report.xlsx'`** — the workbook is open in Excel.
Close it and rerun.

**`Column "Conversions" not found. / Found: Conversion`** — a required
column is missing; the message names the closest header found in your
file. Re-export from Google Ads with the standard columns.

**All products land in WATCH** — your per-product spend is below
`watch.max_cost`. Lower it globally or per campaign in `config.yaml`.

**`config.yaml` seems ignored** — the file is looked up in the *current
working directory*. Run from the project root or pass `--config` with a
full path.

**Something odd happened** — check `logs/YYYY-MM-DD.log`; rerun with
`--verbose` to capture debug records and stack traces in the log.

## Development

```bash
pip install -e .[dev]
pytest                 # 99 tests
pytest -m "not slow"   # skip the pip-install packaging test
```

The codebase follows SOLID with one responsibility per module:
`app/loaders` (parsing), `app/analyzers` (decisions and audit),
`app/services` (pipeline, multi-campaign, budget, validation),
`app/reporting` (Excel), `app/config.py` (validated configuration,
loaded once and injected). Business rules live in `config.yaml`, not in
code. Versioning: bump `app/version.py` (pyproject reads it
dynamically) and tag the release.

## License

[MIT](LICENSE) — free for commercial and private use.
