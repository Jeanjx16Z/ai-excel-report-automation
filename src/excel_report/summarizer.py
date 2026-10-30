"""Offline and Gemini executive summary services."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Protocol

from .models import ExecutiveSummaryResult, SummaryValidationError
from .summary_contract import MAX_ITEMS, SYNTHETIC_DISCLAIMER


class SummaryClient(Protocol):
    """Minimal interface required from a structured summary provider."""

    def generate(self, analysis_payload: dict[str, Any]) -> dict[str, Any]: ...


def load_analysis_payload(path: Path) -> dict[str, Any]:
    """Load and validate the aggregate-only Milestone 2 JSON output."""
    input_path = Path(path)
    try:
        with input_path.open(encoding="utf-8") as input_file:
            payload = json.load(input_file)
    except (OSError, json.JSONDecodeError) as error:
        raise SummaryValidationError(
            f"Unable to load structured analysis '{input_path}': {error}"
        ) from error
    validate_analysis_payload(payload)
    return payload


def validate_analysis_payload(payload: Any) -> None:
    """Reject payloads that are not aggregate-only analysis outputs."""
    if not isinstance(payload, dict):
        raise SummaryValidationError("Analysis payload must be a JSON object")
    required_sections = {
        "metadata",
        "overall_kpis",
        "department_summary",
        "category_summary",
    }
    missing_sections = required_sections - set(payload)
    unexpected_sections = set(payload) - required_sections
    if missing_sections:
        raise SummaryValidationError(
            "Analysis payload is missing sections: "
            + ", ".join(sorted(missing_sections))
        )
    if unexpected_sections:
        raise SummaryValidationError(
            "Analysis payload has unexpected sections: "
            + ", ".join(sorted(unexpected_sections))
        )

    metadata = payload["metadata"]
    kpis = payload["overall_kpis"]
    if not isinstance(metadata, dict) or not isinstance(kpis, dict):
        raise SummaryValidationError("Metadata and overall_kpis must be objects")
    if metadata.get("synthetic_data") is not True:
        raise SummaryValidationError("Analysis payload must be marked synthetic_data=true")
    required_kpis = {
        "total_budget",
        "total_actual_cost",
        "variance",
        "variance_pct",
        "transaction_count",
        "over_budget_count",
        "under_budget_count",
        "on_budget_count",
    }
    missing_kpis = required_kpis - set(kpis)
    if missing_kpis:
        raise SummaryValidationError(
            "Analysis payload is missing KPIs: " + ", ".join(sorted(missing_kpis))
        )
    for section in ("department_summary", "category_summary"):
        if not isinstance(payload[section], list):
            raise SummaryValidationError(f"{section} must be an array")


def _offline_summary(
    payload: dict[str, Any],
    source: str = "offline",
) -> ExecutiveSummaryResult:
    """Create a deterministic interpretation from aggregate KPI data."""
    kpis = payload["overall_kpis"]
    departments = payload["department_summary"]
    categories = payload["category_summary"]
    variance = kpis["variance"]

    if variance > 0:
        budget_position = "realisasi biaya berada di atas anggaran"
    elif variance < 0:
        budget_position = "realisasi biaya berada di bawah anggaran"
    else:
        budget_position = "realisasi biaya sama dengan anggaran"

    top_department = departments[0]["department"] if departments else "tidak tersedia"
    top_category = categories[0]["category"] if categories else "tidak tersedia"
    executive_summary = (
        f"Berdasarkan KPI deterministik, {budget_position}. "
        f"Agregasi dengan variance terbesar terdapat pada departemen {top_department} "
        f"dan kategori {top_category}. Hasil ini harus dibaca sebagai demonstrasi berbasis "
        "data sintetis, bukan sebagai kondisi perusahaan nyata."
    )
    findings = (
        f"Terdapat {kpis['over_budget_count']} transaksi over-budget, "
        f"{kpis['under_budget_count']} under-budget, dan "
        f"{kpis['on_budget_count']} on-budget.",
        f"Departemen dengan variance agregat terbesar adalah {top_department}.",
        f"Kategori dengan variance agregat terbesar adalah {top_category}.",
    )
    risks = (
        {
            "statement": (
                "Variance positif yang berlanjut dapat meningkatkan tekanan terhadap "
                "anggaran; penyebab operasionalnya perlu diverifikasi dengan data pendukung."
            ),
            "evidence_level": "hypothesis",
        },
        {
            "statement": (
                "Data agregat tidak cukup untuk menyimpulkan penyebab pembengkakan biaya "
                "pada transaksi atau aktivitas tertentu."
            ),
            "evidence_level": "fact",
        },
    )
    recommendations = (
        f"Prioritaskan review variance pada departemen {top_department}.",
        f"Tinjau komponen biaya kategori {top_category} menggunakan bukti transaksi yang sah.",
        "Validasi hipotesis penyebab bersama pemilik proses sebelum mengambil keputusan.",
    )
    return ExecutiveSummaryResult(
        executive_summary=executive_summary,
        key_findings=findings,
        potential_risks=risks,
        actionable_recommendations=recommendations,
        synthetic_data_disclaimer=SYNTHETIC_DISCLAIMER,
        source=source,
    )


def validate_summary_response(
    response: Any,
    source: str = "gemini",
) -> ExecutiveSummaryResult:
    """Validate provider JSON independently of the SDK response schema."""
    if not isinstance(response, dict):
        raise SummaryValidationError("Summary response must be a JSON object")
    required_fields = {
        "executive_summary",
        "key_findings",
        "potential_risks",
        "actionable_recommendations",
        "synthetic_data_disclaimer",
    }
    missing_fields = required_fields - set(response)
    unexpected_fields = set(response) - required_fields
    if missing_fields:
        raise SummaryValidationError(
            "Summary response is missing fields: " + ", ".join(sorted(missing_fields))
        )
    if unexpected_fields:
        raise SummaryValidationError(
            "Summary response has unexpected fields: "
            + ", ".join(sorted(unexpected_fields))
        )

    for field in ("executive_summary", "synthetic_data_disclaimer"):
        if not isinstance(response[field], str) or not response[field].strip():
            raise SummaryValidationError(f"{field} must be a non-empty string")

    def normalize_whitespace(value: str) -> str:
        return re.sub(r"\s+", " ", value).strip()

    validated_lists: dict[str, tuple[str, ...]] = {}
    for field in ("key_findings", "actionable_recommendations"):
        items = response[field]
        if not isinstance(items, list) or not 1 <= len(items) <= MAX_ITEMS:
            raise SummaryValidationError(f"{field} must contain 1 to {MAX_ITEMS} items")
        if any(not isinstance(item, str) or not item.strip() for item in items):
            raise SummaryValidationError(f"{field} must contain non-empty strings")
        validated_lists[field] = tuple(normalize_whitespace(item) for item in items)

    risks = response["potential_risks"]
    if not isinstance(risks, list) or not 1 <= len(risks) <= MAX_ITEMS:
        raise SummaryValidationError(
            f"potential_risks must contain 1 to {MAX_ITEMS} items"
        )
    validated_risks: list[dict[str, str]] = []
    for risk in risks:
        if not isinstance(risk, dict) or set(risk) != {"statement", "evidence_level"}:
            raise SummaryValidationError(
                "Each potential risk requires statement and evidence_level"
            )
        if not isinstance(risk["statement"], str) or not risk["statement"].strip():
            raise SummaryValidationError("Risk statement must be a non-empty string")
        if risk["evidence_level"] not in {"fact", "hypothesis"}:
            raise SummaryValidationError("Risk evidence_level must be fact or hypothesis")
        validated_risks.append(
            {
                "statement": normalize_whitespace(risk["statement"]),
                "evidence_level": risk["evidence_level"],
            }
        )

    if response["synthetic_data_disclaimer"].strip() != SYNTHETIC_DISCLAIMER:
        raise SummaryValidationError(
            "synthetic_data_disclaimer must match the canonical synthetic-data disclaimer"
        )

    return ExecutiveSummaryResult(
        executive_summary=normalize_whitespace(response["executive_summary"]),
        key_findings=validated_lists["key_findings"],
        potential_risks=tuple(validated_risks),
        actionable_recommendations=validated_lists["actionable_recommendations"],
        synthetic_data_disclaimer=normalize_whitespace(
            response["synthetic_data_disclaimer"]
        ),
        source=source,
    )


def generate_executive_summary(
    payload: dict[str, Any],
    mode: str = "offline",
    client: SummaryClient | None = None,
) -> ExecutiveSummaryResult:
    """Generate an offline summary or use Gemini with deterministic fallback."""
    validate_analysis_payload(payload)
    if mode == "offline":
        return _offline_summary(payload)
    if mode != "gemini":
        raise ValueError("mode must be 'offline' or 'gemini'")

    try:
        if client is None:
            from .gemini_client import GeminiExecutiveClient

            client = GeminiExecutiveClient()
    except Exception as error:
        return _fallback_summary(payload, "client_initialization", error)

    try:
        response = client.generate(payload)
    except Exception as error:
        return _fallback_summary(payload, "api_request_or_response_parse", error)

    try:
        return validate_summary_response(response)
    except Exception as error:
        return _fallback_summary(payload, "response_validation", error)


def _fallback_summary(
    payload: dict[str, Any],
    stage: str,
    error: Exception,
) -> ExecutiveSummaryResult:
    """Return offline output with safe, stage-specific diagnostics."""
    fallback = _offline_summary(payload, source="offline_fallback")
    error_detail = type(error).__name__
    if isinstance(error, SummaryValidationError):
        error_detail += f": {error}"
    return ExecutiveSummaryResult(
        executive_summary=fallback.executive_summary,
        key_findings=fallback.key_findings,
        potential_risks=fallback.potential_risks,
        actionable_recommendations=fallback.actionable_recommendations,
        synthetic_data_disclaimer=fallback.synthetic_data_disclaimer,
        source=fallback.source,
        fallback_reason=(
            f"Gemini summary unavailable at stage '{stage}'; "
            f"offline fallback used ({error_detail})."
        ),
    )
