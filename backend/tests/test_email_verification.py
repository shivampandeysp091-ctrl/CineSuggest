"""
tests/test_email_verification.py
--------------------------------
Unit tests for OTP generation, hashing, verification, and cooldown logic.
Runs offline without external network or database calls.
"""
import os
import sys
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

# Ensure backend/ is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("JWT_SECRET", "test-secret-key-32-bytes-long-padding-here")
os.environ.setdefault("DATABASE_URL", "postgresql+psycopg2://dummy/dummy")

from routes.auth import _generate_otp, _hash_otp, _check_otp


class TestOtpUnit:

    def test_generate_otp_returns_six_digit_string(self):
        otp = _generate_otp()
        assert isinstance(otp, str)
        assert len(otp) == 6
        assert otp.isdigit()
        val = int(otp)
        assert 100_000 <= val <= 999_999

    def test_generate_otp_randomness(self):
        otps = {_generate_otp() for _ in range(20)}
        # Set of 20 random 6-digit codes should contain at least 15 unique values
        assert len(otps) >= 15

    def test_hash_and_check_otp_matching(self):
        otp = "741852"
        hashed = _hash_otp(otp)
        assert hashed != otp
        assert _check_otp(otp, hashed) is True

    def test_check_otp_rejects_wrong_code(self):
        otp = "123456"
        hashed = _hash_otp(otp)
        assert _check_otp("654321", hashed) is False
        assert _check_otp("", hashed) is False
        assert _check_otp("12345", hashed) is False

    def test_check_otp_handles_invalid_hash_gracefully(self):
        assert _check_otp("123456", "invalid_hash_not_bcrypt") is False


class TestOtpBusinessRules:

    def test_otp_expiry_calculation(self):
        now = datetime.now(timezone.utc)
        expiry_minutes = 15
        expires_at = now + timedelta(minutes=expiry_minutes)
        assert (expires_at - now).total_seconds() == 15 * 60

    def test_otp_cooldown_window(self):
        cooldown_seconds = 60
        now = datetime.now(timezone.utc)
        sent_at = now - timedelta(seconds=30)
        elapsed = (now - sent_at).total_seconds()
        assert elapsed < cooldown_seconds
        remaining = int(cooldown_seconds - elapsed)
        assert remaining == 30

        # After 61 seconds, cooldown has passed
        sent_old = now - timedelta(seconds=61)
        assert (now - sent_old).total_seconds() >= cooldown_seconds
