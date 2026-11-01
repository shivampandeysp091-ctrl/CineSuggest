"""
routes/movies.py
----------------
Endpoints for movies catalog, trending, now-playing, upcoming, top-rated,
search, and TMDB lookups.
"""

import logging
import os
import re
from typing import List, Optional

from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from database import get_db
from models import Movie
from services.tmdb import (
    format_movies_with_catalog,
    session as tmdb_session,
    tmdb_get_results,
    POSTER_BASE_URL,
    BACKDROP_BASE_URL,
    TMDB_BASE_URL,
)
from ml.recommender import popular_movies

load_dotenv()
logger = logging.getLogger("routes.movies")

router = APIRouter(
    prefix="/movies",
    tags=["Movies"],
)


# ============================================================
# 1. CATALOG: GET MOVIES
# ============================================================

@router.get("/")
def get_movies(
    limit: int = 20,
    db: Session = Depends(get_db),
):
    """Return catalog movies from PostgreSQL."""
    return db.query(Movie).limit(limit).all()


# ============================================================
# 2. TRENDING MOVIES (TMDB /trending/movie/week)
# ============================================================

@router.get("/trending")
def get_trending_movies(
    db: Session = Depends(get_db),
):
    """
    Get weekly trending movies from TMDB with 1-hour cache.
    Includes `in_catalog` and `movie_id` matching in a single query.
    """
    raw_movies = tmdb_get_results("/trending/movie/week")
    return format_movies_with_catalog(raw_movies, db)


# ============================================================
# 3. NOW PLAYING MOVIES (TMDB /movie/now_playing)
# ============================================================

@router.get("/now-playing")
def get_now_playing_movies(
    db: Session = Depends(get_db),
):
    """
    Get currently playing movies from TMDB with 1-hour cache.
    Includes `in_catalog` and `movie_id` matching in a single query.
    """
    raw_movies = tmdb_get_results("/movie/now_playing", {"language": "en-US", "page": 1})
    return format_movies_with_catalog(raw_movies, db)


@router.get("/new-releases")
def get_new_releases(
    db: Session = Depends(get_db),
):
    """Backward compatibility alias for /now-playing."""
    return get_now_playing_movies(db)


# ============================================================
# 4. UPCOMING MOVIES (TMDB /movie/upcoming)
# ============================================================

@router.get("/upcoming")
def get_upcoming_movies(
    db: Session = Depends(get_db),
):
    """
    Get upcoming movies from TMDB with 1-hour cache.
    Includes `in_catalog` and `movie_id` matching in a single query.
    """
    raw_movies = tmdb_get_results("/movie/upcoming", {"language": "en-US", "page": 1})
    return format_movies_with_catalog(raw_movies, db)


# ============================================================
# 5. TOP RATED MOVIES (FROM DATABASE: tmdb_rating DESC with poster)
# ============================================================

@router.get("/top-rated")
def top_rated_movies(
    limit: int = 20,
    db: Session = Depends(get_db),
):
    """
    Fetch top-rated movies directly from our database ordered by
    `tmdb_rating` DESC, filtering for movies that have a poster_url.
    """
    movies = (
        db.query(Movie)
        .filter(
            Movie.poster_url.isnot(None),
            Movie.tmdb_rating.isnot(None),
        )
        .order_by(Movie.tmdb_rating.desc())
        .limit(limit)
        .all()
    )

    return [
        {
            "movie_id": m.movie_id,
            "tmdb_id": m.tmdb_id,
            "title": m.title,
            "genres": m.genres,
            "release_year": m.release_year,
            "poster_url": m.poster_url,
            "backdrop_url": m.backdrop_url,
            "tmdb_rating": round(float(m.tmdb_rating), 1) if m.tmdb_rating is not None else None,
            "overview": m.overview,
            "runtime": m.runtime,
        }
        for m in movies
    ]


# ============================================================
# 6. SEARCH MOVIES (DATABASE FIRST, THEN TMDB)
# ============================================================

