# Changelog

All notable changes to this project are documented in this file.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and the project adheres to [Semantic Versioning](https://semver.org/).

## [1.1.0] — 2026-07-20

### Added

- **Desktop graphical interface** (`ppc-optimizer-gui`, `start-gui.bat`):
  choose report files with native dialogs, press one button, get the
  workbook — no command line required. Runs the analysis in a background
  thread through the same pipeline as the CLI, with Open report and Open
  folder buttons on success.

## [1.0.0] — 2026-07-20

First production release.

### Added

- **Report loader** for real Google Ads product exports: automatic header-row
  detection (`Зображення` / `Image`), delimiter sniffing, UTF-8 BOM handling,
  unwrapping of double-quoted data rows, Ukrainian and English header aliases,
  and locale-aware numeric normalization (currency prefixes, non-breaking
  thousands separators, decimal commas, percent values)
- **Decision engine** classifying every product as KEEP / WATCH / PAUSE /
  SCALE with a stored metric-based explanation (`--explain`)
- **Configuration system** (`config.yaml`, YAML or JSON): decision thresholds,
  per-campaign overrides, budget optimizer, audit thresholds, Excel and
  dashboard rendering settings; validated with pydantic, loaded once on
  startup, injected into every service; no hardcoded thresholds in code
- **Multi-campaign analysis**: each input file becomes a campaign; every
  product keeps campaign_name, campaign_type, and source_file; per-campaign
  summaries plus an aggregated overall summary
- **Budget optimizer**: marginal efficiency and saturation scores,
  INCREASE / KEEP / DECREASE recommendations, and concrete transfers with
  expected revenue gain and confidence
- **Excel workbook** (9 sheets): Dashboard with KPI cards, campaign
  comparison, and budget optimization tables; Executive Summary with
  per-campaign recommendations and an action plan; Products with Status,
  ROAS, Recommendation, and Reason columns; per-status sheets; Top Winners
  and Top Losers — with conditional formatting, frozen headers, autofilters,
  auto-fitted columns, and formula-backed values
- **Production CLI**: `--config`, `--output`, `--explain`, `--dry-run`,
  `--validate`, `--verbose`, `--version`; grouped help; friendly errors with
  Expected/Found column suggestions; exit codes 0/1/2/3; no Python tracebacks
- **File validator**: required columns, duplicated SKUs, invalid numeric
  values, unsupported file types
- **Logging**: automatic `logs/YYYY-MM-DD.log` with version, inputs, product
  counts, warnings, and execution time; debug records and stack traces only
  with `--verbose`
- **Packaging**: `pip install .`, `ppc-optimizer` console entry point,
  MIT license, dynamic version from `app/version.py`
- **Test suite**: 99 tests, including a real pip-installation check

[1.1.0]: https://github.com/rapeyourbmx-tech/ppc-optimizer/releases/tag/v1.1.0
[1.0.0]: https://github.com/rapeyourbmx-tech/ppc-optimizer/releases/tag/v1.0.0
