"""Serialize existing KPI values for display; never recompute financial measures."""

from decimal import Decimal
from .errors import ApiError


def financial(value, percentage=False):
    if value is None:
        return {"value": None, "display_value": "N/A (budget nol)"}
    decimal = Decimal(str(value))
    if not decimal.is_finite():
        raise ApiError("INVALID_FILE_SCHEMA")
    return {
        "value": format(decimal, "f"),
        "display_value": f"{value:.2f}%" if percentage else "Rp" + f"{value:,.0f}".replace(",", "."),
    }


def serialize_snapshot(payload):
    overall = payload["overall_kpis"]
    return {
        "schema_version": 1, "metadata": dict(payload["metadata"]),
        "kpis": {"schema_version": 1, "currency": "IDR", **{
            key: int(value) if key.endswith("count") else financial(value, key == "variance_pct")
            for key, value in overall.items()
        }},
        **{section: [{
            key: int(value) if key == "transaction_count" else financial(value, key == "variance_pct")
            if key in {"budget", "actual_cost", "variance", "variance_pct"} else value
            for key, value in row.items()
        } for row in payload[section]] for section in ("department_summary", "category_summary")},
    }
