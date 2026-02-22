"""Helpers for parsing bank statement CSV files."""

import re
from typing import Dict, List

import pandas as pd
from pandas.errors import EmptyDataError, ParserError


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

AMOUNT_ALIASES = [
    "amount",
    "transaction amount",
]

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
    """Normalize column names for flexible matching."""
    return re.sub(r"\s+", " ", str(name).strip().lower())


def _find_column(columns: List[str], aliases: List[str]) -> str | None:
    """Find the first matching source column for a target field."""
    normalized = {_normalize_column_name(col): col for col in columns}
    for alias in aliases:
        if alias in normalized:
            return normalized[alias]

    for alias in aliases:
        for norm_col, original_col in normalized.items():
            if alias in norm_col:
                return original_col

    return None


def _has_value(value) -> bool:
    """Return True when a CSV cell is non-empty."""
    return not pd.isna(value) and str(value).strip() != ""


def _parse_amount(value, row_number: int | None = None) -> float:
    """Convert mixed amount strings like '$1,234.56' into numeric floats."""
    if pd.isna(value):
        return 0.0

    text = str(value).strip()
    if not text:
        return 0.0

    negative = text.startswith("(") and text.endswith(")")
    cleaned = re.sub(r"[^0-9.\-]", "", text)

    if cleaned in {"", "-", ".", "-."}:
        return 0.0

    try:
        amount = float(cleaned)
    except ValueError as exc:
        location = f" on row {row_number}" if row_number else ""
        raise ValueError(f"Invalid amount value '{text}'{location}.") from exc

    if negative and amount > 0:
        amount *= -1

    return amount


def parse_bank_csv(file_path: str) -> List[Dict[str, object]]:
    """Read a CSV statement and return normalized transactions."""
    try:
        df = pd.read_csv(file_path)
    except (EmptyDataError, ParserError, UnicodeDecodeError) as exc:
        raise ValueError(
            "Could not read the CSV file. Please upload a valid comma-separated text file."
        ) from exc

    if df.empty:
        return []

    date_col = _find_column(df.columns.tolist(), DATE_ALIASES)
    description_col = _find_column(df.columns.tolist(), DESCRIPTION_ALIASES)
    amount_col = _find_column(df.columns.tolist(), AMOUNT_ALIASES)
    debit_col = _find_column(df.columns.tolist(), DEBIT_ALIASES)
    credit_col = _find_column(df.columns.tolist(), CREDIT_ALIASES)

    missing = []
    if not date_col:
        missing.append("date")
    if not description_col:
        missing.append("description")
    if not amount_col and not debit_col and not credit_col:
        missing.append("amount")

    if missing:
        raise ValueError(
            "Missing required column(s): "
            + ", ".join(missing)
            + ". Expected fields similar to Date, Description, and Amount (or Debit/Credit)."
        )

    transactions: List[Dict[str, object]] = []
    for row_number, (_, row) in enumerate(df.iterrows(), start=2):
        date_value = "" if pd.isna(row[date_col]) else str(row[date_col]).strip()
        description_value = "" if pd.isna(row[description_col]) else str(row[description_col]).strip()

        if not date_value and not description_value:
            continue

        if amount_col and _has_value(row[amount_col]):
            amount_value = _parse_amount(row[amount_col], row_number=row_number)
        else:
            debit_value = _parse_amount(row[debit_col], row_number=row_number) if debit_col else 0.0
            credit_value = _parse_amount(row[credit_col], row_number=row_number) if credit_col else 0.0
            # Normalize to signed amount: negative = expense, positive = income.
            amount_value = credit_value - debit_value

        transactions.append(
            {
                "date": date_value,
                "description": description_value,
                "amount": amount_value,
            }
        )

    return transactions
