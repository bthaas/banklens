"""Flask entrypoint for BankLens.

This module handles:
1.  **Routes**: Serving the upload page and the results dashboard.
2.  **File Lifecycle**: Securely saving uploaded CSVs, processing them, and cleaning up.
3.  **Session Management**: Storing a short result ID in the client-side session cookie,
    while keeping the actual sensitive transaction data in server-side local storage (JSON).
    This prevents cookie overflow and improves security.
"""

import json
import os
from pathlib import Path
from uuid import uuid4

from flask import Flask, redirect, render_template, request, session, url_for
from werkzeug.utils import secure_filename

from categorizer import categorize_transactions
from parser import parse_bank_csv


app = Flask(__name__)
# Session is used only to store a short result ID, never raw transactions.
# In production, use a persistent secret key.
app.secret_key = os.getenv("FLASK_SECRET_KEY", os.urandom(32).hex())

APP_ROOT = Path(__file__).resolve().parent
UPLOAD_FOLDER = APP_ROOT / "uploads"
RESULTS_FOLDER = APP_ROOT / "processed_results"
UPLOAD_FOLDER.mkdir(exist_ok=True)
RESULTS_FOLDER.mkdir(exist_ok=True)

ALLOWED_EXTENSIONS = {"csv"}


def allowed_file(filename: str) -> bool:
    """Validate that the uploaded file extension is .csv."""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def _result_file_path(result_id: str) -> Path:
    """Return the on-disk result path for a validated result id."""
    return RESULTS_FOLDER / f"{result_id}.json"


def _store_transactions(transactions) -> str:
    """Persist categorized transactions server-side and return a lookup id.

    Why JSON files?
    - Simple and fast for a demo/MVP.
    - No database setup required.
    - Easy to clean up (just delete the file).
    """
    result_id = uuid4().hex
    _result_file_path(result_id).write_text(json.dumps(transactions), encoding="utf-8")
    return result_id


def _load_transactions(result_id: str | None):
    """Load categorized transactions from server storage.

    Returns None if the ID is invalid or the file has expired/been deleted.
    """
    if not result_id or len(result_id) != 32:
        return None

    result_file = _result_file_path(result_id)
    if not result_file.exists():
        return None

    try:
        data = json.loads(result_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None

    return data if isinstance(data, list) else None


def _delete_result(result_id: str | None) -> None:
    """Best-effort cleanup for previously stored result files."""
    if not result_id or len(result_id) != 32:
        return

    result_file = _result_file_path(result_id)
    if result_file.exists():
        result_file.unlink()


def compute_summary(transactions):
    """Compute dashboard metrics and totals by category.

    Assumptions (based on parser normalization):
    - Negative Amount = Expense (Money Out)
    - Positive Amount = Income (Money In)
    """
    amounts = [float(tx["amount"]) for tx in transactions]

    # Filter expenses (negative) and income (positive)
    expenses = [-amount for amount in amounts if amount < 0]
    income = [amount for amount in amounts if amount > 0]

    total_spent = sum(expenses)
    total_income = sum(income)
    transaction_count = len(transactions)
    biggest_expense = max(expenses) if expenses else 0.0

    # Aggregate spending by category for the breakdown chart
    category_totals = {}
    for tx in transactions:
        amount = float(tx["amount"])

        # Only count expenses in the spending breakdown
        if amount < 0:
            category = tx.get("category") or "Other"
            # Use abs(amount) to sum positive spending values
            category_totals[category] = category_totals.get(category, 0.0) + abs(amount)

    return {
        "total_spent": total_spent,
        "total_income": total_income,
        "transaction_count": transaction_count,
        "biggest_expense": biggest_expense,
        "category_totals": category_totals,
    }


@app.get("/")
def index():
    """Render the home page and optional error message."""
    error = request.args.get("error")
    return render_template("index.html", error=error)


@app.post("/upload")
def upload():
    """Receive CSV upload, parse and categorize transactions, then show results.

    Flow:
    1. Validate file (extension, presence).
    2. Save temporarily to disk.
    3. Parse CSV into normalized format.
    4. Call OpenAI (or mock) to categorize descriptions.
    5. Save results to server-side JSON.
    6. Redirect to results page.
    """
    if "file" not in request.files:
        return redirect(url_for("index", error="Please choose a CSV file to upload."))

    file = request.files["file"]
    if file.filename == "":
        return redirect(url_for("index", error="No file selected."))

    if not file or not allowed_file(file.filename):
        return redirect(url_for("index", error="Invalid file type. Please upload a .csv file."))

    safe_name = secure_filename(file.filename)
    file_path = UPLOAD_FOLDER / safe_name

    try:
        file.save(file_path)

        # Parse: Convert generic CSV to structured dicts
        transactions = parse_bank_csv(str(file_path))
        if not transactions:
            raise ValueError("No transactions found in the CSV file.")

        # AI Categorization
        descriptions = [tx["description"] for tx in transactions]
        categories = categorize_transactions(descriptions)

        # Merge categories back into transactions
        for tx, category in zip(transactions, categories):
            tx["category"] = category

        # Cleanup old session data
        previous_result_id = session.pop("result_id", None)
        _delete_result(previous_result_id)

        # Store new results
        result_id = _store_transactions(transactions)
        session["result_id"] = result_id
        return redirect(url_for("results"))

    except ValueError as exc:
        # User error (bad CSV format)
        return redirect(url_for("index", error=str(exc)))
    except RuntimeError as exc:
        # System/API error
        return redirect(url_for("index", error=str(exc)))
    except Exception:
        # Unexpected fallback
        return redirect(url_for("index", error="Something went wrong while processing the file."))
    finally:
        # Always remove temporary uploaded files after processing to save space.
        if file_path.exists():
            file_path.unlink()


@app.get("/results")
def results():
    """Render results for the most recently processed CSV in this session."""
    result_id = session.get("result_id")
    transactions = _load_transactions(result_id)

    if not transactions:
        # Session expired or file deleted
        _delete_result(result_id)
        session.pop("result_id", None)
        return redirect(url_for("index", error="Upload a CSV file to view results."))

    summary = compute_summary(transactions)

    return render_template(
        "results.html",
        transactions=transactions,
        total_spent=summary["total_spent"],
        total_income=summary["total_income"],
        transaction_count=summary["transaction_count"],
        biggest_expense=summary["biggest_expense"],
        category_totals=summary["category_totals"],
    )


if __name__ == "__main__":
    debug_enabled = os.getenv("FLASK_DEBUG", "false").lower() in {"1", "true", "yes"}
    app.run(debug=debug_enabled)
