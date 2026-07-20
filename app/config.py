"""Application configuration models."""

import json
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field

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


class AuditThresholds(_StrictModel):
    """Thresholds used by the campaign audit engine."""

    profitable_roas: float = 500.0
    high_roas: float = 1200.0
    low_ctr: float = 1.0


class ExcelSettings(_StrictModel):
    """Workbook-wide Excel rendering settings."""

    font_name: str = "Arial"
    min_column_width: float = 9.0
    max_column_width: float = 45.0
    top_list_size: int = 10
    output_file: str = "report.xlsx"


class DashboardSettings(_StrictModel):
    """Dashboard sheet rendering settings."""

    title: str = "PPC Optimizer — Campaign Dashboard"
    header_color: str = "1F3864"
    card_fill_color: str = "F5F7FA"
    roas_color_scale_max: float = 10.0


class BudgetThresholds(_StrictModel):
    """Thresholds driving budget redistribution recommendations."""

    increase_efficiency: float = 10.0
    decrease_efficiency: float = 3.0
    shift_share: float = 0.15
    confidence_conversions: float = 30.0


class CampaignThresholds(_StrictModel):
    """Shorthand per-campaign overrides of the global thresholds."""

    pause_spend: float | None = None
    watch_spend: float | None = None
    scale_roas: float | None = None


class ThresholdConfiguration(_StrictModel):
    """Global decision thresholds plus optional per-campaign overrides."""

    pause: PauseThresholds = PauseThresholds()
    scale: ScaleThresholds = ScaleThresholds()
    watch: WatchThresholds = WatchThresholds()
    keep: KeepThresholds = KeepThresholds()
    budget: BudgetThresholds = BudgetThresholds()
    audit: AuditThresholds = AuditThresholds()
    excel: ExcelSettings = ExcelSettings()
    dashboard: DashboardSettings = DashboardSettings()
    campaigns: dict[str, CampaignThresholds] = Field(default_factory=dict)

    def base_thresholds(self) -> DecisionThresholds:
        """Return the global thresholds without any campaign override."""
        return DecisionThresholds(
            pause=self.pause,
            scale=self.scale,
            watch=self.watch,
            keep=self.keep,
        )

    def thresholds_for_campaign(self, campaign_name: str) -> DecisionThresholds:
        """Return the thresholds for one campaign, applying its override.

        A campaign section matches when its key equals the campaign name or
        is contained in it (case-insensitive), so a "low" section applies to
        a campaign named "low_price". The most specific (longest) matching
        key wins. Thresholds absent from the override keep the global values.
        """
        override = self._matching_override(campaign_name)
        if override is None:
            return self.base_thresholds()

        return DecisionThresholds(
            pause=PauseThresholds(
                min_cost=(
                    override.pause_spend
                    if override.pause_spend is not None
                    else self.pause.min_cost
                ),
                max_conversions=self.pause.max_conversions,
            ),
            scale=ScaleThresholds(
                min_roas=(
                    override.scale_roas if override.scale_roas is not None else self.scale.min_roas
                ),
                min_conversion_value=self.scale.min_conversion_value,
            ),
            watch=WatchThresholds(
                max_cost=(
                    override.watch_spend
                    if override.watch_spend is not None
                    else self.watch.max_cost
                ),
            ),
            keep=self.keep,
        )

    def _matching_override(self, campaign_name: str) -> CampaignThresholds | None:
        """Return the campaign override matching one campaign name."""
        lowered_name = campaign_name.casefold()
        normalized = {key.casefold(): override for key, override in self.campaigns.items()}
        if lowered_name in normalized:
            return normalized[lowered_name]

        matches = [(key, override) for key, override in normalized.items() if key in lowered_name]
        if not matches:
            return None

        return max(matches, key=lambda match: len(match[0]))[1]


class ReportRequest(BaseModel):
    """Paths required to build a product performance report."""

    source_path: Path
    output_path: Path


def load_configuration(config_path: Path | None = None) -> ThresholdConfiguration:
    """Load the threshold configuration from a YAML or JSON file.

    Args:
        config_path: Explicit configuration file path. When omitted, the
            default configuration file names are searched in the current
            working directory, and built-in defaults are used when none
            of them exists.

    Returns:
        Validated global thresholds with per-campaign overrides.

    Raises:
        ConfigurationError: If an explicit path is missing, has an
            unsupported extension, or contains invalid content.
    """
    resolved_path = config_path or _find_default_config()
    if resolved_path is None:
        return ThresholdConfiguration()

    if not resolved_path.is_file():
        message = f"Configuration file not found: {resolved_path}."
        raise ConfigurationError(message)

    raw_configuration = _parse_configuration(resolved_path)

    try:
        return ThresholdConfiguration.model_validate(raw_configuration or {})
    except ValueError as error:
        message = f"Invalid threshold configuration in {resolved_path}: {error}"
        raise ConfigurationError(message) from error


def load_thresholds(config_path: Path | None = None) -> DecisionThresholds:
    """Load only the global decision thresholds (no campaign overrides).

    Kept for backward compatibility; see load_configuration for details.
    """
    return load_configuration(config_path).base_thresholds()


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


# The configuration now covers the whole application, not only thresholds.
AppConfiguration = ThresholdConfiguration
