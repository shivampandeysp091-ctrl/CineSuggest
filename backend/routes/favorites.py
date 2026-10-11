from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text

from database import engine
from deps import get_current_user

router = APIRouter(
    prefix="/favorites",
    tags=["Favorites"],
)


class FavoriteRequest(BaseModel):
    movie_id: int


# ── POST /favorites/  ─────────────────────────────────────────────────────────
@router.post("/")
def add_favorite(
    data: FavoriteRequest,
    current_user: dict = Depends(get_current_user),
):
    user_id = current_user["user_id"]

    with engine.begin() as conn:
        if not conn.execute(
            text("SELECT movie_id FROM movies WHERE movie_id = :mid"),
            {"mid": data.movie_id},
        ).fetchone():
            raise HTTPException(status_code=404, detail="Movie not found")

        if conn.execute(
            text("SELECT id FROM favorites WHERE user_id = :uid AND movie_id = :mid"),
            {"uid": user_id, "mid": data.movie_id},
        ).fetchone():
            raise HTTPException(status_code=400, detail="Movie is already in favorites")

        conn.execute(
            text("INSERT INTO favorites (user_id, movie_id) VALUES (:uid, :mid)"),
            {"uid": user_id, "mid": data.movie_id},
        )
        return {"message": "Movie added to favorites", "user_id": user_id, "movie_id": data.movie_id}


# ── GET /favorites/me  ────────────────────────────────────────────────────────
@router.get("/me")
def get_my_favorites(current_user: dict = Depends(get_current_user)):
    user_id = current_user["user_id"]
    with engine.connect() as conn:
        favorites = conn.execute(
            text("""
                SELECT f.id, f.user_id, f.movie_id, m.title, m.genres, m.poster_url, f.created_at
                FROM favorites f
                JOIN movies m ON f.movie_id = m.movie_id
                WHERE f.user_id = :uid
                ORDER BY f.created_at DESC
            """),
            {"uid": user_id},
        ).mappings().all()
        return {"user_id": user_id, "favorites": favorites}


# ── GET /favorites/check/{movie_id}  ─────────────────────────────────────────
@router.get("/check/{movie_id}")
def check_favorite(
    movie_id: int,
    current_user: dict = Depends(get_current_user),
):
    user_id = current_user["user_id"]
    with engine.connect() as conn:
        found = conn.execute(
            text("SELECT id FROM favorites WHERE user_id = :uid AND movie_id = :mid"),
            {"uid": user_id, "mid": movie_id},
        ).fetchone()
        return {"user_id": user_id, "movie_id": movie_id, "is_favorite": bool(found)}


# ── DELETE /favorites/{movie_id}  ────────────────────────────────────────────
@router.delete("/{movie_id}")
def delete_favorite(
    movie_id: int,
    current_user: dict = Depends(get_current_user),
):
    user_id = current_user["user_id"]
    with engine.begin() as conn:
        existing = conn.execute(
            text("SELECT id FROM favorites WHERE user_id = :uid AND movie_id = :mid"),
            {"uid": user_id, "mid": movie_id},
        ).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Favorite not found")

        conn.execute(
            text("DELETE FROM favorites WHERE user_id = :uid AND movie_id = :mid"),
            {"uid": user_id, "mid": movie_id},
        )
        return {"message": "Movie removed from favorites", "user_id": user_id, "movie_id": movie_id}