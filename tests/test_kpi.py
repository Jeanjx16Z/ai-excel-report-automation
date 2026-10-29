"""Tests for deterministic KPI calculations."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

import pandas as pd


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = REPOSITORY_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from excel_report.kpi import calculate_kpis  # noqa: E402


class KpiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.dataframe = pd.DataFrame(
            {
                "date": pd.to_datetime(
                    ["2025-01-01", "2025-01-02", "2025-01-03", "2025-01-04"]
                ),
                "department": [
                    "Mining Operations",
                    "Mining Operations",
                    "HSE",
                    "HSE",
                ],
                "category": [
                    "Diesel Fuel",
                    "Diesel Fuel",
                    "Safety Equipment",
                    "Safety Equipment",
                ],
                "budget": [100.0, 100.0, 200.0, 0.0],
                "actual_cost": [120.0, 80.0, 200.0, 50.0],
            }
        )

    def test_overall_kpis_and_transaction_counts(self) -> None:
        kpis = calculate_kpis(self.dataframe).overall_kpis

        self.assertEqual(400.0, kpis["total_budget"])
        self.assertEqual(450.0, kpis["total_actual_cost"])
        self.assertEqual(50.0, kpis["variance"])
        self.assertEqual(12.5, kpis["variance_pct"])
        self.assertEqual(2, kpis["over_budget_count"])
        self.assertEqual(1, kpis["under_budget_count"])
        self.assertEqual(1, kpis["on_budget_count"])

    def test_zero_total_budget_returns_null_percentage(self) -> None:
        zero_budget_dataframe = self.dataframe.iloc[[3]].copy()

        result = calculate_kpis(zero_budget_dataframe)

        self.assertIsNone(result.overall_kpis["variance_pct"])
        self.assertTrue(pd.isna(result.department_summary.loc[0, "variance_pct"]))

    def test_aggregations_are_sorted_and_match_overall_totals(self) -> None:
        result = calculate_kpis(self.dataframe)

        self.assertEqual("HSE", result.department_summary.loc[0, "department"])
        for summary in (result.department_summary, result.category_summary):
            self.assertEqual(
                result.overall_kpis["total_budget"], float(summary["budget"].sum())
            )
            self.assertEqual(
                result.overall_kpis["total_actual_cost"],
                float(summary["actual_cost"].sum()),
            )
            self.assertEqual(
                result.overall_kpis["transaction_count"],
                int(summary["transaction_count"].sum()),
            )
