"""JSON and CSV exports for deterministic analysis results."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from .models import AnalysisResult, ReportExportError


def _records(dataframe: pd.DataFrame) -> list[dict[str, Any]]:
    """Convert a summary dataframe into JSON-safe records."""
    records: list[dict[str, Any]] = []
    for record in dataframe.to_dict(orient="records"):
        records.append(
            {
                key: None
                if pd.isna(value)
                else value.item()
                if hasattr(value, "item")
                else value
                for key, value in record.items()
            }
        )
    return records


def build_structured_output(analysis: AnalysisResult) -> dict[str, Any]:
    """Build the aggregate-only payload intended for future Gemini usage."""
    return {
        "metadata": analysis.metadata,
        "overall_kpis": analysis.overall_kpis,
        "department_summary": _records(analysis.department_summary),
        "category_summary": _records(analysis.category_summary),
    }


def export_analysis(
    analysis: AnalysisResult,
    output_dir: Path,
) -> tuple[Path, Path, Path]:
    """Write strict JSON plus department and category CSV outputs."""
    destination = Path(output_dir)
    json_path = destination / "analysis_summary.json"
    department_csv_path = destination / "department_summary.csv"
    category_csv_path = destination / "category_summary.csv"

    try:
        destination.mkdir(parents=True, exist_ok=True)
        with json_path.open("w", encoding="utf-8") as output_file:
            json.dump(
                build_structured_output(analysis),
                output_file,
                ensure_ascii=False,
                indent=2,
                allow_nan=False,
            )
        analysis.department_summary.to_csv(department_csv_path, index=False)
        analysis.category_summary.to_csv(category_csv_path, index=False)
    except (OSError, TypeError, ValueError) as error:
        raise ReportExportError(
            f"Unable to export analysis to '{destination}': {error}"
        ) from error

    return json_path, department_csv_path, category_csv_path
