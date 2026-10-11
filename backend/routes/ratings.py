from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text

from database import engine
from deps import get_current_user

router = APIRouter(
    prefix="/ratings",
    tags=["Ratings"],
)


class RatingRequest(BaseModel):
    movie_id: int
    rating: float


# ── POST /ratings/  ───────────────────────────────────────────────────────────
@router.post("/")
def add_rating(
    data: RatingRequest,
    current_user: dict = Depends(get_current_user),
):
    user_id = current_user["user_id"]

    if data.rating < 0.5 or data.rating > 5.0:
        raise HTTPException(status_code=400, detail="Rating must be between 0.5 and 5.0")

    with engine.begin() as conn:
        movie = conn.execute(
            text("SELECT movie_id FROM movies WHERE movie_id = :movie_id"),
            {"movie_id": data.movie_id},
        ).fetchone()
        if not movie:
            raise HTTPException(status_code=404, detail="Movie not found")

        existing = conn.execute(
            text("SELECT id FROM user_ratings WHERE user_id = :uid AND movie_id = :mid"),
            {"uid": user_id, "mid": data.movie_id},
        ).fetchone()

        if existing:
            conn.execute(
                text("""
                    UPDATE user_ratings
                    SET rating = :rating, rated_at = CURRENT_TIMESTAMP
                    WHERE user_id = :uid AND movie_id = :mid
                """),
                {"rating": data.rating, "uid": user_id, "mid": data.movie_id},
            )
            return {"message": "Rating updated successfully", "user_id": user_id,
                    "movie_id": data.movie_id, "rating": data.rating}

        conn.execute(
            text("INSERT INTO user_ratings (user_id, movie_id, rating) VALUES (:uid, :mid, :rating)"),
            {"uid": user_id, "mid": data.movie_id, "rating": data.rating},
        )
        return {"message": "Rating added successfully", "user_id": user_id,
                "movie_id": data.movie_id, "rating": data.rating}


# ── GET /ratings/me  ──────────────────────────────────────────────────────────
@router.get("/me")
def get_my_ratings(current_user: dict = Depends(get_current_user)):
    user_id = current_user["user_id"]
    with engine.connect() as conn:
        ratings = conn.execute(
            text("""
                SELECT ur.id, ur.user_id, ur.movie_id, m.title, ur.rating, ur.rated_at
                FROM user_ratings ur
                JOIN movies m ON ur.movie_id = m.movie_id
                WHERE ur.user_id = :uid
                ORDER BY ur.rated_at DESC
            """),
            {"uid": user_id},
        ).mappings().all()
        return {"user_id": user_id, "ratings": ratings}


# ── PUT /ratings/{movie_id}  ──────────────────────────────────────────────────
@router.put("/{movie_id}")
def update_rating(
    movie_id: int,
    rating: float,
    current_user: dict = Depends(get_current_user),
):
    user_id = current_user["user_id"]

    if rating < 0.5 or rating > 5.0:
        raise HTTPException(status_code=400, detail="Rating must be between 0.5 and 5.0")

    with engine.begin() as conn:
        existing = conn.execute(
            text("SELECT id FROM user_ratings WHERE user_id = :uid AND movie_id = :mid"),
            {"uid": user_id, "mid": movie_id},
        ).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Rating not found")

        conn.execute(
            text("""
                UPDATE user_ratings
                SET rating = :rating, rated_at = CURRENT_TIMESTAMP
                WHERE user_id = :uid AND movie_id = :mid
            """),
            {"rating": rating, "uid": user_id, "mid": movie_id},
        )
        return {"message": "Rating updated successfully", "user_id": user_id,
                "movie_id": movie_id, "rating": rating}


# ── DELETE /ratings/{movie_id}  ───────────────────────────────────────────────
@router.delete("/{movie_id}")
def delete_rating(
    movie_id: int,
    current_user: dict = Depends(get_current_user),
):
    user_id = current_user["user_id"]
    with engine.begin() as conn:
        existing = conn.execute(
            text("SELECT id FROM user_ratings WHERE user_id = :uid AND movie_id = :mid"),
            {"uid": user_id, "mid": movie_id},
        ).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Rating not found")

        conn.execute(
            text("DELETE FROM user_ratings WHERE user_id = :uid AND movie_id = :mid"),
            {"uid": user_id, "mid": movie_id},
        )
        return {"message": "Rating deleted successfully", "user_id": user_id, "movie_id": movie_id}