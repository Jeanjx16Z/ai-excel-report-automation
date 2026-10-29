"""Pipeline orchestration for deterministic mining cost analysis."""

from __future__ import annotations

from pathlib import Path

from .excel_io import read_excel
from .kpi import calculate_kpis
from .models import PipelineResult
from .reporting import export_analysis
from .validation import validate_data


def run_pipeline(input_path: Path, output_dir: Path) -> PipelineResult:
    """Read, validate, analyze, and export one mining cost workbook."""
    raw_dataframe = read_excel(input_path)
    validated_dataframe = validate_data(raw_dataframe)
    analysis = calculate_kpis(validated_dataframe)
    json_path, department_csv_path, category_csv_path = export_analysis(
        analysis,
        output_dir,
    )
    return PipelineResult(
        analysis=analysis,
        json_path=json_path,
        department_csv_path=department_csv_path,
        category_csv_path=category_csv_path,
    )
