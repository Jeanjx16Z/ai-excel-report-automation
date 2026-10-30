"""Tests for fail-fast input validation."""

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

from excel_report.models import DataValidationError, InputFileError  # noqa: E402
from excel_report.excel_io import read_excel  # noqa: E402
from excel_report.validation import validate_data  # noqa: E402


def valid_dataframe() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": pd.to_datetime(["2025-01-01", "2025-01-02"]),
            "department": ["Mining Operations", "HSE"],
            "category": ["Diesel Fuel", "Safety Equipment"],
            "budget": [100.0, 200.0],
            "actual_cost": [110.0, 180.0],
        }
    )


class ValidationTests(unittest.TestCase):
    def test_missing_file_is_rejected(self) -> None:
        with self.assertRaisesRegex(InputFileError, "not found"):
            read_excel(Path("missing-input.xlsx"))

    def test_non_xlsx_extension_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            input_path = Path(temporary_directory) / "input.csv"
            input_path.write_text("not,xlsx", encoding="utf-8")

            with self.assertRaisesRegex(InputFileError, "must use .xlsx"):
                read_excel(input_path)

    def test_corrupt_workbook_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            input_path = Path(temporary_directory) / "corrupt.xlsx"
            input_path.write_bytes(b"not an Excel workbook")

            with self.assertRaisesRegex(InputFileError, "Unable to read Excel"):
                read_excel(input_path)

    def test_missing_column_is_rejected(self) -> None:
        dataframe = valid_dataframe().drop(columns="category")
        with self.assertRaisesRegex(DataValidationError, "Missing required columns"):
            validate_data(dataframe)

    def test_missing_value_is_rejected(self) -> None:
        dataframe = valid_dataframe()
        dataframe.loc[0, "actual_cost"] = None
        with self.assertRaisesRegex(DataValidationError, "Missing or blank"):
            validate_data(dataframe)

    def test_invalid_date_is_rejected(self) -> None:
        dataframe = valid_dataframe()
        dataframe["date"] = ["not-a-date", "2025-01-02"]
        with self.assertRaisesRegex(DataValidationError, "Invalid date"):
            validate_data(dataframe)

    def test_non_numeric_value_is_rejected(self) -> None:
        dataframe = valid_dataframe()
        dataframe["budget"] = ["invalid", "200"]
        with self.assertRaisesRegex(DataValidationError, "must be numeric"):
            validate_data(dataframe)

    def test_non_numeric_actual_cost_is_rejected(self) -> None:
        dataframe = valid_dataframe()
        dataframe["actual_cost"] = ["invalid", "180"]
        with self.assertRaisesRegex(DataValidationError, "actual_cost.*numeric"):
            validate_data(dataframe)

    def test_negative_value_is_rejected(self) -> None:
        dataframe = valid_dataframe()
        dataframe.loc[0, "budget"] = -1
        with self.assertRaisesRegex(DataValidationError, "negative values"):
            validate_data(dataframe)

    def test_unknown_department_is_rejected(self) -> None:
        dataframe = valid_dataframe()
        dataframe.loc[0, "department"] = "Unknown Department"
        with self.assertRaisesRegex(DataValidationError, "Unknown departments"):
            validate_data(dataframe)

    def test_invalid_department_category_mapping_is_rejected(self) -> None:
        dataframe = valid_dataframe()
        dataframe.loc[0, "category"] = "Safety Equipment"
        with self.assertRaisesRegex(DataValidationError, "Invalid department-category"):
            validate_data(dataframe)

    def test_duplicate_transaction_is_rejected(self) -> None:
        dataframe = pd.concat([valid_dataframe().iloc[[0]]] * 2, ignore_index=True)

        with self.assertRaisesRegex(DataValidationError, "Duplicate transactions"):
            validate_data(dataframe)

    def test_dates_and_text_are_normalized_without_mutating_input(self) -> None:
        dataframe = valid_dataframe()
        dataframe["date"] = ["2025-01-01", "2025-01-02"]
        dataframe.loc[0, "department"] = " Mining Operations "
        dataframe.loc[0, "category"] = " Diesel Fuel "
        original = dataframe.copy(deep=True)

        validated = validate_data(dataframe)

        self.assertEqual("Mining Operations", validated.loc[0, "department"])
        self.assertEqual("Diesel Fuel", validated.loc[0, "category"])
        self.assertTrue(pd.api.types.is_datetime64_any_dtype(validated["date"]))
        pd.testing.assert_frame_equal(original, dataframe)
