"""
tests/test_auth.py
------------------
Fast, offline unit tests for JWT logic in deps.py and routes/auth.py.
No database connection required — only PyJWT and passlib are used.

Run from backend/ directory:
    python -m pytest tests/test_auth.py -v
"""

import os
import sys
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

# Add backend/ to path so imports work from tests/
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Inject a dummy secret before deps.py reads env
os.environ.setdefault("JWT_SECRET", "test-secret-key-for-unit-tests")
os.environ.setdefault("DATABASE_URL", "postgresql+psycopg2://dummy/dummy")

import deps  # noqa: E402

SECRET    = os.environ["JWT_SECRET"]
ALGORITHM = deps.JWT_ALGORITHM


# ── helpers ───────────────────────────────────────────────────────────────────

def make_token(payload: dict) -> str:
    return jwt.encode(payload, SECRET, algorithm=ALGORITHM)


def call_dep(token: str) -> dict:
    """Call the get_current_user dependency directly."""
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    return deps.get_current_user(creds)


# ── tests ─────────────────────────────────────────────────────────────────────

class TestGetCurrentUser:

    def test_valid_token_returns_payload(self):
        payload = {
            "user_id":  42,
            "email":    "alice@example.com",
            "username": "alice",
            "exp":      datetime.now(timezone.utc) + timedelta(hours=1),
        }
        token = make_token(payload)
        result = call_dep(token)

        assert result["user_id"] == 42
        assert result["email"] == "alice@example.com"
        assert result["username"] == "alice"

    def test_expired_token_raises_401(self):
        payload = {
            "user_id": 1,
            "exp": datetime.now(timezone.utc) - timedelta(seconds=1),  # already expired
        }
        token = make_token(payload)

        with pytest.raises(HTTPException) as exc_info:
            call_dep(token)

        assert exc_info.value.status_code == 401
        assert "expired" in exc_info.value.detail.lower()

    def test_invalid_signature_raises_401(self):
        payload = {
            "user_id": 1,
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        }
        bad_token = jwt.encode(payload, "wrong-secret", algorithm=ALGORITHM)

        with pytest.raises(HTTPException) as exc_info:
            call_dep(bad_token)

        assert exc_info.value.status_code == 401
        assert "invalid" in exc_info.value.detail.lower()

    def test_token_missing_user_id_raises_401(self):
        payload = {
            "email": "ghost@example.com",
            "exp":   datetime.now(timezone.utc) + timedelta(hours=1),
            # no user_id
        }
        token = make_token(payload)

        with pytest.raises(HTTPException) as exc_info:
            call_dep(token)

        assert exc_info.value.status_code == 401
        assert "user_id" in exc_info.value.detail.lower()

    def test_garbage_token_raises_401(self):
        with pytest.raises(HTTPException) as exc_info:
            call_dep("not.a.real.token")

        assert exc_info.value.status_code == 401

    def test_different_users_get_different_ids(self):
        def tok(uid):
            return make_token({
                "user_id": uid,
                "exp": datetime.now(timezone.utc) + timedelta(hours=1),
            })

        assert call_dep(tok(1))["user_id"] == 1
        assert call_dep(tok(99))["user_id"] == 99
        assert call_dep(tok(1))["user_id"] != call_dep(tok(99))["user_id"]
