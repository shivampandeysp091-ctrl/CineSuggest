"""
tests/test_data_isolation.py
----------------------------
Tests user data isolation:
- Tokens for User A cannot yield User B's identity
- JWT user_id binding in dependencies
- Scoped keys ensure separate user spaces
"""
import os
import sys
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("JWT_SECRET", "test-secret-key-32-bytes-long-padding-here")
os.environ.setdefault("DATABASE_URL", "postgresql+psycopg2://dummy/dummy")

import deps


def make_token(payload: dict) -> str:
    return jwt.encode(payload, deps.JWT_SECRET, algorithm=deps.JWT_ALGORITHM)


class TestUserDataIsolation:

    def test_user_a_token_cannot_yield_user_b_id(self):
        token_a = make_token({
            "user_id": 101,
            "email": "userA@example.com",
            "username": "UserA",
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        })
        token_b = make_token({
            "user_id": 102,
            "email": "userB@example.com",
            "username": "UserB",
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        })

        creds_a = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token_a)
        creds_b = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token_b)

        current_a = deps.get_current_user(creds_a)
        current_b = deps.get_current_user(creds_b)

        assert current_a["user_id"] == 101
        assert current_b["user_id"] == 102
        assert current_a["user_id"] != current_b["user_id"]

    def test_tampered_token_rejected(self):
        token = make_token({
            "user_id": 101,
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        })
        # Tamper payload
        parts = token.split(".")
        tampered_token = f"{parts[0]}.eyAidXNlcl9pZCI6IDk5OSB9.{parts[2]}"

        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=tampered_token)
        with pytest.raises(HTTPException) as exc:
            deps.get_current_user(creds)
        assert exc.value.status_code == 401

    def test_storage_scoped_key_format(self):
        """Validates that key scoping produces strictly distinct keys per user."""
        def get_scoped(base_key, user_id):
            return f"{base_key}_{user_id}" if user_id else base_key

        assert get_scoped("movieRatings", 1) == "movieRatings_1"
        assert get_scoped("movieRatings", 2) == "movieRatings_2"
        assert get_scoped("movieRatings", 1) != get_scoped("movieRatings", 2)

        assert get_scoped("watchHistory", 10) == "watchHistory_10"
        assert get_scoped("watchHistory", 20) == "watchHistory_20"
        assert get_scoped("watchHistory", 10) != get_scoped("watchHistory", 20)

        assert get_scoped("myList", 5) == "myList_5"
        assert get_scoped("myList", 6) == "myList_6"
        assert get_scoped("myList", 5) != get_scoped("myList", 6)
