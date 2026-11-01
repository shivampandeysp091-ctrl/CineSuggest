-- ============================================================
-- CineSuggest AI — Database Migration v2
-- Run this file ONCE against your Supabase database.
-- Safe to re-run: uses IF NOT EXISTS / IF EXISTS guards.
-- ============================================================
--
-- WHAT THIS MIGRATION DOES:
--   1. Adds email verification support to users table.
--   2. Creates email_verification_tokens table (OTP storage).
--   3. Adds source column to movies (movielens vs tmdb_import).
--
-- BEFORE RUNNING:
--   Connect to your Supabase SQL editor and paste this entire file.
--
-- ============================================================

BEGIN;

-- ------------------------------------------------------------
-- 1. Add is_verified to users
--    All existing users are marked verified (they registered
--    before verification was required).
-- ------------------------------------------------------------
ALTER TABLE users
    ADD COLUMN IF NOT EXISTS is_verified BOOLEAN NOT NULL DEFAULT FALSE;

-- Mark every pre-existing account as verified so they can still log in.
UPDATE users SET is_verified = TRUE WHERE is_verified = FALSE;


-- ------------------------------------------------------------
-- 2. Create email_verification_tokens table
--    Stores bcrypt-hashed OTPs with expiry and attempt tracking.
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS email_verification_tokens (
    id          BIGSERIAL PRIMARY KEY,
    user_id     INTEGER       NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    otp_hash    VARCHAR(255)  NOT NULL,
    expires_at  TIMESTAMP     NOT NULL,
    used        BOOLEAN       NOT NULL DEFAULT FALSE,
    attempts    INTEGER       NOT NULL DEFAULT 0,
    created_at  TIMESTAMP     NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_evt_user_id  ON email_verification_tokens (user_id);
CREATE INDEX IF NOT EXISTS idx_evt_expires  ON email_verification_tokens (expires_at);


-- ------------------------------------------------------------
-- 3. Add source column to movies
--    'movielens'   = original training catalog
--    'tmdb_import' = user-imported; NOT in SVD training data
-- ------------------------------------------------------------
ALTER TABLE movies
    ADD COLUMN IF NOT EXISTS source VARCHAR(20) NOT NULL DEFAULT 'movielens';

UPDATE movies SET source = 'movielens' WHERE source IS NULL OR source = '';

COMMIT;
