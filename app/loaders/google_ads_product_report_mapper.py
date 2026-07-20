"""Google Ads Product report header mapping."""

import pandas as pd

from app.utils.column_names import normalize_column_names

GOOGLE_ADS_PRODUCT_SCHEMA: tuple[str, ...] = (
    "product_id",
    "product",
    "clicks",
    "impressions",
    "ctr",
    "average_cpc",
    "cost",
    "conversions",
    "conversion_value",
    "cost_per_conversion",
    "all_conversions",
    "all_conversion_value",
)
_REQUIRED_COLUMNS: tuple[str, ...] = (
    "product_id",
    "clicks",
    "impressions",
    "cost",
    "conversions",
    "conversion_value",
)


class GoogleAdsProductReportMappingError(ValueError):
    """Raised when a Google Ads Product export cannot be mapped safely."""


class MissingColumnsError(GoogleAdsProductReportMappingError):
    """Raised when required columns are absent, with data for friendly output."""

    def __init__(
        self,
        message: str,
        *,
        missing_columns: list[str],
        available_columns: list[str],
    ) -> None:
        """Store the missing canonical columns and the file's actual headers."""
        super().__init__(message)
        self.missing_columns = missing_columns
        self.available_columns = available_columns


class GoogleAdsProductReportMapper:
    """Map English and Ukrainian Google Ads export headers to one schema."""

    _COLUMN_ALIASES: dict[str, tuple[str, ...]] = {
        "product_id": (
            "product_id",
            "item_id",
            "ідентифікатор_товару",
            "ід_товару",
            "ідентифікатор_елемента",
        ),
        "product": (
            "product",
            "item_title",
            "product_title",
            "title",
            "товар",
            "назва_товару",
            "назва",
        ),
        "clicks": ("clicks", "кліки"),
        "impressions": ("impressions", "покази"),
        "ctr": ("ctr",),
        "average_cpc": (
            "average_cpc",
            "avg_cpc",
            "сер_ціна_за_клік",
            "середня_ціна_за_клік",
            "сер_cpc",
        ),
        "cost": ("cost", "вартість"),
        "conversions": ("conversions", "conv", "конверсії", "конв"),
        "conversion_value": (
            "conversion_value",
            "conv_value",
            "цінність_конверсії",
            "цінність_конверсій",
            "цінність_конв",
        ),
        "cost_per_conversion": ("cost_conv", "cost_per_conv", "вартість_конв"),
        "all_conversions": ("all_conversions", "all_conv", "усі_конверсії", "усі_конв"),
        "all_conversion_value": (
            "all_conv_value",
            "all_conversions_value",
            "цінність_усіх_конверсій",
            "цінність_усіх_конв",
        ),
    }

    def map(self, report: pd.DataFrame) -> pd.DataFrame:
        """Normalize and map a Google Ads Product export to the internal schema."""
        original_columns = [str(column) for column in report.columns]
        normalized_report = normalize_column_names(report)
        mapped_report = normalized_report.rename(columns=self._rename_columns())

        self._validate_unique_columns(mapped_report)
        self._validate_required_columns(mapped_report, original_columns)
        return mapped_report.loc[:, self._ordered_columns(mapped_report)]

    def _rename_columns(self) -> dict[str, str]:
        """Build the normalized-export-header to internal-schema mapping."""
        return {
            export_column: internal_column
            for internal_column, aliases in self._COLUMN_ALIASES.items()
            for export_column in aliases
        }

    def _validate_unique_columns(self, report: pd.DataFrame) -> None:
        """Reject exports that map more than one column to the same field."""
        duplicated_mask = report.columns.duplicated()
        duplicate_columns = report.columns[duplicated_mask].unique().tolist()
        if duplicate_columns:
            names = ", ".join(sorted(map(str, duplicate_columns)))
            message = f"Multiple export columns map to the same internal fields: {names}."
            raise GoogleAdsProductReportMappingError(message)

    def _validate_required_columns(
        self,
        report: pd.DataFrame,
        original_columns: list[str],
    ) -> None:
        """Ensure the report has the metrics required by the application pipeline."""
        missing_columns = sorted(set(_REQUIRED_COLUMNS) - set(report.columns))
        if missing_columns:
            names = ", ".join(missing_columns)
            message = (
                "The file is not a complete Google Ads Product report. "
                f"Missing required columns: {names}."
            )
            raise MissingColumnsError(
                message,
                missing_columns=missing_columns,
                available_columns=original_columns,
            )

    def _ordered_columns(self, report: pd.DataFrame) -> list[str]:
        """Place recognized columns in canonical schema order before extras."""
        recognized_columns = [
            column_name
            for column_name in GOOGLE_ADS_PRODUCT_SCHEMA
            if column_name in report.columns
        ]
        additional_columns = [
            column_name
            for column_name in report.columns
            if column_name not in GOOGLE_ADS_PRODUCT_SCHEMA
        ]
        return [*recognized_columns, *additional_columns]
