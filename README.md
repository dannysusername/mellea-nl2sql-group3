# mellea-nl2sql
FIU Student Mellea Project: Ask-Your-Database

Ask a real database questions in plain English and get real answers back — built with Mellea so the generated SQL is validated and automatically repaired if it's wrong.

## Setup
Python 3.11+
pip install mellea
A backend: Ollama running an IBM Granite model locally, or a hosted Granite endpoint
Pick a database

## How to contribute
Fork this repo, pick an open issue, and open a pull request. The interface (CLI, notebook, or web app) is your team's choice

## Group 3: Baseline (issue #15)

The "before Mellea" version: the model writes SQL once, with no checking and no retries.

| File | What it does |
|---|---|
| `baseline.py` | `generate_sql(question)` asks Granite for SQL once (`strategy=None`, so no validation) |
| `scripts/setup_db.py` | Downloads MovieLens "small" and builds `data/movielens.db` (same tables as Group 4's) |
| `run_baseline.py` | Runs every question in `tests/questions.json` and saves results to `results/baseline_sql.json` |
| `tests/questions.json` | Group 2's 32 questions, copied from their PR #18 (answers not filled in yet) |

### Run it

You need Python 3.11+ and [Ollama](https://ollama.com) running.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
ollama pull granite4.1:3b

python scripts/setup_db.py   # once: builds data/movielens.db
python run_baseline.py       # about 2-3 minutes
```

### Latest result (Nov 24, 2026, granite4.1:3b)

- SQL produced for **32/32** questions
- **28** ran, **4** crashed (q023, q030, q031, q032)
- "Ran" doesn't mean "correct." Accuracy needs Group 2's answers (#10) and scorer (#11).
