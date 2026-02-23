# BankLens Demo Script (5-7 Minutes)

## 1) Quick Intro (30 seconds)

Say:
"BankLens is a Flask web app where users upload a bank-statement CSV.  
The app parses the transactions, calls the OpenAI API to categorize descriptions, then renders a spending dashboard with totals and a category breakdown."

## 2) Architecture Walkthrough (1-2 minutes)

Point to files:
- `app.py`: Flask routes, upload lifecycle, server-side result storage, summary metrics.
- `parser.py`: flexible CSV column matching and amount normalization (single amount or debit/credit).
- `categorizer.py`: batched OpenAI categorization with strict response validation and category fallback.
- `templates/index.html` and `templates/results.html`: upload form and results dashboard.
- `tests/`: parser and route tests for happy paths and failures.

Say:
"I intentionally separated parsing, AI categorization, and HTTP logic so each part is testable and easy to explain."

## 3) Live Demo Flow (2-3 minutes)

### A) Happy Path
1. Upload `demo_data/happy_path.csv`.
2. Show:
   - Transaction table
   - Summary cards (total spent, count, biggest expense)
   - Category breakdown

Talk track:
"Negative values are treated as expenses, positive values as income. Categories are generated from transaction descriptions using a batched AI call."

### B) Alternate Bank Format
1. Upload `demo_data/debit_credit_format.csv`.
2. Show that debit/credit format also works.

Talk track:
"Parser supports common schema variations and normalizes everything into a signed `amount` field."

### C) Error Handling
1. Upload `demo_data/missing_amount_column.csv`.
2. Show user-friendly validation error.

Talk track:
"The app fails gracefully for invalid CSV structures and surfaces clear messages instead of stack traces."

## 4) AI Usage Story (1 minute)

Say:
"I used AI as a development tool in three ways:
1. Scaffolding: generated initial Flask route/template structure.
2. Refactoring: improved security by moving transaction data from client cookies to server-side storage.
3. Test acceleration: generated edge-case tests for CSV parsing and route failures.
I still validated logic manually and with tests before committing changes."

## 5) Interview Q&A Prompts (30-60 seconds)

If asked "How did you ensure reliability?":
- "I added tests for parser edge cases and upload route failures."
- "I validate AI output shape and category values before rendering."

If asked "What tradeoffs did you make?":
- "I used local JSON files for server-side storage to keep complexity low for an entry-level demo.  
  In production I would switch to a database and background jobs."

If asked "What would you do next?":
- "Add user auth, persistent history, and budget alerts."
- "Add async queue for AI calls and request tracing."
- "Add CSV schema preview before full processing."
