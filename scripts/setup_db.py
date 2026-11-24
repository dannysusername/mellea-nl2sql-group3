"""Build data/movielens.db from the official MovieLens "small" dataset.

Run from the repo root:  python scripts/setup_db.py

- Downloads ml-latest-small.zip from GroupLens (about 1 MB) and checks its MD5.
- Creates the same 4 tables, with the same columns, as Group 4's db_setup.py,
  so the baseline and the Mellea version run against the same database.
- Uses only the Python standard library (no pandas needed).
"""
import csv
import hashlib
import io
import sqlite3
import urllib.request
import zipfile
from pathlib import Path

URL = "https://files.grouplens.org/datasets/movielens/ml-latest-small.zip"
MD5 = "31a303aabbc519bd33d025e44d6c2570"  # published at URL + ".md5"

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
ZIP_PATH = DATA_DIR / "ml-latest-small.zip"
DB_PATH = DATA_DIR / "movielens.db"

SCHEMA = """
DROP TABLE IF EXISTS ratings;
DROP TABLE IF EXISTS tags;
DROP TABLE IF EXISTS links;
DROP TABLE IF EXISTS movies;

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
"""

# table name -> (columns in the CSV, function that converts one CSV row)
TABLES = {
    "movies": (["movieId", "title", "genres"],
               lambda r: (int(r["movieId"]), r["title"], r["genres"])),
    "links": (["movieId", "imdbId", "tmdbId"],
              lambda r: (int(r["movieId"]), r["imdbId"],
                         int(r["tmdbId"]) if r["tmdbId"] else None)),
    "ratings": (["userId", "movieId", "rating", "timestamp"],
                lambda r: (int(r["userId"]), int(r["movieId"]),
                           float(r["rating"]), int(r["timestamp"]))),
    "tags": (["userId", "movieId", "tag", "timestamp"],
             lambda r: (int(r["userId"]), int(r["movieId"]),
                        r["tag"], int(r["timestamp"]))),
}


def download() -> bytes:
    DATA_DIR.mkdir(exist_ok=True)
    if not ZIP_PATH.exists():
        print(f"Downloading {URL} ...")
        urllib.request.urlretrieve(URL, ZIP_PATH)
    data = ZIP_PATH.read_bytes()
    if hashlib.md5(data).hexdigest() != MD5:
        ZIP_PATH.unlink()
        raise RuntimeError("Download is corrupted (MD5 mismatch). Run the script again.")
    return data


def main() -> None:
    archive = zipfile.ZipFile(io.BytesIO(download()))
    con = sqlite3.connect(DB_PATH)
    con.execute("PRAGMA foreign_keys = ON")
    try:
        con.executescript(SCHEMA)
        for table in ["movies", "links", "ratings", "tags"]:  # movies first (foreign keys)
            columns, convert = TABLES[table]
            with archive.open(f"ml-latest-small/{table}.csv") as f:
                rows = [convert(r) for r in csv.DictReader(io.TextIOWrapper(f, encoding="utf-8"))]
            placeholders = ", ".join("?" for _ in columns)
            con.executemany(
                f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})", rows
            )
            print(f"  {table}: {len(rows):,} rows")
        con.commit()
        if con.execute("PRAGMA foreign_key_check").fetchall():
            raise RuntimeError("Foreign key check failed.")
    finally:
        con.close()
    print(f"Done: {DB_PATH}")


if __name__ == "__main__":
    main()
