"""Deterministic Pandas KPI calculations."""

from __future__ import annotations

from typing import Any

import pandas as pd

from .models import AnalysisResult


def _variance_percentage(actual_cost: float, budget: float) -> float | None:
    """Calculate variance percentage, returning null for a zero budget."""
    if budget == 0:
        return None
    return (actual_cost - budget) / budget * 100


def _build_summary(dataframe: pd.DataFrame, group_column: str) -> pd.DataFrame:
    """Aggregate budget and actual cost for a reporting dimension."""
    summary = (
        dataframe.groupby(group_column, as_index=False, sort=False)
        .agg(
            budget=("budget", "sum"),
            actual_cost=("actual_cost", "sum"),
            transaction_count=("date", "size"),
        )
        .astype({"budget": "float64", "actual_cost": "float64"})
    )
    summary["variance"] = summary["actual_cost"] - summary["budget"]
    summary["variance_pct"] = summary.apply(
        lambda row: _variance_percentage(row["actual_cost"], row["budget"]),
        axis=1,
    )
    ordered_columns = [
        group_column,
        "budget",
        "actual_cost",
        "variance",
        "variance_pct",
        "transaction_count",
    ]
    return summary.loc[:, ordered_columns].sort_values(
        by=["variance", group_column],
        ascending=[False, True],
        ignore_index=True,
    )


def calculate_kpis(dataframe: pd.DataFrame) -> AnalysisResult:
    """Calculate overall and grouped mining operational cost KPIs."""
    total_budget = float(dataframe["budget"].sum())
    total_actual_cost = float(dataframe["actual_cost"].sum())
    total_variance = total_actual_cost - total_budget

    transaction_variance = dataframe["actual_cost"] - dataframe["budget"]
    overall_kpis: dict[str, Any] = {
        "total_budget": total_budget,
        "total_actual_cost": total_actual_cost,
        "variance": total_variance,
        "variance_pct": _variance_percentage(total_actual_cost, total_budget),
        "transaction_count": int(len(dataframe)),
        "over_budget_count": int((transaction_variance > 0).sum()),
        "under_budget_count": int((transaction_variance < 0).sum()),
        "on_budget_count": int((transaction_variance == 0).sum()),
    }
    metadata = {
        "period_start": dataframe["date"].min().date().isoformat(),
        "period_end": dataframe["date"].max().date().isoformat(),
        "currency": "IDR",
        "synthetic_data": True,
    }

    return AnalysisResult(
        metadata=metadata,
        overall_kpis=overall_kpis,
        department_summary=_build_summary(dataframe, "department"),
        category_summary=_build_summary(dataframe, "category"),
    )
