# BankLens

BankLens is a Flask app that analyzes a bank-statement CSV:
- Parses transactions from common bank export formats
- Uses the OpenAI API to categorize transaction descriptions
- Displays a spending dashboard with totals, table, and category breakdown

## Setup

```bash
python3 -m pip install -r requirements.txt
```

## Run

```bash
export OPENAI_API_KEY="your-key"
export FLASK_SECRET_KEY="your-random-secret"
export FLASK_DEBUG="true"  # optional for local dev
python3 app.py
```

Optional:
- `OPENAI_MODEL` (defaults to `gpt-3.5-turbo`)

## Tests

```bash
python3 -m pytest
```

## CSV Expectations

BankLens looks for:
- Date column similar to: `Date`, `Transaction Date`, `Posted Date`
- Description column similar to: `Description`, `Memo`, `Details`
- Amount data from either:
  - a single amount column (`Amount`, `Transaction Amount`), or
  - debit/credit columns (`Debit`/`Credit`, `Withdrawal`/`Deposit`)

## Notes on Data Handling

- Uploaded CSV files are stored temporarily and deleted after processing.
- Parsed/categorized results are stored server-side in local JSON files.
- The browser session stores only a short result ID, not raw transaction data.
