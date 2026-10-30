"""Tests for offline, structured, and fallback summary behavior."""

from __future__ import annotations

from copy import deepcopy
import sys
import unittest
from pathlib import Path
from typing import Any


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = REPOSITORY_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from excel_report.gemini_client import build_gemini_prompt_payload  # noqa: E402
from excel_report.models import SummaryValidationError  # noqa: E402
from excel_report.summary_contract import (  # noqa: E402
    EXECUTIVE_SUMMARY_SCHEMA,
    SYNTHETIC_DISCLAIMER,
)
from excel_report.summarizer import (  # noqa: E402
    generate_executive_summary,
    validate_analysis_payload,
    validate_summary_response,
)


def analysis_payload() -> dict[str, Any]:
    return {
        "metadata": {
            "period_start": "2025-01-01",
            "period_end": "2025-12-31",
            "currency": "IDR",
            "synthetic_data": True,
        },
        "overall_kpis": {
            "total_budget": 300.0,
            "total_actual_cost": 320.0,
            "variance": 20.0,
            "variance_pct": 6.67,
            "transaction_count": 2,
            "over_budget_count": 1,
            "under_budget_count": 1,
            "on_budget_count": 0,
        },
        "department_summary": [
            {
                "department": "Mining Operations",
                "budget": 300.0,
                "actual_cost": 320.0,
                "variance": 20.0,
                "variance_pct": 6.67,
                "transaction_count": 2,
            }
        ],
        "category_summary": [
            {
                "category": "Diesel Fuel",
                "budget": 300.0,
                "actual_cost": 320.0,
                "variance": 20.0,
                "variance_pct": 6.67,
                "transaction_count": 2,
            }
        ],
    }


def valid_gemini_response() -> dict[str, Any]:
    return {
        "executive_summary": "Biaya agregat berada di atas anggaran.",
        "key_findings": ["Variance total bernilai positif."],
        "potential_risks": [
            {
                "statement": "Penyebab variance perlu diverifikasi.",
                "evidence_level": "hypothesis",
            }
        ],
        "actionable_recommendations": ["Lakukan review variance."],
        "synthetic_data_disclaimer": SYNTHETIC_DISCLAIMER,
    }


class FakeGeminiClient:
    def __init__(self, response: dict[str, Any] | None = None) -> None:
        self.response = response or valid_gemini_response()
        self.received_payload: dict[str, Any] | None = None

    def generate(self, payload: dict[str, Any]) -> dict[str, Any]:
        self.received_payload = payload
        return self.response


class FailingGeminiClient:
    def generate(self, payload: dict[str, Any]) -> dict[str, Any]:
        raise TimeoutError("mock timeout")


class ServerError(Exception):
    """Local fake provider error; no SDK or network involved."""


class ServerFailingGeminiClient:
    def generate(self, payload: dict[str, Any]) -> dict[str, Any]:
        raise ServerError("secret-token and raw payload must not be exposed")


class UnexpectedCallClient:
    def generate(self, payload: dict[str, Any]) -> dict[str, Any]:
        raise AssertionError("Gemini client must not be called for an invalid payload")


