"""Tests for fail-fast input validation."""

from __future__ import annotations

import sys
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
