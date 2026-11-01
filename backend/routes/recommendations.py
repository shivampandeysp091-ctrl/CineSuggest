"""
routes/recommendations.py
--------------------------
GET /recommendations/me   — personalized recommendations for the logged-in user.

Flow:
  1. JWT se user_id lo  (deps.get_current_user)
  2. user_ml_mapping  se ml_user_id lo
  3. user_ratings     se rated movie ids aur ratings lo
  4. Only rated movies are excluded from candidates (watch history is separate).
  5. Recommender call:
       ml_user_id <= 610  → get_hybrid_recommendations (known MovieLens user)
       ml_user_id >  610  → Collaborative Filtering Hybrid (Item-Based CF + User-Based CF + SVD)
  6. movies table se poster_url, overview jodo
  7. Empty result / cold start → popular_movies fallback ("personalized": false)
"""

import os
import math
import numpy as np
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from database import get_db
from deps import get_current_user
from ml.recommender import (
    _load,
    _match,
    _profile_from_ratings,
    _svd,
    _user_based,
    get_hybrid_recommendations,
    popular_movies,
)

router = APIRouter(
    prefix="/recommendations",
    tags=["Recommendations"],
)


# ── helpers ───────────────────────────────────────────────────────────────────

def _clean_float(val, decimals: int = 2) -> float | None:
    """Ensure floating-point values are JSON compliant (no NaN or Inf)."""
    if val is None:
        return None
    try:
        f = float(val)
        if math.isnan(f) or math.isinf(f):
            return None
        return round(f, decimals)
    except (TypeError, ValueError):
        return None


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


K_RRF = 60
CANDIDATE_DEPTH = 50
DEFAULT_ALGORITHM = os.environ.get("RECOMMENDER_ALGORITHM", "rrf").lower()


def _build_item(rec: dict, movie: dict | None) -> dict:
    """Merge a recommender row with DB movie details into one response item."""
    base = {
        "movie_id":            int(rec["movieId"]),
        "title":               rec.get("title"),
        "genres":              rec.get("genres"),
        "match_percentage":    _clean_float(rec.get("match_percentage"), 1),
        "recommendation_score": _clean_float(rec.get("match_percentage"), 1),
        "predicted_rating":    _clean_float(rec.get("predicted_rating"), 2),
        "user_score":          _clean_float(rec.get("user_score"), 2),
        "item_score":          _clean_float(rec.get("item_score"), 2),
        "svd_score":           _clean_float(rec.get("svd_score"), 2),
        "hybrid_score":        _clean_float(rec.get("hybrid_score"), 2),
        "rrf_score":           _clean_float(rec.get("rrf_score"), 4),
    }
    if movie:
        base.update({
            "release_year": movie.get("release_year"),
            "tmdb_id":      movie.get("tmdb_id"),
            "poster_url":   movie.get("poster_url"),
            "backdrop_url": movie.get("backdrop_url"),
            "overview":     movie.get("overview"),
            "runtime":      movie.get("runtime"),
            "tmdb_rating":  _clean_float(movie.get("tmdb_rating"), 1),
        })
    return base


