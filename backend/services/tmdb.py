"""
services/tmdb.py
----------------
TMDB API integration service with 1-hour in-memory cache,
safe error handling (no crashing, no token leakage),
and single-query catalog matching.
"""

import logging
import os
import time
from typing import Any, Dict, List, Optional

import requests
from dotenv import load_dotenv
from sqlalchemy.orm import Session

from models import Movie

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

logger = logging.getLogger("services.tmdb")

TMDB_API_KEY = os.getenv("TMDB_API_KEY")
TMDB_BASE_URL = os.getenv("TMDB_BASE_URL", "https://api.tmdb.org/3")
POSTER_BASE_URL = "https://image.tmdb.org/t/p/w500"
BACKDROP_BASE_URL = "https://image.tmdb.org/t/p/w1280"

# In-memory cache: cache_key -> (timestamp, data)
_CACHE: Dict[str, tuple[float, List[Dict[str, Any]]]] = {}
CACHE_TTL = 3600  # 1 hour in seconds

session = requests.Session()
session.headers.update({
    "Accept": "application/json",
    "User-Agent": "CineSuggest-AI/2.0",
})
if TMDB_API_KEY:
    session.headers.update({
        "Authorization": f"Bearer {TMDB_API_KEY}",
    })


def tmdb_get_results(endpoint: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """
    Fetch a list of results from a TMDB endpoint with 1-hour in-memory caching.
    Returns [] on any failure, logs error without exposing secret tokens.
    """
    if not TMDB_API_KEY:
        logger.warning("TMDB_API_KEY is not configured in .env")
        return []

    # Cache lookup
    cache_key = f"{endpoint}?{sorted(params.items()) if params else ''}"
    now = time.time()
    if cache_key in _CACHE:
        cached_time, cached_data = _CACHE[cache_key]
        if now - cached_time < CACHE_TTL:
            return cached_data

    url = f"{TMDB_BASE_URL}{endpoint}"
    try:
        resp = session.get(url, params=params, timeout=10)
        if resp.status_code == 200:
            results = resp.json().get("results", [])
            _CACHE[cache_key] = (now, results)
            return results
        else:
            logger.error("TMDB request to %s failed with status code %s", endpoint, resp.status_code)
            return []
    except requests.exceptions.Timeout:
        logger.error("TMDB request to %s timed out after 10s", endpoint)
        return []
    except Exception as exc:
        logger.error("TMDB request to %s failed: %s", endpoint, exc)
        return []


def format_movies_with_catalog(raw_movies: List[Dict[str, Any]], db: Session) -> List[Dict[str, Any]]:
    """
    Formats TMDB movies and checks if each tmdb_id exists in our `movies` table.
    Uses a single batch query (WHERE tmdb_id IN (...)) for efficiency.
    """
    if not raw_movies:
        return []

    # Extract all valid tmdb_ids
    tmdb_ids = [m["id"] for m in raw_movies if m.get("id")]

    # Single DB query to check presence in our catalog
    catalog_map = {}
    if tmdb_ids:
        rows = (
            db.query(Movie.movie_id, Movie.tmdb_id)
            .filter(Movie.tmdb_id.in_(tmdb_ids))
            .all()
        )
        catalog_map = {r.tmdb_id: r.movie_id for r in rows if r.tmdb_id is not None}

    items = []
    for m in raw_movies:
        tid = m.get("id")
        if not tid:
            continue

        mid = catalog_map.get(tid)
        poster_path = m.get("poster_path")
        vote_avg = m.get("vote_average")

        items.append({
            "tmdb_id": tid,
            "title": m.get("title") or m.get("name") or "Unknown Title",
            "overview": m.get("overview") or "",
            "poster_url": f"{POSTER_BASE_URL}{poster_path}" if poster_path else None,
            "release_date": m.get("release_date") or m.get("first_air_date"),
            "tmdb_rating": round(float(vote_avg), 1) if vote_avg is not None else None,
            "in_catalog": mid is not None,
            "movie_id": mid,
        })

    return items
