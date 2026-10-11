import os
from datetime import datetime, timedelta, timezone

import jwt
import bcrypt
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException, Form, Request
from sqlalchemy import func
from sqlalchemy.orm import Session

from database import get_db
from models import User, UserMLMapping

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

JWT_SECRET        = os.getenv("JWT_SECRET")
JWT_ALGORITHM     = "HS256"
ACCESS_TOKEN_TTL  = timedelta(days=7)   # token expires in 7 days

if not JWT_SECRET:
    raise RuntimeError("JWT_SECRET is not set in backend/.env")

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)

def hash_password(password: str) -> str:
    pwd_bytes = password.encode("utf-8")[:72]
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        pwd_bytes = plain_password.encode("utf-8")[:72]
        hash_bytes = hashed_password.encode("utf-8")
        return bcrypt.checkpw(pwd_bytes, hash_bytes)
    except Exception:
        return False


# ── helpers ───────────────────────────────────────────────────────────────────

def _create_access_token(user_id: int, email: str, username: str) -> str:
    """Create a signed JWT with a fixed expiry."""
    expire = datetime.now(timezone.utc) + ACCESS_TOKEN_TTL
    payload = {
        "user_id":  user_id,
        "email":    email,
        "username": username,
        "exp":      expire,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


# ── REGISTER ──────────────────────────────────────────────────────────────────
@router.post("/register")
async def register(
    request: Request,
    username: str = Form(None),
    email: str    = Form(None),
    password: str = Form(None),
    db: Session   = Depends(get_db),
):
    if not (username and email and password):
        try:
            body = await request.json()
            username = username or body.get("username")
            email = email or body.get("email")
            password = password or body.get("password")
        except Exception:
            pass

    if not (username and email and password):
        raise HTTPException(status_code=422, detail="username, email, and password are required")

    # Check duplicate email
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed_password = hash_password(password)

    new_user = User(
        username=username,
        email=email,
        password_hash=hashed_password,
    )
    db.add(new_user)
    db.flush()  # get new_user.id before ML mapping

    # Assign ML user ID (MovieLens users are 1-610; app users start at 611)
    max_ml_id = db.query(func.max(UserMLMapping.ml_user_id)).scalar()
    new_ml_user_id = max(611, (max_ml_id or 0) + 1)

    db.add(UserMLMapping(user_id=new_user.id, ml_user_id=new_ml_user_id))
    db.commit()
    db.refresh(new_user)

    access_token = _create_access_token(new_user.id, new_user.email, new_user.username)

    return {
        "message":      "User registered successfully",
        "access_token": access_token,
        "token_type":   "bearer",
        "user_id":      new_user.id,
        "ml_user_id":   new_ml_user_id,
        "username":     new_user.username,
        "email":        new_user.email,
    }


# ── LOGIN ─────────────────────────────────────────────────────────────────────
@router.post("/login")
async def login(
    request: Request,
    email: str    = Form(None),
    password: str = Form(None),
    db: Session   = Depends(get_db),
):
    if not (email and password):
        try:
            body = await request.json()
            email = email or body.get("email")
            password = password or body.get("password")
        except Exception:
            pass

    if not (email and password):
        raise HTTPException(status_code=422, detail="email and password are required")

    user = db.query(User).filter(User.email == email).first()

    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    ml_mapping = (
        db.query(UserMLMapping)
        .filter(UserMLMapping.user_id == user.id)
        .first()
    )
    ml_user_id = ml_mapping.ml_user_id if ml_mapping else None

    access_token = _create_access_token(user.id, user.email, user.username)

    return {
        "message":      "Login successful",
        "access_token": access_token,
        "token_type":   "bearer",
        "user_id":      user.id,
        "ml_user_id":   ml_user_id,
        "username":     user.username,
        "email":        user.email,
    }