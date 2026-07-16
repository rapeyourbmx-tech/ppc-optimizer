"""Tests for threshold configuration loading."""

from pathlib import Path

import pytest

from app.config import ConfigurationError, DecisionThresholds, load_thresholds


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
