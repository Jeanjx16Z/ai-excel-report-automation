"""Shared structured-output contract for executive summaries."""

from __future__ import annotations

from typing import Any


MAX_ITEMS = 3
SYNTHETIC_DISCLAIMER = (
    "Laporan ini menggunakan data sintetis untuk demonstrasi dan bukan data asli perusahaan."
)

EXECUTIVE_SUMMARY_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "executive_summary",
        "key_findings",
        "potential_risks",
        "actionable_recommendations",
        "synthetic_data_disclaimer",
    ],
    "properties": {
        "executive_summary": {"type": "string"},
        "key_findings": {
            "type": "array",
            "minItems": 1,
            "maxItems": MAX_ITEMS,
            "items": {"type": "string"},
        },
        "potential_risks": {
            "type": "array",
            "minItems": 1,
            "maxItems": MAX_ITEMS,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["statement", "evidence_level"],
                "properties": {
                    "statement": {"type": "string"},
                    "evidence_level": {
                        "type": "string",
                        "enum": ["fact", "hypothesis"],
                    },
                },
            },
        },
        "actionable_recommendations": {
            "type": "array",
            "minItems": 1,
            "maxItems": MAX_ITEMS,
            "items": {"type": "string"},
        },
        "synthetic_data_disclaimer": {
            "type": "string",
            "enum": [SYNTHETIC_DISCLAIMER],
        },
    },
}
