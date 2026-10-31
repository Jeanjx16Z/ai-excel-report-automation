"""Thin import boundary; no CLI execution, exports, or numerical duplication."""

from pathlib import Path

from excel_report.excel_io import read_excel
from excel_report.kpi import calculate_kpis
from excel_report.validation import validate_data


def analyze_workbook(input_path: Path):
    return calculate_kpis(validate_data(read_excel(input_path)))
