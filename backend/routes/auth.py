import os
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException, Form, Request, status
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from database import get_db
from models import User, UserMLMapping, EmailVerificationToken
from services.email import send_otp_email

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

JWT_SECRET        = os.getenv("JWT_SECRET")
JWT_ALGORITHM     = "HS256"
ACCESS_TOKEN_TTL  = timedelta(days=7)

OTP_EXPIRY_MINUTES = int(os.getenv("OTP_EXPIRY_MINUTES", "15"))
OTP_MAX_ATTEMPTS   = 5
OTP_RESEND_COOLDOWN_SECONDS = 60   # must wait 60 s before resending

if not JWT_SECRET:
    raise RuntimeError("JWT_SECRET is not set in backend/.env")

router = APIRouter(prefix="/auth", tags=["Authentication"])


# ── password helpers ──────────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    pwd_bytes = password.encode("utf-8")[:72]
    return bcrypt.hashpw(pwd_bytes, bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8")[:72], hashed.encode("utf-8"))
    except Exception:
        return False


# ── OTP helpers ───────────────────────────────────────────────────────────────

def _generate_otp() -> str:
    """Return a 6-digit cryptographically secure OTP string."""
    return str(secrets.randbelow(900_000) + 100_000)


def _hash_otp(otp: str) -> str:
    return bcrypt.hashpw(otp.encode(), bcrypt.gensalt()).decode()


def _check_otp(otp: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(otp.encode(), hashed.encode())
    except Exception:
        return False


# ── JWT ───────────────────────────────────────────────────────────────────────

def _create_access_token(user_id: int, email: str, username: str) -> str:
    expire = datetime.now(timezone.utc) + ACCESS_TOKEN_TTL
    payload = {
        "user_id":  user_id,
        "email":    email,
        "username": username,
        "exp":      expire,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


# ── OTP issuance (shared logic) ───────────────────────────────────────────────

def _issue_otp(db: Session, user: User) -> None:
    """
    Invalidate old tokens, generate a new OTP, hash it, store it, and
    send the verification email.  Raises HTTPException on email failure.
    The plain OTP is never stored — only the bcrypt hash is persisted.
    """
    # Invalidate any existing unused tokens for this user.
    db.execute(
        text(
            "UPDATE email_verification_tokens "
            "SET used = TRUE "
            "WHERE user_id = :uid AND used = FALSE"
        ),
        {"uid": user.id},
    )

    otp = _generate_otp()
    otp_hash = _hash_otp(otp)
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=OTP_EXPIRY_MINUTES)

    token_row = EmailVerificationToken(
        user_id    = user.id,
        otp_hash   = otp_hash,
        expires_at = expires_at,
        used       = False,
        attempts   = 0,
    )
    db.add(token_row)
    db.commit()

    ok = send_otp_email(user.email, otp, user.username)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "Account created but we could not send the verification email. "
                "Please use Resend OTP to try again."
            ),
        )


# ── REGISTER ──────────────────────────────────────────────────────────────────

@router.post("/register")
async def register(
    request: Request,
    username: str = Form(None),
    email:    str = Form(None),
    password: str = Form(None),
    db: Session   = Depends(get_db),
):
    """
    Create a new unverified account and send a 6-digit OTP.
    Does NOT return an access token — the user must verify email first.
    If called with an email that already has an unverified account,
    a new OTP is resent (subject to the 60-second cooldown).
    """
    # Accept JSON or form data
    if not (username and email and password):
        try:
            body = await request.json()
            username = username or body.get("username")
            email    = email    or body.get("email")
            password = password or body.get("password")
        except Exception:
            pass

    if not (username and email and password):
        raise HTTPException(status_code=422, detail="username, email, and password are required")

    email = email.strip().lower()

    existing = db.query(User).filter(User.email == email).first()

    if existing:
        if existing.is_verified:
            raise HTTPException(status_code=400, detail="Email already registered")

        # Unverified account exists — check cooldown before resending
        last_token = (
            db.query(EmailVerificationToken)
            .filter(
                EmailVerificationToken.user_id == existing.id,
                EmailVerificationToken.used == False,
            )
            .order_by(EmailVerificationToken.created_at.desc())
            .first()
        )
        if last_token:
            elapsed = (
                datetime.now(timezone.utc) - last_token.created_at.replace(tzinfo=timezone.utc)
            ).total_seconds()
            if elapsed < OTP_RESEND_COOLDOWN_SECONDS:
                wait = int(OTP_RESEND_COOLDOWN_SECONDS - elapsed)
                raise HTTPException(
                    status_code=429,
                    detail=f"Please wait {wait} seconds before requesting a new OTP.",
                )

        _issue_otp(db, existing)
        return {
            "message":          "Verification OTP resent. Please check your email.",
            "email":            email,
            "needs_verification": True,
        }

    # New registration
    hashed_password = hash_password(password)
    new_user = User(
        username      = username.strip(),
        email         = email,
        password_hash = hashed_password,
        is_verified   = False,
    )
    db.add(new_user)
    db.flush()   # get new_user.id

    # Assign ML user ID (MovieLens users are 1-610; app users start at 611)
    max_ml_id = db.query(func.max(UserMLMapping.ml_user_id)).scalar()
    new_ml_user_id = max(611, (max_ml_id or 0) + 1)
    db.add(UserMLMapping(user_id=new_user.id, ml_user_id=new_ml_user_id))
    db.commit()
    db.refresh(new_user)

    _issue_otp(db, new_user)

    return {
        "message":          "Account created. Please check your email for the verification code.",
        "email":            email,
        "needs_verification": True,
    }


# ── LOGIN ─────────────────────────────────────────────────────────────────────

@router.post("/login")
async def login(
    request: Request,
    email:    str = Form(None),
    password: str = Form(None),
    db: Session   = Depends(get_db),
):
    if not (email and password):
        try:
            body = await request.json()
            email    = email    or body.get("email")
            password = password or body.get("password")
        except Exception:
            pass

    if not (email and password):
        raise HTTPException(status_code=422, detail="email and password are required")

    email = email.strip().lower()
    user  = db.query(User).filter(User.email == email).first()

    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not user.is_verified:
        raise HTTPException(
            status_code=403,
            detail="email_not_verified",
            headers={"X-Email": email},
        )

    ml_mapping = (
        db.query(UserMLMapping)
        .filter(UserMLMapping.user_id == user.id)
        .first()
    )
    ml_user_id  = ml_mapping.ml_user_id if ml_mapping else None
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