"""Application configuration models."""

import json
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict


DEFAULT_CONFIG_FILENAMES: tuple[str, ...] = ("config.yaml", "config.yml", "config.json")
_YAML_SUFFIXES: frozenset[str] = frozenset({".yaml", ".yml"})
_JSON_SUFFIX = ".json"


class ConfigurationError(ValueError):
    """Raised when a threshold configuration file cannot be used."""


class _StrictModel(BaseModel):
    """Base model that rejects unknown configuration keys."""

    model_config = ConfigDict(extra="forbid")


class PauseThresholds(_StrictModel):
    """Rules that mark a product as PAUSE."""

    min_cost: float = 300.0
    max_conversions: float = 0.0


class ScaleThresholds(_StrictModel):
    """Rules that mark a product as SCALE."""

    min_roas: float = 10.0
    min_conversion_value: float = 5000.0


class WatchThresholds(_StrictModel):
    """Rules that mark a product as WATCH due to insufficient data."""

    max_cost: float = 300.0


class KeepThresholds(_StrictModel):
    """Rules that mark a product as KEEP."""

    min_conversions: float = 2.0


class DecisionThresholds(_StrictModel):
    """Every configurable threshold used by product decision rules."""

    pause: PauseThresholds = PauseThresholds()
    scale: ScaleThresholds = ScaleThresholds()
    watch: WatchThresholds = WatchThresholds()
    keep: KeepThresholds = KeepThresholds()


class ReportRequest(BaseModel):
    """Paths required to build a product performance report."""

    source_path: Path
    output_path: Path


def load_thresholds(config_path: Path | None = None) -> DecisionThresholds:
    """Load decision thresholds from a YAML or JSON configuration file.

    Args:
        config_path: Explicit configuration file path. When omitted, the
            default configuration file names are searched in the current
            working directory, and built-in defaults are used when none
            of them exists.

    Returns:
        Validated decision thresholds.

    Raises:
        ConfigurationError: If an explicit path is missing, has an
            unsupported extension, or contains invalid content.
    """
    resolved_path = config_path or _find_default_config()
    if resolved_path is None:
        return DecisionThresholds()

    if not resolved_path.is_file():
        message = f"Configuration file not found: {resolved_path}."
        raise ConfigurationError(message)

    raw_configuration = _parse_configuration(resolved_path)

    try:
        return DecisionThresholds.model_validate(raw_configuration or {})
    except ValueError as error:
        message = f"Invalid threshold configuration in {resolved_path}: {error}"
        raise ConfigurationError(message) from error


def _find_default_config() -> Path | None:
    """Return the first default configuration file in the working directory."""
    for filename in DEFAULT_CONFIG_FILENAMES:
        candidate_path = Path(filename)
        if candidate_path.is_file():
            return candidate_path

    return None


def _parse_configuration(config_path: Path) -> object:
    """Parse a YAML or JSON configuration file into plain Python data."""
    suffix = config_path.suffix.casefold()
    content = config_path.read_text(encoding="utf-8")

    try:
        if suffix in _YAML_SUFFIXES:
            return yaml.safe_load(content)
        if suffix == _JSON_SUFFIX:
            return json.loads(content)
    except (yaml.YAMLError, json.JSONDecodeError) as error:
        message = f"Configuration file {config_path} cannot be parsed: {error}"
        raise ConfigurationError(message) from error

    message = "Only YAML (.yaml, .yml) and JSON (.json) configuration files are supported."
    raise ConfigurationError(message)
