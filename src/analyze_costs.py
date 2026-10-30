"""Command-line entry point for mining operational cost analysis."""

from __future__ import annotations

import argparse
from pathlib import Path

from excel_report.management_report import (
    export_management_report,
    export_management_workbook,
)
from excel_report.models import (
    DataValidationError,
    InputFileError,
    ReportExportError,
    SummaryValidationError,
)
from excel_report.pipeline import run_pipeline
from excel_report.summarizer import generate_executive_summary, load_analysis_payload


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT_PATH = REPOSITORY_ROOT / "data" / "raw" / "accounting_sample.xlsx"
DEFAULT_OUTPUT_DIR = REPOSITORY_ROOT / "data" / "processed"
DEFAULT_REPORT_PATH = REPOSITORY_ROOT / "reports" / "management_report.md"
DEFAULT_EXCEL_REPORT_PATH = REPOSITORY_ROOT / "reports" / "management_report.xlsx"


def parse_arguments() -> argparse.Namespace:
    """Parse optional input and output paths."""
    parser = argparse.ArgumentParser(
        description="Analyze synthetic mining operational costs."
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT_PATH)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument(
        "--report-path",
        type=Path,
        default=DEFAULT_REPORT_PATH,
        help="Markdown management report destination.",
    )
    parser.add_argument(
        "--mode",
        choices=("offline", "gemini"),
        default="offline",
        help="Summary mode. Gemini is opt-in; offline is the default.",
    )
    parser.add_argument(
        "--excel-report-path",
        type=Path,
        default=DEFAULT_EXCEL_REPORT_PATH,
        help="Excel management report destination.",
    )
    return parser.parse_args()


def main() -> int:
    """Run the analysis pipeline and print a concise result summary."""
    arguments = parse_arguments()
    try:
        result = run_pipeline(arguments.input, arguments.output_dir)
        payload = load_analysis_payload(result.json_path)
        summary = generate_executive_summary(payload, mode=arguments.mode)
        report_path = export_management_report(
            payload,
            summary,
            arguments.report_path,
        )
        excel_report_path = export_management_workbook(
            payload,
            summary,
            arguments.excel_report_path,
        )
    except (
        InputFileError,
        DataValidationError,
        ReportExportError,
        SummaryValidationError,
    ) as error:
        print(f"Analysis failed: {error}")
        return 1

    kpis = result.analysis.overall_kpis
    print(f"Transactions: {kpis['transaction_count']}")
    print(f"Total budget (IDR): {kpis['total_budget']:.2f}")
    print(f"Total actual cost (IDR): {kpis['total_actual_cost']:.2f}")
    print(f"Variance (IDR): {kpis['variance']:.2f}")
    print(f"JSON output: {result.json_path}")
    print(f"Department CSV: {result.department_csv_path}")
    print(f"Category CSV: {result.category_csv_path}")
    print(f"Summary source: {summary.source}")
    if summary.fallback_reason:
        print(f"Fallback: {summary.fallback_reason}")
    print(f"Management report: {report_path}")
    print(f"Excel management report: {excel_report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
