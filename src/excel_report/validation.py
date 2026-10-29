"""Fail-fast validation for mining operational cost input data."""

from __future__ import annotations

import pandas as pd
from pandas.api.types import is_numeric_dtype

from generate_sample_data import DEPARTMENT_CATEGORIES, REQUIRED_COLUMNS

from .models import DataValidationError


def _row_labels(mask: pd.Series) -> str:
    """Return compact one-based Excel row labels, including the header row."""
    rows = [str(int(index) + 2) for index in mask[mask].index[:10]]
    suffix = ", ..." if int(mask.sum()) > 10 else ""
    return ", ".join(rows) + suffix


def validate_data(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Validate the full schema and return a safe normalized copy."""
    missing_columns = [
        column for column in REQUIRED_COLUMNS if column not in dataframe.columns
    ]
    if missing_columns:
        raise DataValidationError(
            f"Missing required columns: {', '.join(missing_columns)}"
        )

    unexpected_columns = [
        column for column in dataframe.columns if column not in REQUIRED_COLUMNS
    ]
    if unexpected_columns:
        raise DataValidationError(
            f"Unexpected columns: {', '.join(map(str, unexpected_columns))}"
        )

    if dataframe.empty:
        raise DataValidationError("Input dataset must contain at least one transaction")

    validated = dataframe.loc[:, REQUIRED_COLUMNS].copy()
    missing_mask = validated.isna()
    text_columns = ["department", "category"]
    blank_text_mask = validated[text_columns].apply(
        lambda column: column.map(lambda value: isinstance(value, str) and not value.strip())
    )
    missing_mask.loc[:, text_columns] = (
        missing_mask[text_columns] | blank_text_mask
    )
    if missing_mask.any().any():
        problem_columns = [
            column for column in REQUIRED_COLUMNS if missing_mask[column].any()
        ]
        raise DataValidationError(
            f"Missing or blank values found in columns: {', '.join(problem_columns)}"
        )

    parsed_dates = pd.to_datetime(validated["date"], errors="coerce", format="mixed")
    invalid_date_mask = parsed_dates.isna()
    if invalid_date_mask.any():
        raise DataValidationError(
            "Invalid date values at Excel rows: " + _row_labels(invalid_date_mask)
        )

    for column in ("budget", "actual_cost"):
        if not is_numeric_dtype(validated[column]):
            invalid_numeric_mask = pd.to_numeric(
                validated[column], errors="coerce"
            ).isna()
            detail = (
                f" at Excel rows: {_row_labels(invalid_numeric_mask)}"
                if invalid_numeric_mask.any()
                else ""
            )
            raise DataValidationError(f"Column '{column}' must be numeric{detail}")
        negative_mask = validated[column] < 0
        if negative_mask.any():
            raise DataValidationError(
                f"Column '{column}' contains negative values at Excel rows: "
                + _row_labels(negative_mask)
            )

    for column in text_columns:
        non_text_mask = ~validated[column].map(lambda value: isinstance(value, str))
        if non_text_mask.any():
            raise DataValidationError(
                f"Column '{column}' must contain text values at Excel rows: "
                + _row_labels(non_text_mask)
            )

    unexpected_departments = sorted(
        set(validated["department"]) - set(DEPARTMENT_CATEGORIES)
    )
    if unexpected_departments:
        raise DataValidationError(
            "Unknown departments: " + ", ".join(map(str, unexpected_departments))
        )

    invalid_mapping_mask = validated.apply(
        lambda row: row["category"]
        not in DEPARTMENT_CATEGORIES[row["department"]],
        axis=1,
    )
    if invalid_mapping_mask.any():
        raise DataValidationError(
            "Invalid department-category combinations at Excel rows: "
            + _row_labels(invalid_mapping_mask)
        )

    duplicate_mask = validated.duplicated(keep=False)
    if duplicate_mask.any():
        raise DataValidationError(
            "Duplicate transactions found at Excel rows: "
            + _row_labels(duplicate_mask)
        )

    validated["date"] = parsed_dates
    return validated
