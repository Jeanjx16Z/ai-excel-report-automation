"""Shared result models and domain exceptions."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd


class InputFileError(Exception):
    """Raised when an input workbook cannot be read."""


class DataValidationError(Exception):
    """Raised when input data violates the agreed dataset contract."""


class ReportExportError(Exception):
    """Raised when structured analysis output cannot be written."""


class SummaryValidationError(Exception):
    """Raised when a summary payload or response violates its schema."""


@dataclass(frozen=True)
class AnalysisResult:
    """Deterministic KPI result before serialization."""

    metadata: dict[str, Any]
    overall_kpis: dict[str, Any]
    department_summary: pd.DataFrame
    category_summary: pd.DataFrame


@dataclass(frozen=True)
class PipelineResult:
    """Structured pipeline result and generated output paths."""

    analysis: AnalysisResult
    json_path: Path
    department_csv_path: Path
    category_csv_path: Path


@dataclass(frozen=True)
class ExecutiveSummaryResult:
    """Validated interpretation generated offline or by Gemini."""

    executive_summary: str
    key_findings: tuple[str, ...]
    potential_risks: tuple[dict[str, str], ...]
    actionable_recommendations: tuple[str, ...]
    synthetic_data_disclaimer: str
    source: str
    fallback_reason: str | None = None
