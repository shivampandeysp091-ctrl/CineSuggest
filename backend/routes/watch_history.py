from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text

from database import engine
from deps import get_current_user

router = APIRouter(
    prefix="/watch-history",
    tags=["Watch History"],
)


class WatchHistoryRequest(BaseModel):
    movie_id: int


# ── POST /watch-history/  ────────────────────────────────────────────────────
@router.post("/")
def add_watch_history(
    data: WatchHistoryRequest,
    current_user: dict = Depends(get_current_user),
):
    user_id = current_user["user_id"]

    with engine.begin() as conn:
        if not conn.execute(
            text("SELECT movie_id FROM movies WHERE movie_id = :mid"),
            {"mid": data.movie_id},
        ).fetchone():
            raise HTTPException(status_code=404, detail="Movie not found")

        existing = conn.execute(
            text("SELECT id FROM watch_history WHERE user_id = :uid AND movie_id = :mid"),
            {"uid": user_id, "mid": data.movie_id},
        ).fetchone()

        if existing:
            conn.execute(
                text("UPDATE watch_history SET watched_at = NOW() WHERE id = :id"),
                {"id": existing[0]},
            )
            message = "Watch history timestamp updated"
        else:
            conn.execute(
                text("INSERT INTO watch_history (user_id, movie_id, watched_at) VALUES (:uid, :mid, NOW())"),
                {"uid": user_id, "mid": data.movie_id},
            )
            message = "Movie added to watch history"

        return {"message": message, "user_id": user_id, "movie_id": data.movie_id}


# ── GET /watch-history/me  ───────────────────────────────────────────────────
@router.get("/me")
def get_my_watch_history(current_user: dict = Depends(get_current_user)):
    user_id = current_user["user_id"]
    with engine.connect() as conn:
        history = conn.execute(
            text("""
                SELECT
                    latest.max_id   AS id,
                    latest.user_id,
                    latest.movie_id,
                    m.title,
                    m.genres,
                    m.poster_url,
                    latest.max_watched AS watched_at
                FROM (
                    SELECT
                        user_id,
                        movie_id,
                        MAX(id)         AS max_id,
                        MAX(watched_at) AS max_watched
                    FROM watch_history
                    WHERE user_id = :uid
                    GROUP BY user_id, movie_id
                ) latest
                JOIN movies m ON latest.movie_id = m.movie_id
                ORDER BY latest.max_watched DESC
            """),
            {"uid": user_id},
        ).mappings().all()
        return {"user_id": user_id, "watch_history": history}


# ── DELETE /watch-history/{movie_id}  ────────────────────────────────────────
@router.delete("/{movie_id}")
def delete_watch_history(
    movie_id: int,
    current_user: dict = Depends(get_current_user),
):
    user_id = current_user["user_id"]
    with engine.begin() as conn:
        existing = conn.execute(
            text("SELECT id FROM watch_history WHERE user_id = :uid AND movie_id = :mid"),
            {"uid": user_id, "mid": movie_id},
        ).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Watch history not found")

        conn.execute(
            text("DELETE FROM watch_history WHERE user_id = :uid AND movie_id = :mid"),
            {"uid": user_id, "mid": movie_id},
        )
        return {"message": "Movie removed from watch history", "user_id": user_id, "movie_id": movie_id}