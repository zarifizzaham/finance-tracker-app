# Simple Finance Dashboard

A personal finance tracking app built with Streamlit. Upload your bank statement CSVs and get instant categorised spending breakdowns, month-over-month comparisons, and a 50/30/20 budget analysis — all running locally with no data leaving your machine.

---

## Features

- **Multi-month, multi-bank upload** — drop in one or more CSVs per month; multiple banks for the same month are merged automatically
- **Auto-categorisation** — transactions are matched against keyword rules you define; one override teaches the app and applies it to matching descriptions in the same month and all other loaded months
- **Manual override** — edit any category directly in the table with a colour-coded status indicator (🔴 uncategorised, 🟢 categorised); changes persist across sessions
- **Compare Months** — side-by-side bar charts, stacked category breakdown, top-6 trend lines, and month-over-month % change
- **50/30/20 Rule** — budget calculator, savings projections (cash / easy-access / index fund scenarios), and actual vs target breakdown across three buckets: Needs, Wants, and Savings
- **PDF report export** — generates a multi-page PDF with a full transaction log, per-month expense charts, month comparison, and a 40-year savings projection
- **Custom bank support** — map any unrecognised CSV format once; saved and reused automatically
- **Frosted glass UI** — dark-themed with a background image; charts use transparent backgrounds

---

## Supported Banks

| Bank | Auto-detected by |
|---|---|
| Monzo | `Emoji`, `Name` columns |
| Revolut | `Started Date`, `Completed Date` columns |
| Barclays | `Memo`, `Subcategory` columns |
| HSBC | `Paid out`, `Paid in` columns |
| Starling | `Counter Party`, `Reference` columns |
| **Any other bank** | Map columns manually on first upload — saved for next time |

---

## Setup

**Requirements:** Python 3.11+

1. Clone or download this repository.

2. (Optional but recommended) Create a virtual environment:
   ```
   python -m venv .venv
   .venv\Scripts\activate        # Windows
   source .venv/bin/activate     # macOS / Linux
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Place your background image (`image finance tracker.webp`) in the project root. The app will error on startup if this file is missing.

---

## Running the App

```
python -m streamlit run app.py
```

The app opens in your browser at `http://localhost:8501`.

**Important:** Always stop the server with `Ctrl+C` when you are done. If you close the terminal window without stopping it, a stale process may keep port 8501 occupied. If the browser shows no changes after edits, check for a second running instance on port 8502 using:

```
Get-Process python* | Stop-Process -Force   # PowerShell (Windows)
pkill -f streamlit                          # macOS / Linux
```

Then restart with the command above and open a fresh browser tab.

---

## How to Use

### Uploading statements

1. Click **Browse files** at the top and select one or more CSV files (one per calendar month).
2. The app detects your bank automatically. If it doesn't recognise the format, a column-mapping UI appears — fill it in once and the mapping is saved.
3. Each loaded month appears as a tab.

### Categorising transactions

- Transactions are auto-assigned based on saved keyword rules.
- Each row shows a status indicator: 🔴 uncategorised, 🟢 categorised.
- To change a category: find the row in the **Cash Outflow** or **Cash Inflow** table, select a new category from the dropdown, then click **Apply Changes**.
- Applying a change saves a keyword rule and propagates it to every other row with the same description — in the same month and across all other loaded months.

### Managing categories

Open the sidebar (arrow on the left) to:
- Add a new category
- Delete a category (transactions revert to Uncategorised and all saved overrides for that category are removed)

### 50/30/20 Rule tab

1. Enter your monthly take-home pay (after tax).
2. Adjust the savings slider to explore different saving rates.
3. Scroll to **Your Spending vs 50/30/20** and assign each of your categories to **Needs**, **Wants**, or **Savings** (e.g. pension, ISA).
4. The app calculates how your actual spending compares to the 50/30/20 targets and projects your total savings rate over 40 years.

### Downloading a PDF report

1. Open the sidebar and expand **Before you download — checklist**.
2. Complete all four steps: upload CSVs, categorise all transactions, enter your take-home pay, and assign Needs/Wants in the 50/30/20 tab.
3. Click **Generate Report** — the PDF renders in the background.
4. Click **Download Report PDF** to save it.

---

## File Structure

```
Finance App/
├── app.py                         # Entry point — Streamlit page config, CSS, tab layout
├── config.py                      # Bank CSV format definitions and date format options
├── ingestion.py                   # Bank detection, CSV parsing, month labelling
├── categories.py                  # Keyword matching, override propagation, category CRUD
├── persistence.py                 # JSON read/write for overrides, mappings, and categories
├── requirements.txt
├── image finance tracker.webp     # Background image (required)
├── ui/
│   ├── month.py                   # Per-month transaction tables and expense charts
│   ├── comparison.py              # Multi-month comparison charts and summary metrics
│   ├── budget_rule.py             # 50/30/20 calculator, projections, actual breakdown
│   ├── sidebar.py                 # Category management sidebar
│   ├── mapping.py                 # Column mapping UI for unrecognised bank formats
│   └── welcome.py                 # Welcome screen shown before any files are uploaded
└── .gitignore
```

### Runtime-generated files

These are created automatically and excluded from git (they contain personal financial data):

| File | Contents |
|---|---|
| `categories.json` | Category names and their keyword lists |
| `outflow_overrides.json` | Per-transaction category overrides (outflows) |
| `inflow_overrides.json` | Per-transaction category overrides (inflows) |
| `bank_mappings.json` | Saved column mappings for custom bank formats |
| `bucket_assignments.json` | 50/30/20 Needs/Wants bucket selections |

Delete any of these files to reset that part of the app to its defaults.

---

## What is Excluded from Git

The `.gitignore` excludes:

- All `*.csv` files — your bank statements
- All runtime JSON files listed above — your categories and overrides
- `__pycache__/` — compiled bytecode
- `notebooks/` and `archive/` — development scratchpad files
- `.venv/`, `.vscode/`, `.idea/` — local environment and editor config