def clean_search_term(term: str) -> str:
    """Ignore brackets, parentheses, and trailing release years."""
    # 1. Remove bracketed contents e.g. (1995), [2021]
    cleaned = re.sub(r"\s*[\(\[\{].*?[\)\]\}]\s*", " ", term)
    # 2. Remove trailing 4-digit release year e.g. "Avatar 2009"
    cleaned = re.sub(r"\s+\b(18|19|20)\d{2}\b\s*$", "", cleaned)
    # 3. Collapse multiple spaces
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned if cleaned else term.strip()


@router.get("/search")
def search_movies(
    title: str = Query(...),
    db: Session = Depends(get_db),
):
    """
    Search movies:
    1) Case-insensitive partial match (ILIKE) on movies table, ignoring year/brackets.
    2) TMDB /search/movie results appended with duplicates removed (by tmdb_id).
    3) Returns single unified list with DB matches first, each containing `in_catalog`.
    """
    raw_query = title.strip()
    if not raw_query:
        return []

    clean_query = clean_search_term(raw_query)

    # ── 1. Search PostgreSQL database first (ILIKE, case-insensitive) ────────
    if clean_query != raw_query:
        filter_expr = or_(
            Movie.title.ilike(f"%{clean_query}%"),
            Movie.title.ilike(f"%{raw_query}%"),
        )
    else:
        filter_expr = Movie.title.ilike(f"%{clean_query}%")

    db_movies = (
        db.query(Movie)
        .filter(filter_expr)
        .limit(20)
        .all()
    )

    db_results = []
    seen_tmdb_ids = set()

    for m in db_movies:
        if m.tmdb_id:
            seen_tmdb_ids.add(m.tmdb_id)

        db_results.append({
            "movie_id": m.movie_id,
            "tmdb_id": m.tmdb_id,
            "title": m.title,
            "overview": m.overview or "",
            "poster_url": m.poster_url,
            "backdrop_url": m.backdrop_url,
            "release_date": f"{m.release_year}-01-01" if m.release_year else None,
            "release_year": m.release_year,
            "genres": m.genres,
            "tmdb_rating": round(float(m.tmdb_rating), 1) if m.tmdb_rating is not None else None,
            "in_catalog": True,
        })

    # ── 2. TMDB Search (appended, deduplicated by tmdb_id) ───────────────────
    raw_tmdb = tmdb_get_results(
        "/search/movie",
        {"query": clean_query, "language": "en-US", "include_adult": "false"},
    )
    catalog_tmdb = format_movies_with_catalog(raw_tmdb, db)

    tmdb_results = []
    for t in catalog_tmdb:
        tid = t.get("tmdb_id")
        if tid and tid in seen_tmdb_ids:
            continue
        if tid:
            seen_tmdb_ids.add(tid)
        tmdb_results.append(t)

    # ── 3. Combine with DB results first ─────────────────────────────────────
    return db_results + tmdb_results


# ============================================================
# 7. TMDB DETAILS + AUTO CATALOG IMPORT
# ============================================================

