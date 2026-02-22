import pytest

from parser import parse_bank_csv


def test_parse_amount_column(tmp_path):
    csv_path = tmp_path / "statement.csv"
    csv_path.write_text(
        "Date,Description,Amount\n"
        "2026-01-01,Coffee,-4.50\n"
        "2026-01-02,Salary,2000.00\n",
        encoding="utf-8",
    )

    transactions = parse_bank_csv(str(csv_path))

    assert len(transactions) == 2
    assert transactions[0]["amount"] == -4.5
    assert transactions[1]["amount"] == 2000.0


def test_parse_debit_credit_columns(tmp_path):
    csv_path = tmp_path / "statement.csv"
    csv_path.write_text(
        "Posted Date,Transaction Description,Debit,Credit\n"
        "2026-01-01,Coffee,4.50,\n"
        "2026-01-02,Refund,,8.25\n",
        encoding="utf-8",
    )

    transactions = parse_bank_csv(str(csv_path))

    assert len(transactions) == 2
    assert transactions[0]["amount"] == -4.5
    assert transactions[1]["amount"] == 8.25


def test_parse_missing_required_columns(tmp_path):
    csv_path = tmp_path / "statement.csv"
    csv_path.write_text("Date,Memo\n2026-01-01,Coffee\n", encoding="utf-8")

    with pytest.raises(ValueError, match="Missing required column"):
        parse_bank_csv(str(csv_path))


def test_parse_invalid_amount_reports_row_number(tmp_path):
    csv_path = tmp_path / "statement.csv"
    csv_path.write_text(
        "Date,Description,Amount\n"
        "2026-01-01,Coffee,12.34.56\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="row 2"):
        parse_bank_csv(str(csv_path))


def test_parse_invalid_csv_format(tmp_path):
    csv_path = tmp_path / "statement.csv"
    csv_path.write_text(
        "Date,Description,Amount\n"
        "\"2026-01-01,Coffee,-4.50\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Could not read the CSV file"):
        parse_bank_csv(str(csv_path))
