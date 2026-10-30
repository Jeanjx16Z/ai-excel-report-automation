"""Tests for deterministic Markdown management reporting."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = REPOSITORY_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from excel_report.management_report import (  # noqa: E402
    export_management_report,
    render_management_report,
)
from excel_report.summarizer import generate_executive_summary  # noqa: E402
from test_summarizer import analysis_payload  # noqa: E402


class ManagementReportTests(unittest.TestCase):
    def test_offline_report_uses_kpis_from_analysis_payload(self) -> None:
        payload = analysis_payload()
        summary = generate_executive_summary(payload)

        report = render_management_report(payload, summary)

        self.assertIn("Rp300", report)
        self.assertIn("Rp320", report)
        self.assertIn("Rp20", report)
        self.assertIn("Offline deterministic template", report)
        self.assertIn("bukan data asli perusahaan", report)

    def test_markdown_report_is_written(self) -> None:
        payload = analysis_payload()
        summary = generate_executive_summary(payload)
        with tempfile.TemporaryDirectory() as temporary_directory:
            output_path = Path(temporary_directory) / "management_report.md"

            result_path = export_management_report(payload, summary, output_path)

            self.assertEqual(output_path, result_path)
            self.assertTrue(output_path.is_file())
            self.assertIn(
                "# Mining Operational Cost",
                output_path.read_text(encoding="utf-8"),
            )

    def test_provider_failure_report_keeps_numeric_results_and_safe_status(self) -> None:
        class FailingClient:
            def generate(self, payload: dict) -> dict:
                raise TimeoutError("secret-value must not appear")

        payload = analysis_payload()
        summary = generate_executive_summary(
            payload, mode="gemini", client=FailingClient()
        )

        report = render_management_report(payload, summary)

        self.assertIn("Offline deterministic fallback", report)
        self.assertIn("api_request_or_response_parse", report)
        self.assertIn("TimeoutError", report)
        self.assertNotIn("secret-value", report)
        self.assertIn("| Total Budget | Rp300 |", report)
        self.assertIn("| Total Actual Cost | Rp320 |", report)
        self.assertIn("| Variance | Rp20 |", report)


if __name__ == "__main__":
    unittest.main()
