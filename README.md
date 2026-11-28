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


## Group 3: Benchmark (issue #14)

Baseline vs. Mellea on 2 Granite sizes, same 32 questions, same DB.

- **baseline**: one shot, no checks (`baseline.py`)
- **mellea**: same prompt, but the SQL has to run. If it crashes, the error goes back to the model and it retries (up to 3 tries)

### Run it

```bash
python benchmark.py --models granite4.1:3b granite4:1b
python benchmark.py --limit 3   # quick test
```

Saves `results/benchmark.json` + `results/benchmark.md`.

### Results (temp 0, CPU laptop)

| Model | System | Ran | Crashed | Avg tries | Avg sec |
|---|---|---|---|---|---|
| granite4.1:3b | baseline | 28/32 | 4 | 1.0 | 18.2 |
| granite4.1:3b | mellea | **30/32** | **2** | 1.16 | 13.8 |
| granite4:1b | baseline | 29/32 | 3 | 1.0 | 26.8 |
| granite4:1b | mellea | 29/32 | 3 | 1.19 | 14.2 |

"Ran" = no SQL error, not "correct." Accuracy fills in once Group 2 adds `gold_sql` (#10/#11).

### Why Mellea helped

- **3b: crashes cut in half (4 → 2).** It got the error back and fixed its own SQL.
- **1b: no change (3 → 3).** Same feedback, but the model wasn't strong enough to fix it.
- **q031 + q032 failed on both models.** Too hard for small local models.
- **Takeaway:** Mellea's a solid upgrade on a decent model, but it can't save a weak one.

### Notes

- granite4.1:8b ran out of memory on a student laptop, so we used Granite 4.0 1b as the small model.
- The Mellea side is our own validate + repair loop. Swap in Group 4's (#12/#13) when it merges.
