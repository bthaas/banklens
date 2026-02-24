# BankLens Demo Script (5-7 Minutes)

## 1) Quick Intro (30 seconds)

Say:
"BankLens is a Flask web app where users upload a bank-statement CSV.  
The app parses the transactions, calls the OpenAI API to categorize descriptions, then renders a spending dashboard with totals and a category breakdown."

## 2) Architecture Walkthrough (1-2 minutes)

Point to files:
- `app.py`: Flask routes, upload lifecycle, server-side result storage, summary metrics (now tracking Income vs Expense).
- `parser.py`: flexible CSV column matching and strict amount normalization (Negative = Out, Positive = In).
- `categorizer.py`: OpenAI integration with **Batching** (to avoid token limits) and a **Mock Mode** (for reliable offline demos).
- `templates/index.html` and `templates/results.html`: upload form and results dashboard.
- `tests/`: parser, route, and logic tests.

Say:
"I intentionally separated parsing, AI categorization, and HTTP logic so each part is testable and easy to explain. I also added detailed comments throughout the code to explain the 'why' behind decisions."

## 3) Live Demo Flow (2-3 minutes)

### A) Happy Path
1. Upload `demo_data/happy_path.csv`.
2. Show:
   - Transaction table (with categories)
   - Summary cards: **Total Spent**, **Total Income**, Count, Biggest Expense
   - Category breakdown (Expenses only)

Talk track:
"Negative values are treated as expenses, positive values as income. Categories are generated from transaction descriptions using a batched AI call (or a deterministic mock for this demo)."

### B) Alternate Bank Format
1. Upload `demo_data/debit_credit_format.csv`.
2. Show that debit/credit format also works.

Talk track:
"The parser supports common schema variations (like separate Debit/Credit columns) and normalizes everything into a signed `amount` field."

### C) Error Handling
1. Upload `demo_data/missing_amount_column.csv`.
2. Show user-friendly validation error.

Talk track:
"The app fails gracefully for invalid CSV structures and surfaces clear messages instead of stack traces."

## 4) AI Usage Story (1 minute)

Say:
"I used AI as a development tool in three ways:
1. **Scaffolding**: generated initial Flask route/template structure.
2. **Refactoring**: improved security (server-side storage) and added features like Mock Mode and Batching.
3. **Test acceleration**: generated edge-case tests for CSV parsing.
I still validated logic manually and with tests before committing changes."

## 5) Interview Q&A Prompts (30-60 seconds)

If asked "How did you ensure reliability?":
- "I implemented **Batching** in `categorizer.py` to handle large CSVs without hitting API token limits."
- "I added a **Mock Mode** so the app works even if the API is down or keys are missing."
- "I strictly validate AI output (JSON shape, allowed categories) before using it."

If asked "What tradeoffs did you make?":
- "I used local JSON files for server-side storage to keep complexity low for an entry-level demo. In production I would switch to a database."
- "The categorizer is synchronous. For a real app, I'd move this to a background job (Celery/Redis) to avoid timeouts."

If asked "What would you do next?":
- "Add user auth, persistent history, and budget alerts."
- "Add async queue for AI calls."
- "Add visual charts (Chart.js) to the dashboard."
