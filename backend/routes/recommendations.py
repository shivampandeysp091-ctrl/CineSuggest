"""
routes/recommendations.py
--------------------------
GET /recommendations/me   — personalized recommendations for the logged-in user.

Flow:
  1. JWT se user_id lo  (deps.get_current_user)
  2. user_ml_mapping  se ml_user_id lo
  3. user_ratings     se rated movie ids aur ratings lo
  4. watch_history    se watched movie ids lo (exclude_movie_ids)
  5. Recommender call:
       ml_user_id <= 610  → get_hybrid_recommendations
       ml_user_id >  610  → get_new_user_recommendations
  6. movies table se poster_url, overview jodo
  7. Khaali result → popular_movies fallback ("personalized": false)
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from database import get_db
from deps import get_current_user
from ml.recommender import (
    get_hybrid_recommendations,
    get_new_user_recommendations,
    popular_movies,
)

router = APIRouter(
    prefix="/recommendations",
    tags=["Recommendations"],
)


# ── helpers ───────────────────────────────────────────────────────────────────

def _fetch_movie_details(db: Session, movie_ids: list[int]) -> dict:
    """Fetch poster_url, overview (and more) for a list of movie_ids from DB."""
    if not movie_ids:
        return {}
    placeholders = ", ".join(f":mid_{i}" for i in range(len(movie_ids)))
    params = {f"mid_{i}": mid for i, mid in enumerate(movie_ids)}
    rows = db.execute(
        text(f"""
            SELECT movie_id, title, genres, release_year,
                   tmdb_id, poster_url, backdrop_url, overview, runtime, tmdb_rating
            FROM   movies
            WHERE  movie_id IN ({placeholders})
        """),
        params,
    ).mappings().all()
    return {r["movie_id"]: dict(r) for r in rows}


def _build_item(rec: dict, movie: dict | None) -> dict:
    """Merge a recommender row with DB movie details into one response item."""
    base = {
        "movie_id":            int(rec["movieId"]),
        "title":               rec.get("title"),
        "genres":              rec.get("genres"),
        "match_percentage":    rec.get("match_percentage"),
        # recommender scores — present depending on which model was used
        "recommendation_score": rec.get("recommendation_score"),
        "predicted_rating":    rec.get("predicted_rating"),
        "user_score":          rec.get("user_score"),
        "item_score":          rec.get("item_score"),
        "svd_score":           rec.get("svd_score"),
        "hybrid_score":        rec.get("hybrid_score"),
    }
    if movie:
        base.update({
            "release_year": movie.get("release_year"),
            "tmdb_id":      movie.get("tmdb_id"),
            "poster_url":   movie.get("poster_url"),
            "backdrop_url": movie.get("backdrop_url"),
            "overview":     movie.get("overview"),
            "runtime":      movie.get("runtime"),
            "tmdb_rating":  movie.get("tmdb_rating"),
        })
    return base


# ── endpoint ──────────────────────────────────────────────────────────────────

@router.get("/me")
def get_recommendations(
    n: int = 10,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if n < 1 or n > 50:
        raise HTTPException(status_code=400, detail="n must be between 1 and 50")

    user_id = current_user["user_id"]

    # ── 1. Get ML user ID ────────────────────────────────────────────────────
    mapping = db.execute(
        text("SELECT ml_user_id FROM user_ml_mapping WHERE user_id = :uid"),
        {"uid": user_id},
    ).fetchone()
    if not mapping:
        raise HTTPException(status_code=404, detail="ML profile not found for this user.")
    ml_user_id = mapping[0]

    # ── 2. Load user ratings ─────────────────────────────────────────────────
    ratings_rows = db.execute(
        text("SELECT movie_id, rating FROM user_ratings WHERE user_id = :uid"),
        {"uid": user_id},
    ).mappings().all()

    rating_data = [
        {"movieId": int(r["movie_id"]), "rating": float(r["rating"])}
        for r in ratings_rows
    ]
    rated_ids = {r["movieId"] for r in rating_data}

    # ── 3. Load watch history (exclude these from recommendations) ───────────
    history_rows = db.execute(
        text("SELECT DISTINCT movie_id FROM watch_history WHERE user_id = :uid"),
        {"uid": user_id},
    ).mappings().all()
    exclude_ids = list({r["movie_id"] for r in history_rows} | rated_ids)

    # ── 4. Call recommender ──────────────────────────────────────────────────
    try:
        if ml_user_id <= 610:
            # Existing MovieLens user — full hybrid model
            recs_df = get_hybrid_recommendations(
                ml_user_id,
                n=n,
                exclude_movie_ids=exclude_ids,
            )
        else:
            # New app user — fold ratings into latent space
            if not rating_data:
                recs_df = None   # will fall through to popular_movies
            else:
                recs_df = get_new_user_recommendations(
                    rating_data,
                    n=n,
                    exclude_movie_ids=exclude_ids,
                )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    # ── 5. popular_movies fallback ───────────────────────────────────────────
    personalized = True
    if recs_df is None or recs_df.empty:
        personalized = False
        recs_df = popular_movies(n=n, exclude_movie_ids=exclude_ids)

    # ── 6. Enrich with DB metadata ───────────────────────────────────────────
    rec_list   = recs_df.to_dict(orient="records")
    movie_ids  = [int(r["movieId"]) for r in rec_list]
    movie_meta = _fetch_movie_details(db, movie_ids)

    final = [_build_item(rec, movie_meta.get(int(rec["movieId"]))) for rec in rec_list]

    return {
        "user_id":       user_id,
        "ml_user_id":    ml_user_id,
        "personalized":  personalized,
        "count":         len(final),
        "recommendations": final,
    }