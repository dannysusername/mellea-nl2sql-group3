"""Issue #15: Plain-prompt SQL generator (no validation).

The "before" version: ask the model once, return whatever SQL it writes.
No checks, no retries. Mellea's checking is added later by Group 4.
"""
import re

import mellea

m = mellea.start_session(backend_name="ollama", model_id="granite4.1:3b")

# MovieLens "small" (ml-latest-small from GroupLens).
# Copied from the CREATE TABLE statements in Group 4's db_setup.py
# (github.com/Ozald/mellea-nl2sql, branch feature/query-generation-and-validation)
# so the baseline sees the same tables and columns as the Mellea version.
# If Group 1 (#7) builds the database differently, update this to match.
SCHEMA = """
CREATE TABLE movies (
    movieId INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    genres TEXT NOT NULL
);

CREATE TABLE links (
    movieId INTEGER PRIMARY KEY,
    imdbId TEXT,
    tmdbId INTEGER,
    FOREIGN KEY (movieId) REFERENCES movies(movieId)
);

CREATE TABLE ratings (
    ratingId INTEGER PRIMARY KEY,
    userId INTEGER NOT NULL,
    movieId INTEGER NOT NULL,
    rating REAL NOT NULL,
    timestamp INTEGER NOT NULL,
    FOREIGN KEY (movieId) REFERENCES movies(movieId)
);

CREATE TABLE tags (
    tagId INTEGER PRIMARY KEY,
    userId INTEGER NOT NULL,
    movieId INTEGER NOT NULL,
    tag TEXT NOT NULL,
    timestamp INTEGER NOT NULL,
    FOREIGN KEY (movieId) REFERENCES movies(movieId)
);
""".strip()


def generate_sql(question: str) -> str:
    prompt = (
        f"SQLite database schema:\n{SCHEMA}\n\n"
        f"Write one SQL query that answers: {question}\n"
        "Return only the SQL."
    )
    # strategy=None means no checking and no retries
    answer = m.instruct(prompt, strategy=None).value
    return strip_code_fences(answer)


def strip_code_fences(text: str) -> str:
    """Remove Markdown ```sql ... ``` wrappers if the model added them.

    This is cleanup, not validation: the SQL itself is never checked or changed.
    """
    match = re.search(r"```(?:sql)?\s*(.*?)```", text, re.DOTALL | re.IGNORECASE)
    return (match.group(1) if match else text).strip()


if __name__ == "__main__":
    print(generate_sql("What is the average rating of 'Toy Story (1995)'?"))