class SummarizerTests(unittest.TestCase):
    def test_gemini_prompt_payload_uses_final_display_values_without_mutation(self) -> None:
        payload = analysis_payload()
        payload["department_summary"][0]["variance_pct"] = 2.4954394693200666
        payload["category_summary"][0]["variance_pct"] = 7.669270833333333
        payload["department_summary"][0]["budget"] = 36_180_000_000.0
        original_payload = deepcopy(payload)

        prompt_payload = build_gemini_prompt_payload(payload)

        self.assertEqual(
            "2.50%", prompt_payload["department_summary"][0]["variance_pct"]
        )
        self.assertEqual(
            "7.67%", prompt_payload["category_summary"][0]["variance_pct"]
        )
        self.assertEqual(
            "Rp36.180.000.000", prompt_payload["department_summary"][0]["budget"]
        )
        self.assertIsInstance(
            prompt_payload["overall_kpis"]["transaction_count"], int
        )
        self.assertEqual(original_payload, payload)
        self.assertEqual(
            {
                "metadata",
                "overall_kpis",
                "department_summary",
                "category_summary",
            },
            set(prompt_payload),
        )
        self.assertNotIn("transactions", prompt_payload)

    def test_offline_summary_is_deterministic(self) -> None:
        first = generate_executive_summary(analysis_payload())
        second = generate_executive_summary(analysis_payload())

        self.assertEqual(first, second)
        self.assertEqual("offline", first.source)
        self.assertIn("data sintetis", first.synthetic_data_disclaimer.lower())

    def test_mocked_gemini_receives_only_aggregate_payload(self) -> None:
        client = FakeGeminiClient()

        result = generate_executive_summary(
            analysis_payload(), mode="gemini", client=client
        )

        self.assertEqual("gemini", result.source)
        self.assertIsNotNone(client.received_payload)
        self.assertNotIn("transactions", client.received_payload or {})

    def test_invalid_structured_response_is_rejected(self) -> None:
        response = valid_gemini_response()
        response["actionable_recommendations"] = ["item"] * 4

        with self.assertRaisesRegex(SummaryValidationError, "1 to 3"):
            validate_summary_response(response)

    def test_raw_transaction_section_is_rejected(self) -> None:
        payload = analysis_payload()
        payload["transactions"] = [{"sensitive": "raw row"}]

        with self.assertRaisesRegex(SummaryValidationError, "unexpected sections"):
            validate_analysis_payload(payload)

    def test_invalid_payload_stops_before_gemini_client_call(self) -> None:
        payload = analysis_payload()
        payload["transactions"] = [{"sensitive": "raw row"}]

        with self.assertRaisesRegex(SummaryValidationError, "unexpected sections"):
            generate_executive_summary(
                payload,
                mode="gemini",
                client=UnexpectedCallClient(),
            )

    def test_gemini_failure_falls_back_without_ai_claim(self) -> None:
        result = generate_executive_summary(
            analysis_payload(), mode="gemini", client=FailingGeminiClient()
        )

        self.assertEqual("offline_fallback", result.source)
        self.assertIn("TimeoutError", result.fallback_reason or "")
        self.assertIn("api_request_or_response_parse", result.fallback_reason or "")
        self.assertNotIn("AI generated", result.executive_summary)

    def test_server_error_fallback_reason_does_not_expose_error_message(self) -> None:
        result = generate_executive_summary(
            analysis_payload(), mode="gemini", client=ServerFailingGeminiClient()
        )

        self.assertEqual("offline_fallback", result.source)
        self.assertIn("ServerError", result.fallback_reason or "")
        self.assertIn("api_request_or_response_parse", result.fallback_reason or "")
        self.assertNotIn("secret-token", result.fallback_reason or "")
        self.assertNotIn("raw payload", result.fallback_reason or "")

    def test_response_validation_failure_reports_field_and_stage(self) -> None:
        response = valid_gemini_response()
        response["synthetic_data_disclaimer"] = (
            "Informasi ini dibuat untuk simulasi dan tidak berasal dari perusahaan nyata."
        )

        result = generate_executive_summary(
            analysis_payload(),
            mode="gemini",
            client=FakeGeminiClient(response),
        )

        self.assertEqual("offline_fallback", result.source)
        self.assertIn("response_validation", result.fallback_reason or "")
        self.assertIn("synthetic_data_disclaimer", result.fallback_reason or "")
        self.assertNotIn(response["synthetic_data_disclaimer"], result.fallback_reason or "")

    def test_schema_requires_canonical_synthetic_disclaimer(self) -> None:
        disclaimer_schema = EXECUTIVE_SUMMARY_SCHEMA["properties"][
            "synthetic_data_disclaimer"
        ]

        self.assertEqual([SYNTHETIC_DISCLAIMER], disclaimer_schema["enum"])

    def test_structured_response_whitespace_is_normalized(self) -> None:
        response = valid_gemini_response()
        response["executive_summary"] = "  Biaya   agregat\nberada di atas anggaran.  "
        response["key_findings"] = ["Variance\n\ntotal   bernilai positif."]
        response["potential_risks"][0]["statement"] = (
            "Penyebab   variance\nperlu diverifikasi."
        )
        response["actionable_recommendations"] = ["  Lakukan   review\nvariance. "]

        result = validate_summary_response(response)

        self.assertEqual(
            "Biaya agregat berada di atas anggaran.", result.executive_summary
        )
        self.assertEqual(("Variance total bernilai positif.",), result.key_findings)
        self.assertEqual(
            "Penyebab variance perlu diverifikasi.",
            result.potential_risks[0]["statement"],
        )
        self.assertEqual(
            ("Lakukan review variance.",), result.actionable_recommendations
        )
        self.assertEqual(SYNTHETIC_DISCLAIMER, result.synthetic_data_disclaimer)


if __name__ == "__main__":
    unittest.main()
