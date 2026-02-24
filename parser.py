"""Helpers for parsing bank statement CSV files.

This module handles:
1.  Flexible column matching (case-insensitive, partial matching) to support various bank formats.
2.  Cleaning and normalizing amount strings (handling currency symbols, commas, parentheses).
3.  Unifying different schema types (Single Amount vs. Debit/Credit columns) into a standard signed amount.
    - Negative Amount = Expense (Money Out)
    - Positive Amount = Income (Money In)
"""

import re
from typing import Dict, List

import pandas as pd
from pandas.errors import EmptyDataError, ParserError


# Common column headers found in bank exports.
DATE_ALIASES = [
    "date",
    "transaction date",
    "posted date",
    "posting date",
]

DESCRIPTION_ALIASES = [
    "description",
    "memo",
    "details",
    "transaction",
    "transaction description",
]

# For single-column amounts (signed values).
AMOUNT_ALIASES = [
    "amount",
    "transaction amount",
]

# For split-column formats (absolute values).
DEBIT_ALIASES = [
    "debit",
    "withdrawal",
    "money out",
]

CREDIT_ALIASES = [
    "credit",
    "deposit",
    "money in",
]


def _normalize_column_name(name: str) -> str:
    """Normalize column names for flexible matching (lowercase, single spaces)."""
    return re.sub(r"\s+", " ", str(name).strip().lower())


def _find_column(columns: List[str], aliases: List[str]) -> str | None:
    """Find the first matching source column for a target field.

    Strategies:
    1. Exact match (normalized).
    2. Partial match (alias is a substring of the column name).
    """
    normalized = {_normalize_column_name(col): col for col in columns}

    # Strategy 1: Exact match against known aliases
    for alias in aliases:
        if alias in normalized:
            return normalized[alias]

    # Strategy 2: Substring match (e.g., "Chase Description" matches "description")
    for alias in aliases:
        for norm_col, original_col in normalized.items():
            if alias in norm_col:
                return original_col

    return None


def _has_value(value) -> bool:
    """Return True when a CSV cell is non-empty."""
    return not pd.isna(value) and str(value).strip() != ""


def _parse_amount(value, row_number: int | None = None) -> float:
    """Convert mixed amount strings like '$1,234.56' or '(50.00)' into numeric floats.

    Handles:
    - Currency symbols ($) and commas.
    - Parentheses for negative values (accounting format).
    - Standard negative signs.
    """
    if pd.isna(value):
        return 0.0

    text = str(value).strip()
    if not text:
        return 0.0

    # Check for accounting negative format: (123.45) -> -123.45
    negative = text.startswith("(") and text.endswith(")")

    # Remove everything except digits, dots, and minus signs.
    cleaned = re.sub(r"[^0-9.\-]", "", text)

    if cleaned in {"", "-", ".", "-."}:
        return 0.0

    try:
        amount = float(cleaned)
    except ValueError as exc:
        location = f" on row {row_number}" if row_number else ""
        raise ValueError(f"Invalid amount value '{text}'{location}.") from exc

    # Apply negative sign if it was parenthesized
    if negative and amount > 0:
        amount *= -1

    return amount


def parse_bank_csv(file_path: str) -> List[Dict[str, object]]:
    """Read a CSV statement and return normalized transactions.

    Returns a list of dicts with:
    - date: str
    - description: str
    - amount: float (Negative = Expense, Positive = Income)
    """
    try:
        # standard pandas read
        df = pd.read_csv(file_path)
    except (EmptyDataError, ParserError, UnicodeDecodeError) as exc:
        raise ValueError(
            "Could not read the CSV file. Please upload a valid comma-separated text file."
        ) from exc

    if df.empty:
        return []

    # Identify columns dynamically
    date_col = _find_column(df.columns.tolist(), DATE_ALIASES)
    description_col = _find_column(df.columns.tolist(), DESCRIPTION_ALIASES)
    amount_col = _find_column(df.columns.tolist(), AMOUNT_ALIASES)
    debit_col = _find_column(df.columns.tolist(), DEBIT_ALIASES)
    credit_col = _find_column(df.columns.tolist(), CREDIT_ALIASES)

    # Validate required columns
    missing = []
    if not date_col:
        missing.append("date")
    if not description_col:
        missing.append("description")

    # We need either a single Amount column OR at least one of Debit/Credit
    if not amount_col and not debit_col and not credit_col:
        missing.append("amount")

    if missing:
        raise ValueError(
            "Missing required column(s): "
            + ", ".join(missing)
            + ". Expected fields similar to Date, Description, and Amount (or Debit/Credit)."
        )

    transactions: List[Dict[str, object]] = []

    # Iterate rows (start=2 assuming header is row 1, 1-based indexing for user errors)
    for row_number, (_, row) in enumerate(df.iterrows(), start=2):
        date_value = "" if pd.isna(row[date_col]) else str(row[date_col]).strip()
        description_value = "" if pd.isna(row[description_col]) else str(row[description_col]).strip()

        # Skip completely empty rows
        if not date_value and not description_value:
            continue

        # Determine Amount
        # Priority: explicit Amount column > calculated from Debit/Credit
        if amount_col and _has_value(row[amount_col]):
            amount_value = _parse_amount(row[amount_col], row_number=row_number)
        else:
            debit_value = _parse_amount(row[debit_col], row_number=row_number) if debit_col else 0.0
            credit_value = _parse_amount(row[credit_col], row_number=row_number) if credit_col else 0.0

            # Normalize to signed amount:
            # Income (Credit) - Expense (Debit)
            # Example: Credit=0, Debit=50 -> Amount = -50 (Expense)
            # Example: Credit=100, Debit=0 -> Amount = +100 (Income)
            amount_value = credit_value - debit_value

        transactions.append(
            {
                "date": date_value,
                "description": description_value,
                "amount": amount_value,
            }
        )

    return transactions
