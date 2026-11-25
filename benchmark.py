"""#14: baseline vs. Mellea, across Granite model sizes.

baseline: one shot, no checks (same prompt as baseline.py)
mellea:   same prompt, but the SQL has to run. If it crashes, the SQLite
          error goes back to the model and it retries (up to 3 tries).

Usage (repo root, Ollama running, data/movielens.db built):
    python benchmark.py
    python benchmark.py --limit 3
    python benchmark.py --models granite4.1:3b

Outputs results/benchmark.json + results/benchmark.md.
"Ran" = no SQLite error. Add "gold_sql" to a question to also get accuracy.
"""
import argparse
import json
import sqlite3
import time
from pathlib import Path

import mellea
from mellea.backends.model_options import ModelOption
from mellea.stdlib.requirements import req, simple_validate
from mellea.stdlib.sampling import RepairTemplateStrategy

from baseline import SCHEMA, strip_code_fences

ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "data" / "movielens.db"
QUESTIONS = ROOT / "tests" / "questions.json"
RESULTS = ROOT / "results"
MODELS = ["granite4.1:3b", "granite4.1:8b"]
LOOP_BUDGET = 3


def prompt(question):
    # same as baseline.py so the only variable is Mellea
    return f"SQLite database schema:\n{SCHEMA}\n\nWrite one SQL query that answers: {question}\nReturn only the SQL."


def run_sql(sql, limit=None):
    """Read-only run. Returns (rows, None) or (None, error)."""
    con = sqlite3.connect(f"{DB_PATH.as_uri()}?mode=ro", uri=True)
    try:
        cur = con.execute(sql)
        return (cur.fetchmany(limit) if limit else cur.fetchall()), None
    except sqlite3.Error as e:
        return None, str(e)
    finally:
        con.close()


def sql_runs(output):
    # the error message doubles as repair feedback for the next try
    _, err = run_sql(strip_code_fences(output), limit=5)
    return (True, "ok") if err is None else (False, f"SQL failed with: {err}. Fix the query.")


SQL_MUST_RUN = req("The SQL must run on the SQLite database.", validation_fn=simple_validate(sql_runs))


def baseline_generate(m, question):
    return strip_code_fences(m.instruct(prompt(question), strategy=None).value), 1


def mellea_generate(m, question):
    res = m.instruct(
        prompt(question),
        requirements=[SQL_MUST_RUN],
        strategy=RepairTemplateStrategy(loop_budget=LOOP_BUDGET),
        return_sampling_results=True,
    )
    final = res.value if res.success else res.sample_generations[-1].value  # last try if all failed
    return strip_code_fences(final), len(res.sample_generations)


SYSTEMS = {"baseline": baseline_generate, "mellea": mellea_generate}


def same_rows(a, b):
    # order + column names don't matter, floats rounded
    norm = lambda rows: sorted(tuple(round(v, 4) if isinstance(v, float) else v for v in r) for r in rows)
    return norm(a) == norm(b)


def evaluate(system, generate, m, model, questions):
    out = []
    for q in questions:
        t = time.time()
        try:
            sql, tries = generate(m, q["question"])
            rows, err = run_sql(sql)
        except Exception as e:  # model blowing up counts as a crash
            sql, tries, rows, err = "", 0, None, f"generation failed: {e}"
        correct = None
        if q.get("gold_sql"):
            gold, _ = run_sql(q["gold_sql"])
            correct = rows is not None and gold is not None and same_rows(rows, gold)
        out.append(dict(model=model, system=system, id=q["id"], question=q["question"], sql=sql,
                        runs=err is None, error=err, correct=correct, attempts=tries,
                        seconds=round(time.time() - t, 1)))
        print(f"  [{'ok ' if err is None else 'ERR'}] {q['id']} (tries: {tries})")
    return out


def summarize(records):
    rows = []
    for model, system in dict.fromkeys((r["model"], r["system"]) for r in records):
        g = [r for r in records if r["model"] == model and r["system"] == system]
        graded = [r for r in g if r["correct"] is not None]
        ran = sum(r["runs"] for r in g)
        rows.append(dict(
            model=model, system=system, questions=len(g), ran=ran, crashed=len(g) - ran,
            accuracy=f"{sum(r['correct'] for r in graded)}/{len(graded)}" if graded else "n/a",
            avg_attempts=round(sum(r["attempts"] for r in g) / len(g), 2),
            avg_seconds=round(sum(r["seconds"] for r in g) / len(g), 1),
        ))
    return rows


def to_markdown(summary):
    lines = ["| Model | System | Ran | Crashed | Accuracy | Avg tries | Avg sec |", "|---|---|---|---|---|---|---|"]
    lines += [f"| {s['model']} | {s['system']} | {s['ran']}/{s['questions']} | {s['crashed']} | "
              f"{s['accuracy']} | {s['avg_attempts']} | {s['avg_seconds']} |" for s in summary]
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description="baseline vs. Mellea benchmark (#14)")
    ap.add_argument("--models", nargs="+", default=MODELS)
    ap.add_argument("--limit", type=int, help="only run the first N questions")
    args = ap.parse_args()

    if not DB_PATH.exists():
        raise SystemExit("data/movielens.db not found. Run: python scripts/setup_db.py")
    questions = json.loads(QUESTIONS.read_text())[: args.limit]

    records = []
    for model in args.models:
        # temp 0 so reruns are reproducible
        m = mellea.start_session(backend_name="ollama", model_id=model,
                                 model_options={ModelOption.TEMPERATURE: 0})
        for name, gen in SYSTEMS.items():
            print(f"\n== {model} / {name} ({len(questions)} questions)")
            records += evaluate(name, gen, m, model, questions)

    summary = summarize(records)
    table = to_markdown(summary)
    RESULTS.mkdir(exist_ok=True)
    (RESULTS / "benchmark.json").write_text(json.dumps({"summary": summary, "records": records}, indent=2))
    (RESULTS / "benchmark.md").write_text(table + "\n")
    print(f"\n{table}\n\nsaved to results/benchmark.json + results/benchmark.md")


if __name__ == "__main__":
    main()
