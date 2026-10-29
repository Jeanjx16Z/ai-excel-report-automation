"""Excel input operations."""

from __future__ import annotations

from pathlib import Path
from zipfile import BadZipFile

import pandas as pd

from .models import InputFileError


def read_excel(path: Path) -> pd.DataFrame:
    """Read an .xlsx workbook or raise an actionable domain error."""
    input_path = Path(path)
    if not input_path.exists():
        raise InputFileError(f"Input Excel file not found: {input_path}")
    if not input_path.is_file():
        raise InputFileError(f"Input path is not a file: {input_path}")
    if input_path.suffix.lower() != ".xlsx":
        raise InputFileError(f"Input file must use .xlsx format: {input_path}")

    try:
        return pd.read_excel(input_path, engine="openpyxl")
    except (OSError, ValueError, ImportError, BadZipFile) as error:
        raise InputFileError(
            f"Unable to read Excel file '{input_path}': {error}"
        ) from error
