"""Issue #15: run the baseline generator on every test-set question.

Run from the repo root (Ollama must be running):
    python scripts/setup_db.py   # once, builds data/movielens.db
    python run_baseline.py

For each question in tests/questions.json it prints the SQL the model wrote
and whether that SQL runs on the database. Everything is also saved to
results/baseline_sql.json so #16 can score it.

"Runs" only means SQLite didn't throw an error. It does NOT mean the answer
is correct; checking correctness is the scorer's job (#16, Group 2's #11).
"""
import json
import sqlite3
import time
from pathlib import Path

from baseline import generate_sql

ROOT = Path(__file__).resolve().parent
QUESTIONS = ROOT / "tests" / "questions.json"
DB_PATH = ROOT / "data" / "movielens.db"
OUT = ROOT / "results" / "baseline_sql.json"


def try_run(sql: str) -> str | None:
    """Run the SQL read-only. Return None if it worked, or the error message."""
    con = sqlite3.connect(f"{DB_PATH.as_uri()}?mode=ro", uri=True)
    try:
        con.execute(sql).fetchmany(5)
        return None
    except sqlite3.Error as e:
        return str(e)
    finally:
        con.close()


def main() -> None:
    if not DB_PATH.exists():
        raise SystemExit("data/movielens.db not found. Run: python scripts/setup_db.py")
    questions = json.loads(QUESTIONS.read_text())
    results = []
    for q in questions:
        start = time.time()
        sql = generate_sql(q["question"])
        error = try_run(sql)
        results.append({
            "id": q["id"],
            "question": q["question"],
            "sql": sql,
            "runs": error is None,
            "error": error,
            "seconds": round(time.time() - start, 1),
        })
        status = "runs" if error is None else f"ERROR: {error}"
        print(f"\n[{q['id']}] {q['question']}\n{sql}\n-> {status}")

    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(results, indent=2))
    ok = sum(r["runs"] for r in results)
    print(f"\nSQL produced for {len(results)}/{len(questions)} questions; "
          f"{ok} ran without an error, {len(results) - ok} crashed.")
    print(f"Saved to {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
