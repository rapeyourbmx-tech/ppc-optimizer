"""Validation of Google Ads product report files."""

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from app.loaders.product_report_loader import GoogleAdsProductReportLoader

_SUPPORTED_SUFFIXES: frozenset[str] = frozenset({".csv", ".xlsx"})
_METRIC_COLUMNS: tuple[str, ...] = (
    "clicks",
    "impressions",
    "cost",
    "conversions",
    "conversion_value",
)
_MAX_LISTED_SKUS = 5


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    """One problem found in one report file."""

    source_file: str
    message: str


@dataclass(frozen=True, slots=True)
class ValidationResult:
    """Outcome of validating one or more report files."""

    issues: list[ValidationIssue]
    checked_files: int

    @property
    def is_valid(self) -> bool:
        """Return True when no issues were found."""
        return not self.issues


class ReportValidator:
    """Check report files for structural and data problems without analyzing."""

    def __init__(self, loader: GoogleAdsProductReportLoader | None = None) -> None:
        """Initialize the validator with the report loader it reuses."""
        self._loader = loader or GoogleAdsProductReportLoader()

    def validate(self, source_paths: Sequence[Path]) -> ValidationResult:
        """Validate every supplied file and collect all issues."""
        issues: list[ValidationIssue] = []
        for source_path in source_paths:
            issues.extend(self._validate_file(source_path))

        return ValidationResult(issues=issues, checked_files=len(source_paths))

    def _validate_file(self, source_path: Path) -> list[ValidationIssue]:
        """Validate one report file."""
        file_name = source_path.name

        if source_path.suffix.casefold() not in _SUPPORTED_SUFFIXES:
            message = (
                f"Unsupported file type '{source_path.suffix}'. "
                "Only CSV and XLSX reports are supported."
            )
            return [ValidationIssue(source_file=file_name, message=message)]

        if not source_path.is_file():
            return [ValidationIssue(source_file=file_name, message="File not found.")]

        try:
            report = self._loader.load(source_path)
        except (ValueError, OSError) as error:
            return [ValidationIssue(source_file=file_name, message=str(error))]

        issues: list[ValidationIssue] = []
        issues.extend(self._duplicated_sku_issues(file_name, report))
        issues.extend(self._invalid_numeric_issues(file_name, report))
        return issues

    @staticmethod
    def _duplicated_sku_issues(file_name: str, report) -> list[ValidationIssue]:
        """Flag SKUs that appear in more than one row."""
        if "product_id" not in report.columns:
            return []

        sku_values = report["product_id"].astype(str)
        duplicated = sorted(set(sku_values[sku_values.duplicated(keep=False)]))
        if not duplicated:
            return []

        listed = ", ".join(duplicated[:_MAX_LISTED_SKUS])
        suffix = ", …" if len(duplicated) > _MAX_LISTED_SKUS else ""
        message = f"Duplicated SKUs ({len(duplicated)}): {listed}{suffix}"
        return [ValidationIssue(source_file=file_name, message=message)]

    @staticmethod
    def _invalid_numeric_issues(file_name: str, report) -> list[ValidationIssue]:
        """Flag metric cells that could not be parsed as numbers."""
        issues: list[ValidationIssue] = []
        for column_name in _METRIC_COLUMNS:
            if column_name not in report.columns:
                continue
            invalid_count = int(report[column_name].isna().sum())
            if invalid_count:
                message = (
                    f"{invalid_count} invalid or missing numeric value(s) "
                    f"in column '{column_name}'."
                )
                issues.append(ValidationIssue(source_file=file_name, message=message))

        return issues