def _recommend_new_user_cf(
    rating_data: list[dict],
    n: int = 10,
    exclude_ids: list[int] | None = None,
    algorithm: str | None = None,
) -> tuple[pd.DataFrame | None, bool]:
    """
    Pure collaborative filtering recommendation pipeline for app users.
    Supports:
      - RRF (Reciprocal Rank Fusion of User CF, Item CF, and SVD with k=60, candidate depth=50) [DEFAULT]
      - Hybrid CF (component score-weighted blend) [ROLLBACK / BENCHMARK OPTION]
    Strictly forbids content-based matching, text/metadata matching, or fake scores.
    Requires positive collaborative connection so SVD global bias cannot hijack recommendations.
    """
    selected_alg = (algorithm or DEFAULT_ALGORITHM).lower()
    S = _load()
    p = _profile_from_ratings(S, rating_data)
    if p is None:
        return None, False

    exclude_set = set(exclude_ids or [])
    rated_idx = np.where(p["rated"])[0]
    if len(rated_idx) == 0:
        return None, False

    # ── 1. Item-Based Collaborative Filtering ─────────────────────────────────
    Rc = S["Rc"]
    item_norm = S["item_norm"]
    raw_sims = (Rc[:, rated_idx].T @ Rc) / (item_norm[rated_idx][:, None] * item_norm[None, :] + 1e-9)
    pos_sims = np.maximum(0, raw_sims)
    sim_sum = pos_sims.sum(axis=0)

    # Collaborative shrinkage prevents tiny/spurious similarities from causing flat 5.0 ratings
    shrinkage = 0.5
    rc_rated = p["rc"][rated_idx]
    weighted_dev = pos_sims.T @ rc_rated
    item_score = np.where(sim_sum > 0, p["mean"] + weighted_dev / (sim_sum + shrinkage), np.nan)

    # ── 2. User-Based Collaborative Filtering ─────────────────────────────────
    u_score = _user_based(S, p)
    has_user_cf = (~np.isnan(u_score)).any()

    # ── 3. SVD Collaborative Filtering ───────────────────────────────────────
    svd_score = _svd(S, p)

    # ── 4. Collaborative Evidence & Personalization Gate ──────────────────────
    profile_counts = S["counts"][rated_idx]
    has_anchor = bool((profile_counts >= 10).any() or (profile_counts.sum() >= 15))

    if not has_anchor and not has_user_cf:
        # Insufficient collaborative evidence -> honest cold-start fallback
        return None, False

    n_rated = len(rated_idx)
    min_sim = 0.25 if n_rated <= 3 else 0.15
    has_collab = (~np.isnan(u_score)) | (sim_sum >= min_sim)
    if not has_collab.any():
        return None, False

    # Component rating blend (for honest predicted rating / match percentage estimation)
    if n_rated <= 3:
        weights = (0.20, 0.60, 0.20)  # (User, Item, SVD)
    else:
        weights = (0.30, 0.40, 0.30)

    preds = np.column_stack([u_score, item_score, svd_score])
    w = np.asarray(weights, dtype=float)[None, :] * ~np.isnan(preds)
    tw = w.sum(axis=1)
    hybrid_score = np.where(has_collab & (tw > 0), (np.nan_to_num(preds) * w).sum(axis=1) / tw, np.nan)

    # Candidate eligibility mask:
    # 1. MovieLens review count >= 10
    # 2. Not already rated by user
    # 3. Not in exclude_set
    base_eligible = (S["counts"] >= 10) & (~p["rated"])
    for mid in exclude_set:
        j = S["col_index"].get(int(mid))
        if j is not None:
            base_eligible[j] = False

    # ── 5. Candidate Ranking Generation (RRF vs Hybrid CF) ───────────────────
    rrf_score_map: dict[int, float] = {}

    if selected_alg == "hybrid":
        # Classic score-weighted hybrid ranking
        valid = np.where(~np.isnan(hybrid_score) & base_eligible)[0]
        if len(valid) == 0:
            return None, False
        top_idx = sorted(valid, key=lambda j: hybrid_score[j], reverse=True)[:n]
    else:
        # Reciprocal Rank Fusion (RRF) with k=60, component depth=50
        def _rank_component_candidates(scores_arr, top_k=CANDIDATE_DEPTH):
            # Must be base eligible, possess positive collaborative affinity, and finite score
            cand_mask = base_eligible & has_collab & (~np.isnan(scores_arr)) & np.isfinite(scores_arr)
            cand_j = np.where(cand_mask)[0]
            if len(cand_j) == 0:
                return []
            cand_scores = scores_arr[cand_j]
            top_local = np.argsort(-cand_scores)[:top_k]
            return cand_j[top_local].tolist()

        list_ub = _rank_component_candidates(u_score)
        list_ib = _rank_component_candidates(item_score)
        list_svd = _rank_component_candidates(svd_score)

        comp_weights = (0.20, 0.60, 0.20) if n_rated <= 3 else (1.0, 1.0, 1.0)
        for w_c, cand_list in zip(comp_weights, (list_ub, list_ib, list_svd)):
            for rank_idx, j in enumerate(cand_list, 1):
                rrf_score_map[j] = rrf_score_map.get(j, 0.0) + w_c * (1.0 / (K_RRF + rank_idx))

        if not rrf_score_map:
            return None, False

        # Deterministic tie-breaking:
        # (rrf_score DESC, S["counts"] DESC, movieId ASC)
        sorted_cands = sorted(
            rrf_score_map.items(),
            key=lambda x: (x[1], S["counts"][x[0]], -int(S["movie_ids"][x[0]])),
            reverse=True,
        )
        top_idx = [j for j, _ in sorted_cands[:n]]

    df_movies = S["movies"].drop_duplicates("movieId").set_index("movieId")
    rows = []
    for j in top_idx:
        mid = int(S["movie_ids"][j])
        sc = hybrid_score[j]
        pred_rating = round(float(sc), 2) if not np.isnan(sc) else None
        match_pct = float(_match(sc)) if not np.isnan(sc) else None
        rrf_val = round(float(rrf_score_map[j]), 4) if j in rrf_score_map else None

        rows.append({
            "movieId": mid,
            "title": df_movies.loc[mid, "title"] if mid in df_movies.index else "Unknown",
            "genres": df_movies.loc[mid, "genres"] if mid in df_movies.index else "",
            "predicted_rating": pred_rating,
            "match_percentage": match_pct,
            "recommendation_score": match_pct,
            "user_score": round(float(u_score[j]), 2) if not np.isnan(u_score[j]) else None,
            "item_score": round(float(item_score[j]), 2) if not np.isnan(item_score[j]) else None,
            "svd_score": round(float(svd_score[j]), 2) if not np.isnan(svd_score[j]) else None,
            "hybrid_score": pred_rating,
            "rrf_score": rrf_val,
        })

    return pd.DataFrame(rows), True


