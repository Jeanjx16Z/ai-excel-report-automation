"""Generate reproducible synthetic mining operational expense data."""

from __future__ import annotations

import random
from pathlib import Path

import pandas as pd
from pandas.api.types import is_datetime64_any_dtype, is_numeric_dtype


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_PATH = REPOSITORY_ROOT / "data" / "raw" / "accounting_sample.xlsx"
DEFAULT_ROW_COUNT = 120
DEFAULT_RANDOM_SEED = 2026
REQUIRED_COLUMNS = ["date", "department", "category", "budget", "actual_cost"]
DEPARTMENT_CATEGORIES = {
    "Mining Operations": [
        "Diesel Fuel",
        "Drilling Consumables",
        "Blasting Materials",
        "Equipment Rental",
    ],
    "Heavy Equipment": [
        "Equipment Maintenance",
        "Spare Parts",
        "Diesel Fuel",
        "Equipment Rental",
    ],
    "Logistics": [
        "Hauling Transportation",
        "Diesel Fuel",
        "Tire Replacement",
        "Equipment Rental",
    ],
    "HSE": [
        "Safety Equipment",
        "Environmental Monitoring",
        "Emergency Response",
        "Safety Training",
    ],
    "Site Infrastructure": [
        "Road Maintenance",
        "Site Utilities",
        "Camp Maintenance",
        "Equipment Rental",
    ],
}
VARIANCE_RATES = [-0.25, -0.18, -0.12, -0.07, 0.05, 0.10, 0.16, 0.25]


def create_sample_dataframe(
    row_count: int = DEFAULT_ROW_COUNT,
    random_seed: int = DEFAULT_RANDOM_SEED,
) -> pd.DataFrame:
    """Create synthetic accounting rows with deterministic random values."""
    if row_count < 120:
        raise ValueError("row_count must be at least 120")

    random_generator = random.Random(random_seed)
    departments = list(DEPARTMENT_CATEGORIES)
    start_date = pd.Timestamp("2025-01-01")
    rows: list[dict[str, object]] = []

    for index in range(row_count):
        department = departments[index % len(departments)]
        department_categories = DEPARTMENT_CATEGORIES[department]
        category_cycle = index // len(departments)
        category = department_categories[category_cycle % len(department_categories)]
        budget = random_generator.randrange(25_000_000, 2_500_000_001, 5_000_000)
        variance_rate = VARIANCE_RATES[index % len(VARIANCE_RATES)]
        actual_cost = round(budget * (1 + variance_rate), 2)
        transaction_date = start_date + pd.Timedelta(
            days=random_generator.randint(0, 364)
        )

        rows.append(
            {
                "date": transaction_date,
                "department": department,
                "category": category,
                "budget": float(budget),
                "actual_cost": actual_cost,
            }
        )

    return pd.DataFrame(rows, columns=REQUIRED_COLUMNS)


def validate_sample_dataframe(dataframe: pd.DataFrame) -> None:
    """Raise ValueError when generated data violates the dataset contract."""
    errors: list[str] = []

    if list(dataframe.columns) != REQUIRED_COLUMNS:
        errors.append(f"columns must be exactly {REQUIRED_COLUMNS}")
    if len(dataframe) < 120:
        errors.append("dataset must contain at least 120 rows")
    if dataframe.isna().any().any():
        errors.append("dataset must not contain missing values")

    if "date" in dataframe and not is_datetime64_any_dtype(dataframe["date"]):
        errors.append("date must use a datetime dtype")

    for column in ("budget", "actual_cost"):
        if column in dataframe:
            if not is_numeric_dtype(dataframe[column]):
                errors.append(f"{column} must be numeric")
            elif (dataframe[column] < 0).any():
                errors.append(f"{column} must be non-negative")

    if "department" in dataframe:
        unexpected_departments = set(dataframe["department"]) - set(
            DEPARTMENT_CATEGORIES
        )
        missing_departments = set(DEPARTMENT_CATEGORIES) - set(dataframe["department"])
        if unexpected_departments:
            errors.append(
                f"unexpected departments: {sorted(unexpected_departments)}"
            )
        if missing_departments:
            errors.append(f"missing departments: {sorted(missing_departments)}")

    if {"department", "category"}.issubset(dataframe.columns):
        invalid_category_rows = dataframe.apply(
            lambda row: row["category"]
            not in DEPARTMENT_CATEGORIES.get(row["department"], []),
            axis=1,
        )
        if invalid_category_rows.any():
            errors.append("category must match its mining department")

    if {"budget", "actual_cost"}.issubset(dataframe.columns):
        if not (dataframe["actual_cost"] > dataframe["budget"]).any():
            errors.append("dataset must contain over-budget rows")
        if not (dataframe["actual_cost"] < dataframe["budget"]).any():
            errors.append("dataset must contain under-budget rows")

    if errors:
        raise ValueError("Invalid synthetic dataset: " + "; ".join(errors))


def generate_sample_excel(
    output_path: Path = DEFAULT_OUTPUT_PATH,
    row_count: int = DEFAULT_ROW_COUNT,
    random_seed: int = DEFAULT_RANDOM_SEED,
) -> pd.DataFrame:
    """Generate, validate, write, and read back the synthetic Excel dataset."""
    dataframe = create_sample_dataframe(row_count, random_seed)
    validate_sample_dataframe(dataframe)

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    dataframe.to_excel(output_path, index=False, engine="openpyxl")

    reloaded_dataframe = pd.read_excel(output_path, engine="openpyxl")
    validate_sample_dataframe(reloaded_dataframe)
    return reloaded_dataframe


def main() -> None:
    """Generate the default demo workbook and print a non-sensitive summary."""
    dataframe = generate_sample_excel()
    over_budget_count = int((dataframe["actual_cost"] > dataframe["budget"]).sum())
    under_budget_count = int((dataframe["actual_cost"] < dataframe["budget"]).sum())

    print(f"Created: {DEFAULT_OUTPUT_PATH}")
    print(f"Rows: {len(dataframe)}")
    print(f"Columns: {', '.join(dataframe.columns)}")
    print(f"Over-budget rows: {over_budget_count}")
    print(f"Under-budget rows: {under_budget_count}")


if __name__ == "__main__":
    main()
