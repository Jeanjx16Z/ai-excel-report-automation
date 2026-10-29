"""Integration tests for structured pipeline outputs."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = REPOSITORY_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from excel_report.pipeline import run_pipeline  # noqa: E402


class PipelineTests(unittest.TestCase):
    def test_pipeline_exports_valid_aggregate_only_outputs(self) -> None:
        dataframe = pd.DataFrame(
            {
                "date": pd.to_datetime(["2025-01-01", "2025-02-01"]),
                "department": ["Mining Operations", "HSE"],
                "category": ["Diesel Fuel", "Safety Equipment"],
                "budget": [100.0, 200.0],
                "actual_cost": [110.0, 180.0],
            }
        )

        with tempfile.TemporaryDirectory() as temporary_directory:
            temporary_path = Path(temporary_directory)
            input_path = temporary_path / "input.xlsx"
            output_dir = temporary_path / "processed"
            dataframe.to_excel(input_path, index=False, engine="openpyxl")

            result = run_pipeline(input_path, output_dir)

            self.assertTrue(result.json_path.is_file())
            self.assertTrue(result.department_csv_path.is_file())
            self.assertTrue(result.category_csv_path.is_file())
            with result.json_path.open(encoding="utf-8") as input_file:
                payload = json.load(input_file)
            self.assertEqual("IDR", payload["metadata"]["currency"])
            self.assertTrue(payload["metadata"]["synthetic_data"])
            self.assertEqual(2, payload["overall_kpis"]["transaction_count"])
            self.assertNotIn("transactions", payload)


if __name__ == "__main__":
    unittest.main()
