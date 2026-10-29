"""Isolated google-genai adapter for structured executive summaries."""

from __future__ import annotations

import json
from typing import Any

from .config import get_gemini_api_key, get_gemini_model
from .summary_contract import EXECUTIVE_SUMMARY_SCHEMA, SYNTHETIC_DISCLAIMER


SYSTEM_INSTRUCTIONS = """Anda adalah analis biaya operasional pertambangan.
Gunakan hanya agregasi JSON yang diberikan. Tulis dalam bahasa Indonesia profesional.
Jangan menghitung ulang atau mengubah KPI. Jangan mengarang nominal, penyebab pembengkakan,
kejadian operasional, atau fakta perusahaan yang tidak tersedia. Nyatakan observasi yang langsung
didukung data sebagai fact. Nyatakan kemungkinan penyebab atau dampak yang perlu diverifikasi
sebagai hypothesis, dengan bahasa bersyarat. Berikan maksimal tiga temuan, tiga risiko, dan tiga
rekomendasi. Isi synthetic_data_disclaimer harus persis: "{disclaimer}"
"""


class GeminiExecutiveClient:
    """Generate one structured interpretation from aggregate KPI data."""

    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        from google import genai

        self._client = genai.Client(api_key=api_key or get_gemini_api_key())
        self._model = model or get_gemini_model()

    def generate(self, analysis_payload: dict[str, Any]) -> dict[str, Any]:
        """Call Gemini with aggregate-only JSON and return parsed JSON."""
        prompt = (
            f"{SYSTEM_INSTRUCTIONS.format(disclaimer=SYNTHETIC_DISCLAIMER)}\n\n"
            "Analisis agregasi KPI berikut:\n"
            + json.dumps(analysis_payload, ensure_ascii=False, allow_nan=False)
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