@router.get("/tmdb/{tmdb_id}")
def get_tmdb_movie(
    tmdb_id: int,
    db: Session = Depends(get_db),
):
    """Fetch movie details from TMDB by tmdb_id."""
    existing_movie = (
        db.query(Movie)
        .filter(Movie.tmdb_id == tmdb_id)
        .first()
    )

    try:
        resp = tmdb_session.get(f"{TMDB_BASE_URL}/movie/{tmdb_id}", timeout=10)
        if resp.status_code == 404:
            raise HTTPException(status_code=404, detail="Movie not found on TMDB.")
        if not resp.ok:
            raise HTTPException(status_code=resp.status_code, detail="Failed to fetch from TMDB.")
        data = resp.json()
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("TMDB details fetch error: %s", exc)
        raise HTTPException(status_code=500, detail="Unable to connect to TMDB.")

    release_date = data.get("release_date")
    release_year = None
    if release_date and len(str(release_date)) >= 4:
        try:
            release_year = int(str(release_date)[:4])
        except (ValueError, TypeError):
            release_year = None

    genres = " | ".join(g["name"] for g in data.get("genres", []))
    poster_url = f"{POSTER_BASE_URL}{data['poster_path']}" if data.get("poster_path") else None
    backdrop_url = f"{BACKDROP_BASE_URL}{data['backdrop_path']}" if data.get("backdrop_path") else None
    vote_avg = data.get("vote_average")

    return {
        "movie_id": existing_movie.movie_id if existing_movie else None,
        "tmdb_id": tmdb_id,
        "title": data.get("title") or (existing_movie.title if existing_movie else "Unknown Title"),
        "original_title": data.get("original_title"),
        "genres": genres or (existing_movie.genres if existing_movie else ""),
        "release_date": release_date,
        "release_year": release_year,
        "overview": data.get("overview"),
        "runtime": data.get("runtime"),
        "rating": round(float(vote_avg), 1) if vote_avg is not None else None,
        "vote_count": data.get("vote_count"),
        "popularity": data.get("popularity"),
        "poster_url": poster_url or (existing_movie.poster_url if existing_movie else None),
        "backdrop_url": backdrop_url or (existing_movie.backdrop_url if existing_movie else None),
        "in_catalog": existing_movie is not None,
        "source": "tmdb",
    }


# ============================================================
# 8. ONBOARDING MOVIES (FROM RECOMMENDER popular_movies())
# ============================================================

