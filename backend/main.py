from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import engine, Base
from ml.recommender import warmup as recommender_warmup

from routes.movies import router as movies_router
from routes.auth import router as auth_router
from routes.ratings import router as ratings_router
from routes.favorites import router as favorites_router
from routes.watch_history import router as watch_history_router
from routes.recommendations import router as recommendations_router
from routes.verify import router as verify_router


import os

# Import all models so Base knows about them before create_all
import models  # noqa: F401


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: optionally create tables (set CREATE_TABLES=1), then warm up ML."""
    if os.getenv("CREATE_TABLES", "0") == "1":
        Base.metadata.create_all(bind=engine)
    recommender_warmup()   # pre-load ML matrices so first request isn't slow
    yield


app = FastAPI(
    title="CineMatch-AI API",
    description="Movie Recommendation Engine Backend",
    version="1.0.0",
    lifespan=lifespan,
)


# Allow React frontend (local and explicit FRONTEND_URL) to communicate with FastAPI.
# Vercel.app wildcard is intentionally excluded — set FRONTEND_URL env var instead.
allowed_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
]
frontend_url = os.getenv("FRONTEND_URL")
if frontend_url:
    allowed_origins.append(frontend_url)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def home():
    return {
        "message": "CineMatch-AI API is running!"
    }


@app.get("/health")
def health():
    try:
        with engine.connect():
            return {
                "status": "OK",
                "database": "PostgreSQL connected successfully"
            }
    except Exception as e:
        return {
            "status": "ERROR",
            "database": "PostgreSQL connection failed",
            "error": str(e)
        }


app.include_router(movies_router)
app.include_router(auth_router)
app.include_router(ratings_router)
app.include_router(favorites_router)
app.include_router(watch_history_router)
app.include_router(recommendations_router)
app.include_router(verify_router)
