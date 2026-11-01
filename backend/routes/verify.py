"""
routes/verify.py
----------------
POST /auth/verify-otp  — verify 6-digit OTP, mark account verified, return JWT
POST /auth/resend-otp  — resend OTP with 60-second cooldown
"""
import os
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models import User, UserMLMapping, EmailVerificationToken
from routes.auth import (
    OTP_MAX_ATTEMPTS,
    OTP_RESEND_COOLDOWN_SECONDS,
    _check_otp,
    _create_access_token,
    _issue_otp,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


# ── request schemas ───────────────────────────────────────────────────────────

class VerifyOtpRequest(BaseModel):
    email: str
    otp:   str   # 6-digit code entered by user


class ResendOtpRequest(BaseModel):
    email: str


# ── POST /auth/verify-otp ─────────────────────────────────────────────────────

@router.post("/verify-otp")
def verify_otp(data: VerifyOtpRequest, db: Session = Depends(get_db)):
    """
    Verify the 6-digit OTP.  On success: mark account verified, return JWT.
    Rejects expired tokens, used tokens, and tokens with >= 5 failed attempts.
    Every wrong guess increments the attempt counter without revealing the hash.
    """
    email = data.email.strip().lower()
    otp   = data.otp.strip()

    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Account not found")

    if user.is_verified:
        # Already verified — just issue a token (idempotent re-verify)
        ml_mapping  = db.query(UserMLMapping).filter(UserMLMapping.user_id == user.id).first()
        access_token = _create_access_token(user.id, user.email, user.username)
        return {
            "message":      "Email already verified",
            "access_token": access_token,
            "token_type":   "bearer",
            "user_id":      user.id,
            "ml_user_id":   ml_mapping.ml_user_id if ml_mapping else None,
            "username":     user.username,
            "email":        user.email,
        }

    # Find the latest unused, unexpired token
    now = datetime.now(timezone.utc)
    token_row = (
        db.query(EmailVerificationToken)
        .filter(
            EmailVerificationToken.user_id   == user.id,
            EmailVerificationToken.used      == False,
            EmailVerificationToken.expires_at > now,
        )
        .order_by(EmailVerificationToken.created_at.desc())
        .first()
    )

    if not token_row:
        raise HTTPException(
            status_code=400,
            detail="OTP has expired or does not exist. Please request a new one.",
        )

    if token_row.attempts >= OTP_MAX_ATTEMPTS:
        raise HTTPException(
            status_code=429,
            detail="Too many failed attempts. Please request a new OTP.",
        )

    if not _check_otp(otp, token_row.otp_hash):
        token_row.attempts += 1
        db.commit()
        remaining = OTP_MAX_ATTEMPTS - token_row.attempts
        raise HTTPException(
            status_code=400,
            detail=f"Incorrect OTP. {remaining} attempt(s) remaining.",
        )

    # OTP is correct — mark token used and activate account
    token_row.used      = True
    user.is_verified    = True
    db.commit()

    ml_mapping   = db.query(UserMLMapping).filter(UserMLMapping.user_id == user.id).first()
    access_token = _create_access_token(user.id, user.email, user.username)

    return {
        "message":      "Email verified successfully",
        "access_token": access_token,
        "token_type":   "bearer",
        "user_id":      user.id,
        "ml_user_id":   ml_mapping.ml_user_id if ml_mapping else None,
        "username":     user.username,
        "email":        user.email,
    }


# ── POST /auth/resend-otp ─────────────────────────────────────────────────────

@router.post("/resend-otp")
def resend_otp(data: ResendOtpRequest, db: Session = Depends(get_db)):
    """
    Resend OTP for an unverified account.
    Enforces a 60-second cooldown between sends.
    """
    email = data.email.strip().lower()
    user  = db.query(User).filter(User.email == email).first()

    if not user:
        # Respond identically to prevent email enumeration
        raise HTTPException(
            status_code=200,
            detail="If that email is registered, a new OTP has been sent.",
        )

    if user.is_verified:
        raise HTTPException(status_code=400, detail="This account is already verified.")

    # Cooldown check
    now = datetime.now(timezone.utc)
    last_token = (
        db.query(EmailVerificationToken)
        .filter(
            EmailVerificationToken.user_id == user.id,
            EmailVerificationToken.used    == False,
        )
        .order_by(EmailVerificationToken.created_at.desc())
        .first()
    )
    if last_token:
        created_utc = last_token.created_at
        if created_utc.tzinfo is None:
            created_utc = created_utc.replace(tzinfo=timezone.utc)
        elapsed = (now - created_utc).total_seconds()
        if elapsed < OTP_RESEND_COOLDOWN_SECONDS:
            wait = int(OTP_RESEND_COOLDOWN_SECONDS - elapsed)
            raise HTTPException(
                status_code=429,
                detail=f"Please wait {wait} seconds before requesting another OTP.",
            )

    _issue_otp(db, user)

    return {"message": "A new verification code has been sent to your email."}
