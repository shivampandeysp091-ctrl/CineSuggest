import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

vars_to_check = [
    "DATABASE_URL",
    "JWT_SECRET",
    "TMDB_API_KEY",
    "RESEND_API_KEY",
    "EMAIL_FROM",
    "FRONTEND_URL",
    "RECOMMENDER_ALGORITHM",
]

print("=" * 60)
print("ENVIRONMENT VARIABLES READINESS AUDIT (NO SECRETS PRINTED)")
print("=" * 60)
for v in vars_to_check:
    val = os.getenv(v)
    if val is not None and len(val.strip()) > 0:
        print(f"  {v:<24}: CONFIGURED (Non-empty, length={len(val)})")
    else:
        print(f"  {v:<24}: NOT SET (Using safe code default if applicable)")
print("=" * 60)