# ── endpoint ──────────────────────────────────────────────────────────────────

@router.get("/me")
def get_recommendations(
    n: int = 10,
    algorithm: str | None = None,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if n < 1 or n > 50:
        raise HTTPException(status_code=400, detail="n must be between 1 and 50")
    if algorithm is not None and algorithm.lower() not in ("rrf", "hybrid"):
        raise HTTPException(status_code=400, detail="algorithm must be 'rrf' or 'hybrid'")

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

    # ── 3. Exclude only already-rated movies from recommendations ────────────
    # Watch history is NOT used as an exclusion filter.
    # Viewing a movie ≠ rating it. Only explicit star ratings are excluded.
    ml_rated_ids = {mid for mid in rated_ids if mid < 1_000_000}
    exclude_ids  = list(ml_rated_ids)

    # ── 4. Call recommender ──────────────────────────────────────────────────
    # Only pass ML-catalog movie ratings to the CF model.
    # TMDB-imported movies (id >= 1,000,000) are NOT in MovieLens training data.
    ml_rating_data = [r for r in rating_data if r["movieId"] < 1_000_000]

    try:
        if ml_user_id <= 610:
            # Existing MovieLens user — full hybrid model
            recs_df = get_hybrid_recommendations(
                ml_user_id,
                n=n,
                exclude_movie_ids=exclude_ids,
            )
            personalized = recs_df is not None and not recs_df.empty
        else:
            # App user (ml_user_id > 610) — pure collaborative filtering
            if not ml_rating_data:
                recs_df = None
                personalized = False
            else:
                recs_df, personalized = _recommend_new_user_cf(
                    ml_rating_data,
                    n=n,
                    exclude_ids=exclude_ids,
                    algorithm=algorithm,
                )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    # ── 5. Honest Cold-Start Fallback ─────────────────────────────────────────
    # If collaborative data is insufficient or user has 0 ratings, show popular movies
    # with personalized: false and NO fake match percentages.
    if recs_df is None or recs_df.empty:
        personalized = False
        recs_df = popular_movies(n=n, exclude_movie_ids=exclude_ids)
        # Clear match_percentage so unpersonalized fallback is honest
        if not recs_df.empty and "match_percentage" in recs_df.columns:
            recs_df["match_percentage"] = None

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