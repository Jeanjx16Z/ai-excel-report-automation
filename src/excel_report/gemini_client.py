"""Isolated google-genai adapter for structured executive summaries."""

from __future__ import annotations

import json
from typing import Any

from .config import get_gemini_api_key, get_gemini_model
from .summary_contract import EXECUTIVE_SUMMARY_SCHEMA, SYNTHETIC_DISCLAIMER


SYSTEM_INSTRUCTIONS = """Anda adalah analis biaya operasional pertambangan.
Gunakan hanya agregasi JSON yang diberikan. Tulis dalam bahasa Indonesia profesional.
Salin setiap nominal IDR dan persentase persis seperti tertulis dalam JSON. Jangan menghitung,
membulatkan ulang, memotong angka desimal, atau mengubah KPI. Periksa ejaan, tanda baca, dan
spasi antar kata sebelum memberi respons. Jangan mengarang nominal, penyebab pembengkakan,
kejadian operasional, atau fakta perusahaan yang tidak tersedia. Nyatakan observasi yang langsung
didukung data sebagai fact. Nyatakan kemungkinan penyebab atau dampak yang perlu diverifikasi
sebagai hypothesis, dengan bahasa bersyarat. Berikan maksimal tiga temuan, tiga risiko, dan tiga
rekomendasi. Isi synthetic_data_disclaimer harus persis: "{disclaimer}"
"""


def _format_idr(value: float | int) -> str:
    return "Rp" + f"{value:,.0f}".replace(",", ".")


def _format_percentage(value: float | None) -> str:
    return "N/A" if value is None else f"{value:.2f}%"


def _display_kpis(kpis: dict[str, Any]) -> dict[str, Any]:
    return {
        "total_budget": _format_idr(kpis["total_budget"]),
        "total_actual_cost": _format_idr(kpis["total_actual_cost"]),
        "variance": _format_idr(kpis["variance"]),
        "variance_pct": _format_percentage(kpis["variance_pct"]),
        "transaction_count": int(kpis["transaction_count"]),
        "over_budget_count": int(kpis["over_budget_count"]),
        "under_budget_count": int(kpis["under_budget_count"]),
        "on_budget_count": int(kpis["on_budget_count"]),
    }


def _display_summary_rows(
    rows: list[dict[str, Any]], label_key: str
) -> list[dict[str, Any]]:
    return [
        {
            label_key: row[label_key],
            "budget": _format_idr(row["budget"]),
            "actual_cost": _format_idr(row["actual_cost"]),
            "variance": _format_idr(row["variance"]),
            "variance_pct": _format_percentage(row["variance_pct"]),
            "transaction_count": int(row["transaction_count"]),
        }
        for row in rows
    ]


def build_gemini_prompt_payload(
    analysis_payload: dict[str, Any],
) -> dict[str, Any]:
    """Build an aggregate-only display payload without mutating KPI source data."""
    metadata = analysis_payload["metadata"]
    return {
        "metadata": {
            "period_start": metadata["period_start"],
            "period_end": metadata["period_end"],
            "currency": metadata["currency"],
            "synthetic_data": metadata["synthetic_data"],
        },
        "overall_kpis": _display_kpis(analysis_payload["overall_kpis"]),
        "department_summary": _display_summary_rows(
            analysis_payload["department_summary"], "department"
        ),
        "category_summary": _display_summary_rows(
            analysis_payload["category_summary"], "category"
        ),
    }


class GeminiExecutiveClient:
    """Generate one structured interpretation from aggregate KPI data."""

    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        from google import genai

        self._client = genai.Client(api_key=api_key or get_gemini_api_key())
        self._model = model or get_gemini_model()

    def generate(self, analysis_payload: dict[str, Any]) -> dict[str, Any]:
        """Call Gemini with aggregate-only JSON and return parsed JSON."""
        prompt_payload = build_gemini_prompt_payload(analysis_payload)
        prompt = (
            f"{SYSTEM_INSTRUCTIONS.format(disclaimer=SYNTHETIC_DISCLAIMER)}\n\n"
            "Analisis agregasi KPI berikut:\n"
            + json.dumps(prompt_payload, ensure_ascii=False, allow_nan=False)
        )
        response = self._client.models.generate_content(
            model=self._model,
            contents=prompt,
            config={
                "response_mime_type": "application/json",
                "response_json_schema": EXECUTIVE_SUMMARY_SCHEMA,
                "temperature": 0.2,
            },
        )
        if not response.text:
            raise ValueError("Gemini returned an empty response")
        parsed = json.loads(response.text)
        if not isinstance(parsed, dict):
            raise ValueError("Gemini response must be a JSON object")
        return parsed
