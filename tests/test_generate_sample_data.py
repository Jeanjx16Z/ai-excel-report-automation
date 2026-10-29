"""Tests for the synthetic accounting dataset generator."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = REPOSITORY_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from generate_sample_data import (  # noqa: E402
    DEPARTMENT_CATEGORIES,
    REQUIRED_COLUMNS,
    create_sample_dataframe,
    generate_sample_excel,
    validate_sample_dataframe,
)


class SampleDataGeneratorTests(unittest.TestCase):
    def test_dataframe_matches_dataset_contract(self) -> None:
        dataframe = create_sample_dataframe()

        validate_sample_dataframe(dataframe)
        self.assertEqual(120, len(dataframe))
        self.assertEqual(REQUIRED_COLUMNS, list(dataframe.columns))
        self.assertEqual(set(DEPARTMENT_CATEGORIES), set(dataframe["department"]))
        expected_categories = {
            category
            for categories in DEPARTMENT_CATEGORIES.values()
            for category in categories
        }
        self.assertEqual(expected_categories, set(dataframe["category"]))
        for department, categories in DEPARTMENT_CATEGORIES.items():
            department_rows = dataframe[dataframe["department"] == department]
            self.assertTrue(department_rows["category"].isin(categories).all())
        self.assertTrue((dataframe[["budget", "actual_cost"]] >= 0).all().all())
        self.assertTrue((dataframe["actual_cost"] > dataframe["budget"]).any())
        self.assertTrue((dataframe["actual_cost"] < dataframe["budget"]).any())

    def test_budget_has_realistic_synthetic_variation(self) -> None:
        dataframe = create_sample_dataframe()

        self.assertGreaterEqual(dataframe["budget"].nunique(), 20)
        self.assertGreater(dataframe["budget"].max(), dataframe["budget"].min())
        self.assertGreaterEqual(dataframe["budget"].min(), 25_000_000)
        self.assertLessEqual(dataframe["budget"].max(), 2_500_000_000)

    def test_fixed_seed_is_reproducible(self) -> None:
        first_dataframe = create_sample_dataframe()
        second_dataframe = create_sample_dataframe()

        pd.testing.assert_frame_equal(first_dataframe, second_dataframe)

    def test_excel_is_written_and_can_be_read_back(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            output_path = Path(temporary_directory) / "accounting_sample.xlsx"

            generated_dataframe = generate_sample_excel(output_path)
            reloaded_dataframe = pd.read_excel(output_path, engine="openpyxl")

            self.assertTrue(output_path.is_file())
            self.assertEqual(REQUIRED_COLUMNS, list(reloaded_dataframe.columns))
            self.assertEqual(len(generated_dataframe), len(reloaded_dataframe))
            validate_sample_dataframe(reloaded_dataframe)

    def test_row_count_below_minimum_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "at least 120"):
            create_sample_dataframe(row_count=119)


if __name__ == "__main__":
    unittest.main()
