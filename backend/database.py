import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import NullPool

# Load environment variables from backend/.env
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set. Please add it to backend/.env")

# SQLAlchemy 2.x defaults to psycopg (v3) for "postgresql://".
# Force psycopg2-binary by normalising the scheme.
# NOTE: check the longer prefix first to avoid partial replacement.
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = "postgresql+psycopg2://" + DATABASE_URL[len("postgresql://"):]
elif DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = "postgresql+psycopg2://" + DATABASE_URL[len("postgres://"):]

# Supabase transaction pooler (port 6543) or explicit env flag → NullPool
# NullPool is required for serverless environments (Vercel) where connections
# cannot be held open between requests.
_use_null_pool = (
    ":6543/" in DATABASE_URL
    or os.getenv("DB_NULLPOOL", "0") == "1"
)

engine = create_engine(
    DATABASE_URL,
    echo=False,
    poolclass=NullPool if _use_null_pool else None,
    **({} if _use_null_pool else {"pool_pre_ping": True}),
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()