@router.get("/onboarding")
def get_onboarding_movies(
    n: int = Query(12, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """
    Return popular movies from recommender.popular_movies(n=n) enriched with
    poster_url, backdrop_url, release_year, and tmdb_rating from the movies table.
    """
    try:
        df = popular_movies(n=n)
    except Exception as exc:
        logger.warning("popular_movies recommender failed: %s", exc)
        df = None

    if df is None or df.empty:
        db_fallback = (
            db.query(Movie)
            .filter(Movie.poster_url.isnot(None))
            .order_by(Movie.tmdb_rating.desc().nullslast())
            .limit(n)
            .all()
        )
        return [
            {
                "movie_id": m.movie_id,
                "title": m.title,
                "genres": m.genres,
                "release_year": m.release_year,
                "poster_url": m.poster_url,
                "backdrop_url": m.backdrop_url,
                "tmdb_rating": round(float(m.tmdb_rating), 1) if m.tmdb_rating is not None else None,
                "overview": m.overview,
                "in_catalog": True,
            }
            for m in db_fallback
        ]

    rec_list = df.to_dict(orient="records")
    movie_ids = [int(r["movieId"]) for r in rec_list]

    db_movies = db.query(Movie).filter(Movie.movie_id.in_(movie_ids)).all()
    meta_map = {m.movie_id: m for m in db_movies}

    results = []
    for r in rec_list:
        mid = int(r["movieId"])
        db_m = meta_map.get(mid)
        results.append({
            "movie_id": mid,
            "title": db_m.title if (db_m and db_m.title) else r.get("title"),
            "genres": db_m.genres if (db_m and db_m.genres) else r.get("genres"),
            "release_year": db_m.release_year if db_m else None,
            "poster_url": db_m.poster_url if db_m else None,
            "backdrop_url": db_m.backdrop_url if db_m else None,
            "tmdb_rating": round(float(db_m.tmdb_rating), 1) if (db_m and db_m.tmdb_rating is not None) else None,
            "overview": db_m.overview if db_m else None,
            "in_catalog": True,
        })

    return results



# ============================================================
# 10. IMPORT TMDB MOVIE INTO CATALOG
# ============================================================

TMDB_IMPORT_ID_FLOOR = 1_000_000   # Safe offset above all MovieLens IDs

@router.post("/import-tmdb/{tmdb_id}")
def import_tmdb_movie(
    tmdb_id: int,
    db: Session = Depends(get_db),
):
    """
    Import a TMDB movie into the internal movies catalog so users can rate it.

    - Assigns a unique internal movie_id >= 1,000,000.
    - Sets source='tmdb_import' so the CF model is never invoked for it.
    - Idempotent: returns the existing record if already imported.
    - The movie will NOT appear in collaborative-filtering recommendations
      until it accumulates sufficient user ratings and is retrained.
    """
    # Already in catalog?
    existing = db.query(Movie).filter(Movie.tmdb_id == tmdb_id).first()
    if existing:
        return {
            "movie_id":        existing.movie_id,
            "tmdb_id":         existing.tmdb_id,
            "title":           existing.title,
            "in_catalog":      True,
            "source":          existing.source,
            "cf_eligible":     existing.source == "movielens",
            "message":         "Movie already in catalog",
        }

    # Fetch from TMDB
    try:
        resp = tmdb_session.get(f"{TMDB_BASE_URL}/movie/{tmdb_id}", timeout=10)
        if resp.status_code == 404:
            raise HTTPException(status_code=404, detail="Movie not found on TMDB.")
        if not resp.ok:
            raise HTTPException(status_code=resp.status_code, detail="TMDB request failed.")
        data = resp.json()
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("TMDB fetch error during import: %s", exc)
        raise HTTPException(status_code=500, detail="Unable to connect to TMDB.")

    # Parse metadata
    release_date = data.get("release_date", "")
    release_year = None
    if release_date and len(release_date) >= 4:
        try:
            release_year = int(release_date[:4])
        except (ValueError, TypeError):
            pass

    genres_str   = " | ".join(g["name"] for g in data.get("genres", []))
    poster_url   = f"{POSTER_BASE_URL}{data['poster_path']}"   if data.get("poster_path")   else None
    backdrop_url = f"{BACKDROP_BASE_URL}{data['backdrop_path']}" if data.get("backdrop_path") else None
    vote_avg     = data.get("vote_average")

    # Assign safe unique movie_id
    from sqlalchemy import text as _text
    max_import_id = db.execute(
        _text(
            "SELECT COALESCE(MAX(movie_id), :floor - 1) "
            "FROM movies WHERE movie_id >= :floor"
        ),
        {"floor": TMDB_IMPORT_ID_FLOOR},
    ).scalar()
    new_movie_id = max(TMDB_IMPORT_ID_FLOOR, int(max_import_id) + 1)

    title = data.get("title") or data.get("original_title") or "Unknown Title"

    new_movie = Movie(
        movie_id     = new_movie_id,
        title        = title,
        genres       = genres_str or None,
        release_year = release_year,
        tmdb_id      = tmdb_id,
        poster_url   = poster_url,
        backdrop_url = backdrop_url,
        overview     = data.get("overview") or None,
        runtime      = data.get("runtime") or None,
        tmdb_rating  = round(float(vote_avg), 1) if vote_avg is not None else None,
        source       = "tmdb_import",
    )
    db.add(new_movie)
    db.commit()
    db.refresh(new_movie)

    logger.info("Imported TMDB movie %s as internal id %s", tmdb_id, new_movie_id)

    return {
        "movie_id":    new_movie_id,
        "tmdb_id":     tmdb_id,
        "title":       title,
        "in_catalog":  True,
        "source":      "tmdb_import",
        "cf_eligible": False,
        "message": (
            "Movie imported. You can now rate it. "
            "AI collaborative recommendations for this title will become available "
            "after it accumulates sufficient user ratings in the catalog."
        ),
    }


# ============================================================
# 11. GET MOVIE BY DATABASE MOVIE_ID
# ============================================================

@router.get("/{movie_id}")
def get_movie(
    movie_id: int,
    db: Session = Depends(get_db),
):
    """Retrieve single movie by our database movie_id."""
    movie = (
        db.query(Movie)
        .filter(Movie.movie_id == movie_id)
        .first()
    )

    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found.")

    return movie