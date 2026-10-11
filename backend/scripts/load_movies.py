"""
scripts/load_movies.py
----------------------
Loads MovieLens movies.csv (and optionally links.csv) into the Postgres
`movies` table.

Columns filled:
  movie_id     <- movieId  (movies.csv)
  title        <- title    (movies.csv, without trailing year)
  genres       <- genres   (movies.csv, pipe-separated kept as-is)
  release_year <- parsed from "(YYYY)" in title
  tmdb_id      <- tmdbId   (links.csv, if file exists)

Idempotent: uses INSERT ... ON CONFLICT DO NOTHING so re-runs are safe.

Usage (run from backend/ directory):
  python scripts/load_movies.py
  python scripts/load_movies.py --movies ml/movies.csv --links ml/links.csv
"""

import argparse
import os
import re
import sys

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import text

# -- resolve paths relative to this script's location -------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(SCRIPT_DIR)

# Load .env from backend/
load_dotenv(dotenv_path=os.path.join(BACKEND_DIR, ".env"))

# Add backend/ to sys.path so we can import database / models
sys.path.insert(0, BACKEND_DIR)

from database import engine  # noqa: E402
import models  # noqa: E402, F401  (registers tables on Base)

# -- helpers ------------------------------------------------------------------
_YEAR_RE = re.compile(r"\((\d{4})\)\s*$")


def parse_year(title: str):
    """Extract 4-digit year from trailing '(YYYY)' in title, else None."""
    m = _YEAR_RE.search(title)
    return int(m.group(1)) if m else None


def clean_title(title: str) -> str:
    """Remove trailing '(YYYY)' from title."""
    return _YEAR_RE.sub("", title).strip()


# -- main ---------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="Load MovieLens data into Postgres movies table"
    )
    parser.add_argument(
        "--movies",
        default=os.path.join(BACKEND_DIR, "ml", "movies.csv"),
        help="Path to movies.csv (default: backend/ml/movies.csv)",
    )
    parser.add_argument(
        "--links",
        default=os.path.join(BACKEND_DIR, "ml", "links.csv"),
        help="Path to links.csv (default: backend/ml/links.csv, optional)",
    )
    args = parser.parse_args()

    # 1. Load movies.csv
    if not os.path.exists(args.movies):
        sys.exit(f"ERROR: movies.csv not found at {args.movies}")

    print(f"Reading movies from: {args.movies}")
    movies_df = pd.read_csv(
        args.movies,
        dtype={"movieId": int, "title": str, "genres": str},
    )
    movies_df.rename(columns={"movieId": "movie_id"}, inplace=True)

    movies_df["release_year"] = movies_df["title"].apply(parse_year)
    movies_df["title"] = movies_df["title"].apply(clean_title)
    movies_df["genres"] = movies_df["genres"].replace("(no genres listed)", None)

    # 2. Load links.csv (optional)
    movies_df["tmdb_id"] = None

    if os.path.exists(args.links):
        print(f"Reading links from:  {args.links}")
        links_df = pd.read_csv(
            args.links,
            usecols=lambda c: c in ("movieId", "tmdbId"),
        )
        links_df.rename(columns={"movieId": "movie_id", "tmdbId": "tmdb_id"}, inplace=True)
        links_df["movie_id"] = pd.to_numeric(links_df["movie_id"], errors="coerce")
        links_df["tmdb_id"] = pd.to_numeric(links_df["tmdb_id"], errors="coerce")
        links_df = links_df.dropna(subset=["movie_id"])
        links_df["movie_id"] = links_df["movie_id"].astype(int)
        movies_df = movies_df.merge(
            links_df, on="movie_id", how="left", suffixes=("_drop", "")
        )
        movies_df.drop(
            columns=[c for c in movies_df.columns if c.endswith("_drop")],
            inplace=True,
        )
    else:
        print(f"links.csv not found at {args.links} -- tmdb_id will be NULL for all rows.")

    # 3. Upsert into Postgres
    rows = movies_df[
        ["movie_id", "title", "genres", "release_year", "tmdb_id"]
    ].to_dict(orient="records")

    def sanitize(row: dict) -> dict:
        """Convert pandas NA / NaN to Python None so psycopg2 sends NULL, and ensure tmdb_id is int or None."""
        clean = {}
        for k, v in row.items():
            if pd.isna(v) or v is None:
                clean[k] = None
            elif k in ("tmdb_id", "release_year"):
                clean[k] = int(v)
            else:
                clean[k] = v
        return clean

    rows = [sanitize(r) for r in rows]

    upsert_sql = text("""
        INSERT INTO movies (movie_id, title, genres, release_year, tmdb_id)
        VALUES (:movie_id, :title, :genres, :release_year, :tmdb_id)
        ON CONFLICT (movie_id) DO UPDATE SET
            tmdb_id = EXCLUDED.tmdb_id,
            title = EXCLUDED.title,
            genres = EXCLUDED.genres,
            release_year = EXCLUDED.release_year
    """)

    BATCH = 1000
    total = len(rows)
    processed = 0

    print(f"Upserting {total:,} movies in batches of {BATCH}...")

    with engine.begin() as conn:
        for start in range(0, total, BATCH):
            batch = rows[start: start + BATCH]
            result = conn.execute(upsert_sql, batch)
            processed += result.rowcount
            done = min(start + BATCH, total)
            print(f"  {done:>6,} / {total:,} processed", end="\r")

    print(f"\nDone. {total:,} rows upserted / verified in database.")


if __name__ == "__main__":
    main()
