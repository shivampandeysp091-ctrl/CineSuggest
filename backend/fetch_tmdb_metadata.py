"""
fetch_tmdb_metadata.py
----------------------
Fetches TMDB metadata for every movie in the `movies` table that already has
a tmdb_id but is missing a poster_url (resume-safe).

Strategy  : GET /movie/{tmdb_id}  (direct ID lookup — no search needed)
Auth      : Bearer token from TMDB_API_KEY in backend/.env
Saves     : poster_url, backdrop_url, overview, runtime, tmdb_rating
Idempotent: rows with poster_url already set are skipped
Batches   : DB commit every 100 rows
Failures  : written to tmdb_failed_movies.txt (appended, not overwritten)
"""

import argparse
import os
import sys
import time

import requests
from dotenv import load_dotenv
from sqlalchemy import text

# ── env + path ────────────────────────────────────────────────────────────────
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

TMDB_API_KEY = os.getenv("TMDB_API_KEY")
if not TMDB_API_KEY:
    sys.exit("ERROR: TMDB_API_KEY not set in backend/.env")

from database import engine  # noqa: E402 (after load_dotenv)

# ── config ────────────────────────────────────────────────────────────────────
TMDB_BASE_URL   = "https://api.tmdb.org/3"
POSTER_BASE     = "https://image.tmdb.org/t/p/w500"
BACKDROP_BASE   = "https://image.tmdb.org/t/p/w1280"
REQUEST_DELAY   = 0.25          # seconds between TMDB calls
REQUEST_TIMEOUT = (5, 15)       # (connect, read) seconds
COMMIT_BATCH    = 100           # commit every N successful updates
FAIL_LOG        = os.path.join(os.path.dirname(__file__), "tmdb_failed_movies.txt")

# ── HTTP session ──────────────────────────────────────────────────────────────
session = requests.Session()
session.headers.update({
    "Authorization": f"Bearer {TMDB_API_KEY}",
    "Accept": "application/json",
    "User-Agent": "CineSuggest-AI/2.0",
})


# ── TMDB call ─────────────────────────────────────────────────────────────────
def fetch_tmdb(tmdb_id: int) -> dict | None:
    """GET /movie/{tmdb_id} and return JSON dict, or None on any error."""
    url = f"{TMDB_BASE_URL}/movie/{tmdb_id}"
    try:
        resp = session.get(url, timeout=REQUEST_TIMEOUT)
        if resp.status_code == 404:
            return None          # movie deleted/not found on TMDB
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.Timeout:
        print(f"      ⏱  Timeout for tmdb_id={tmdb_id}")
        return None
    except requests.exceptions.RequestException as exc:
        print(f"      ❌  Request error: {exc}")
        return None
    except ValueError:
        print(f"      ❌  Invalid JSON for tmdb_id={tmdb_id}")
        return None


# ── DB update (single row, within an open connection) ─────────────────────────
_UPDATE_SQL = text("""
    UPDATE movies
    SET
        poster_url   = :poster_url,
        backdrop_url = :backdrop_url,
        overview     = :overview,
        runtime      = :runtime,
        tmdb_rating  = :tmdb_rating
    WHERE movie_id = :movie_id
""")


def build_row(movie_id: int, data: dict) -> dict:
    """Extract the fields we care about from a TMDB /movie/{id} response."""
    poster_path   = data.get("poster_path")
    backdrop_path = data.get("backdrop_path")
    vote_avg      = data.get("vote_average")

    return {
        "movie_id":    movie_id,
        "poster_url":  (POSTER_BASE   + poster_path)   if poster_path   else None,
        "backdrop_url":(BACKDROP_BASE + backdrop_path) if backdrop_path else None,
        "overview":    data.get("overview") or None,
        "runtime":     data.get("runtime")  or None,
        "tmdb_rating": float(vote_avg) if vote_avg else None,
    }


# ── main ──────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="Fetch TMDB metadata for movies missing posters"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of movies to process (e.g. --limit 20 for quick test)",
    )
    args = parser.parse_args()

    print()
    print("=" * 70)
    print("      CINESUGGEST-AI  —  TMDB METADATA FETCHER  (v2)")
    print("=" * 70)
    print()

    # Fetch only rows that HAVE a tmdb_id but are missing poster_url (resumable)
    query_str = """
        SELECT movie_id, title, tmdb_id
        FROM   movies
        WHERE  tmdb_id   IS NOT NULL
          AND  poster_url IS NULL
        ORDER  BY movie_id
    """
    if args.limit:
        query_str += f" LIMIT {args.limit}"

    with engine.connect() as conn:
        movies = conn.execute(text(query_str)).mappings().all()

    total = len(movies)
    if args.limit:
        print(f"Limit applied      : {args.limit}")
    print(f"Movies to process  : {total:,}")
    print(f"Commit batch size  : {COMMIT_BATCH}")
    print(f"Request delay      : {REQUEST_DELAY}s")
    print()

    if total == 0:
        print("All movies with a tmdb_id already have metadata. Nothing to do.")
        return

    success   = 0
    skipped   = 0
    failed    = 0
    pending   = []          # rows waiting for next batch commit
    fail_log  = []

    with engine.connect() as conn:
        for idx, movie in enumerate(movies, start=1):
            movie_id = movie["movie_id"]
            tmdb_id  = movie["tmdb_id"]
            title    = movie["title"]

            print(f"[{idx:>5}/{total}] id={movie_id}  tmdb={tmdb_id}  {title[:50]}")

            data = fetch_tmdb(tmdb_id)

            if data is None:
                reason = f"TMDB returned nothing for tmdb_id={tmdb_id}"
                print(f"         ⚠  {reason}")
                failed += 1
                fail_log.append(f"{movie_id} | {title} | {reason}")
                time.sleep(REQUEST_DELAY)
                continue

            row = build_row(movie_id, data)

            poster_flag   = "YES" if row["poster_url"]   else "NO "
            backdrop_flag = "YES" if row["backdrop_url"] else "NO "
            rating_str    = f"{row['tmdb_rating']:.1f}" if row["tmdb_rating"] else "N/A"
            runtime_str   = str(row["runtime"]) if row["runtime"] else "N/A"

            print(
                f"         poster={poster_flag}  backdrop={backdrop_flag}"
                f"  runtime={runtime_str}min  rating={rating_str}"
            )

            pending.append(row)
            success += 1

            # Commit every COMMIT_BATCH rows
            if len(pending) >= COMMIT_BATCH:
                conn.execute(_UPDATE_SQL, pending)
                conn.commit()
                print(f"         >>> Committed {len(pending)} rows to DB")
                pending = []

            time.sleep(REQUEST_DELAY)

        # Final commit for remaining rows
        if pending:
            conn.execute(_UPDATE_SQL, pending)
            conn.commit()
            print(f"         >>> Final commit: {len(pending)} rows")

    # ── failure log ───────────────────────────────────────────────────────────
    if fail_log:
        mode = "a"  # append so previous failures are preserved
        with open(FAIL_LOG, mode, encoding="utf-8") as fh:
            fh.write("\n".join(fail_log) + "\n")
        print(f"\nFailed entries appended to: {FAIL_LOG}")

    # ── summary ───────────────────────────────────────────────────────────────
    print()
    print("=" * 70)
    print("                      IMPORT COMPLETE")
    print("=" * 70)
    print(f"  Successful : {success:>6,}")
    print(f"  Failed     : {failed:>6,}")
    print(f"  Total      : {success + failed:>6,} / {total:,}")
    print("=" * 70)
    print()


if __name__ == "__main__":
    main()
