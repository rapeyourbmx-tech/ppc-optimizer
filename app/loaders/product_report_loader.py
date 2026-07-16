"""Loader for Google Ads product reports stored in CSV or XLSX files."""

import csv
import io
import re
from pathlib import Path

import pandas as pd

from app.loaders.google_ads_product_report_mapper import GoogleAdsProductReportMapper
from app.loaders.metric_normalizer import normalize_metric_values


class UnsupportedReportFormatError(ValueError):
    """Raised when a report file is not a supported CSV or XLSX file."""


class GoogleAdsProductReportLoader:
    """Load a Google Ads product report into a normalized data frame."""

    _CSV_SUFFIX = ".csv"
    _XLSX_SUFFIX = ".xlsx"
    _CSV_ENCODING = "utf-8-sig"
    _CSV_ENGINE = "python"
    _HEADER_MARKERS: frozenset[str] = frozenset({"зображення", "image"})
    _CANDIDATE_DELIMITERS = ",;\t|"
    _DEFAULT_DELIMITER = ","
    _SNIFF_SAMPLE_LINES = 10
    _FIRST_CELL_PATTERN = re.compile(r'^\s*"?([^",;\t|]*)')

    def __init__(self, mapper: GoogleAdsProductReportMapper | None = None) -> None:
        """Initialize the loader with the Google Ads export header mapper."""
        self._mapper = mapper or GoogleAdsProductReportMapper()

    def load(self, source_path: Path) -> pd.DataFrame:
        """Load a CSV or XLSX report and normalize its column names.

        Args:
            source_path: Path to the Google Ads product report export.

        Returns:
            A pandas data frame with normalized column names.

        Raises:
            UnsupportedReportFormatError: If the file is not CSV or XLSX.
        """
        suffix = source_path.suffix.casefold()

        if suffix == self._CSV_SUFFIX:
            report = self._load_csv(source_path)
        elif suffix == self._XLSX_SUFFIX:
            report = pd.read_excel(source_path)
        else:
            message = "Only CSV and XLSX Google Ads product reports are supported."
            raise UnsupportedReportFormatError(message)

        return normalize_metric_values(self._mapper.map(report))

    def _load_csv(self, source_path: Path) -> pd.DataFrame:
        """Read a Google Ads CSV export with header detection and delimiter sniffing.

        Google Ads exports often begin with preamble rows (report title and
        date range) before the header row. The header row is located by its
        first cell ("Зображення" or "Image"), every row before it is skipped,
        and the delimiter is detected from the tabular part of the file.
        Quoted fields keep embedded delimiters, so product names that contain
        commas stay intact. Exports whose data rows are wrapped in one extra
        layer of quoting are unwrapped before parsing.
        """
        lines = source_path.read_text(encoding=self._CSV_ENCODING).splitlines()
        header_index = self._find_header_index(lines)
        tabular_lines = lines[header_index:]
        delimiter = self._detect_delimiter(tabular_lines)
        tabular_lines = self._unwrap_quoted_rows(tabular_lines, delimiter)

        return pd.read_csv(
            io.StringIO("\n".join(tabular_lines)),
            engine=self._CSV_ENGINE,
            sep=delimiter,
        )

    def _unwrap_quoted_rows(self, tabular_lines: list[str], delimiter: str) -> list[str]:
        """Remove one extra quoting layer from fully wrapped data rows.

        Some exports quote every data row as a single field, so a header with
        many columns is followed by rows that parse into exactly one cell.
        Such rows are replaced with their unescaped content, which is the
        original delimited row.
        """
        if not tabular_lines:
            return tabular_lines

        header_cells = self._parse_row(tabular_lines[0], delimiter)
        if len(header_cells) <= 1:
            return tabular_lines

        unwrapped_lines = [tabular_lines[0]]
        for line in tabular_lines[1:]:
            cells = self._parse_row(line, delimiter)
            if len(cells) == 1 and delimiter in cells[0]:
                unwrapped_lines.append(cells[0])
            else:
                unwrapped_lines.append(line)

        return unwrapped_lines

    @staticmethod
    def _parse_row(line: str, delimiter: str) -> list[str]:
        """Parse one physical line into CSV cells."""
        return next(csv.reader([line], delimiter=delimiter), [])

    def _find_header_index(self, lines: list[str]) -> int:
        """Return the index of the first row whose leading cell is a header marker.

        Falls back to the first row for exports that have no preamble and no
        image column, keeping plain tabular CSV files loadable.
        """
        for line_index, line in enumerate(lines):
            if self._first_cell(line) in self._HEADER_MARKERS:
                return line_index

        return 0

    def _first_cell(self, line: str) -> str:
        """Extract the first delimited cell of a line without knowing the delimiter."""
        match = self._FIRST_CELL_PATTERN.match(line)
        if match is None:
            return ""

        return match.group(1).strip().casefold()

    def _detect_delimiter(self, tabular_lines: list[str]) -> str:
        """Detect the CSV delimiter from the tabular part of the export."""
        sample = "\n".join(tabular_lines[: self._SNIFF_SAMPLE_LINES])

        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=self._CANDIDATE_DELIMITERS)
        except csv.Error:
            return self._DEFAULT_DELIMITER

        return dialect.delimiter
