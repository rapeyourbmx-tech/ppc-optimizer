"""Tests for threshold configuration loading."""

from pathlib import Path

import pytest

from app.config import (
    ConfigurationError,
    DecisionThresholds,
    load_configuration,
    load_thresholds,
)


def test_load_thresholds_returns_defaults_without_config_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Built-in defaults are used when no configuration file exists."""
    monkeypatch.chdir(tmp_path)

    assert load_thresholds() == DecisionThresholds()


def test_load_thresholds_reads_partial_yaml_overrides(tmp_path: Path) -> None:
    """YAML files may override a subset of thresholds; the rest keep defaults."""
    config_path = tmp_path / "custom.yaml"
    config_path.write_text("scale:\n  min_roas: 50\n", encoding="utf-8")

    thresholds = load_thresholds(config_path)

    assert thresholds.scale.min_roas == 50.0
    assert thresholds.scale.min_conversion_value == 5000.0
    assert thresholds.pause.min_cost == 300.0


def test_load_thresholds_reads_json_file(tmp_path: Path) -> None:
    """JSON configuration files are supported alongside YAML."""
    config_path = tmp_path / "custom.json"
    config_path.write_text('{"keep": {"min_conversions": 5}}', encoding="utf-8")

    thresholds = load_thresholds(config_path)

    assert thresholds.keep.min_conversions == 5.0


def test_load_thresholds_finds_default_file_in_working_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A config.yaml in the working directory is picked up automatically."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "config.yaml").write_text("pause:\n  min_cost: 111\n", encoding="utf-8")

    thresholds = load_thresholds()

    assert thresholds.pause.min_cost == 111.0


def test_load_thresholds_rejects_missing_explicit_path(tmp_path: Path) -> None:
    """An explicit configuration path must exist."""
    with pytest.raises(ConfigurationError, match="not found"):
        load_thresholds(tmp_path / "missing.yaml")


def test_load_thresholds_rejects_unknown_keys(tmp_path: Path) -> None:
    """Misspelled configuration keys produce an informative error."""
    config_path = tmp_path / "custom.yaml"
    config_path.write_text("pasue:\n  min_cost: 300\n", encoding="utf-8")

    with pytest.raises(ConfigurationError, match="Invalid threshold configuration"):
        load_thresholds(config_path)


def test_load_thresholds_rejects_unsupported_extension(tmp_path: Path) -> None:
    """Only YAML and JSON configuration files are supported."""
    config_path = tmp_path / "config.toml"
    config_path.write_text("[pause]\nmin_cost = 300\n", encoding="utf-8")

    with pytest.raises(ConfigurationError, match="Only YAML"):
        load_thresholds(config_path)


def test_load_configuration_reads_campaign_overrides(tmp_path: Path) -> None:
    """Campaign sections override pause, watch, and scale thresholds."""
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        "watch:\n  max_cost: 300\n"
        "campaigns:\n"
        "  low:\n"
        "    pause_spend: 220\n"
        "    watch_spend: 120\n"
        "    scale_roas: 700\n",
        encoding="utf-8",
    )

    configuration = load_configuration(config_path)
    low_thresholds = configuration.thresholds_for_campaign("low_price")

    assert low_thresholds.pause.min_cost == 220.0
    assert low_thresholds.watch.max_cost == 120.0
    assert low_thresholds.scale.min_roas == 700.0
    assert low_thresholds.keep.min_conversions == 2.0


def test_thresholds_for_campaign_without_override_returns_base(
    tmp_path: Path,
) -> None:
    """Campaigns without a matching section use the global thresholds."""
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        "campaigns:\n  low:\n    watch_spend: 120\n",
        encoding="utf-8",
    )

    configuration = load_configuration(config_path)

    assert configuration.thresholds_for_campaign("brand").watch.max_cost == 300.0


def test_thresholds_for_campaign_prefers_most_specific_key(tmp_path: Path) -> None:
    """When several keys match, the longest one wins."""
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        "campaigns:\n"
        "  low:\n    watch_spend: 120\n"
        "  low_price:\n    watch_spend: 90\n",
        encoding="utf-8",
    )

    configuration = load_configuration(config_path)

    assert configuration.thresholds_for_campaign("low_price").watch.max_cost == 90.0
    assert configuration.thresholds_for_campaign("low_value").watch.max_cost == 120.0


def test_load_configuration_rejects_unknown_campaign_keys(tmp_path: Path) -> None:
    """Misspelled campaign override keys produce an informative error."""
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        "campaigns:\n  low:\n    pause_spent: 220\n",
        encoding="utf-8",
    )

    with pytest.raises(ConfigurationError, match="Invalid threshold configuration"):
        load_configuration(config_path)


def test_load_configuration_reads_audit_excel_and_dashboard_sections(
    tmp_path: Path,
) -> None:
    """Audit, Excel, and dashboard settings load from the configuration file."""
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        "audit:\n  low_ctr: 2.5\n"
        "excel:\n  font_name: Calibri\n  top_list_size: 5\n"
        "dashboard:\n  title: My Dashboard\n  header_color: '336699'\n",
        encoding="utf-8",
    )

    configuration = load_configuration(config_path)

    assert configuration.audit.low_ctr == 2.5
    assert configuration.audit.profitable_roas == 500.0
    assert configuration.excel.font_name == "Calibri"
    assert configuration.excel.top_list_size == 5
    assert configuration.excel.output_file == "report.xlsx"
    assert configuration.dashboard.title == "My Dashboard"
    assert configuration.dashboard.header_color == "336699"


def test_load_configuration_rejects_unknown_settings_keys(tmp_path: Path) -> None:
    """Misspelled keys in the settings sections produce an informative error."""
    config_path = tmp_path / "config.yaml"
    config_path.write_text("excel:\n  font: Calibri\n", encoding="utf-8")

    with pytest.raises(ConfigurationError, match="Invalid threshold configuration"):
        load_configuration(config_path)
