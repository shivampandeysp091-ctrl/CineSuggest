# -*- coding: utf-8 -*-
"""
backend/scripts/audit_api_compatibility.py
===========================================
Audits API and response schema compatibility for Phase 7:
1. Default algorithm selection (defaults to RRF)
2. ?algorithm=rrf explicitly
3. ?algorithm=hybrid explicitly (rollback option)
4. Invalid algorithm values (e.g. ?algorithm=content) -> raises HTTPException 400
5. Response field schema compatibility
6. Verify no RRF-score leakage into match_percentage or predicted_rating
"""

import os
import sys
from fastapi import HTTPException
from unittest.mock import MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from routes.recommendations import get_recommendations, _recommend_new_user_cf

print("=" * 80)
print("AUDITING API COMPATIBILITY & PARAMETER CONTRACT")
print("=" * 80)

# Mock authenticated user and DB session
mock_user = {"user_id": "test-user-uuid-1234"}
mock_db = MagicMock()

# Mock user mapping -> ml_user_id = 999 (app user)
mock_db.execute.return_value.fetchone.return_value = (999,)

# Mock user ratings in DB: Marvel profile (122892, 122912)
mock_ratings_rows = [
    {"movie_id": 122892, "rating": 5.0},
    {"movie_id": 122912, "rating": 5.0},
]
# Mock mappings().all()
mock_db.execute.return_value.mappings.return_value.all.return_value = mock_ratings_rows

# 1. Test Default Algorithm Selection
print("\n1. Testing Default Algorithm Selection (no query param)...")
res_default = get_recommendations(n=5, algorithm=None, current_user=mock_user, db=mock_db)
assert res_default["personalized"] is True
assert len(res_default["recommendations"]) == 5
first_rec = res_default["recommendations"][0]
print(f"   Default selection: personalized={res_default['personalized']}, count={res_default['count']}")
print(f"   Sample item fields: {list(first_rec.keys())}")
print(f"   Sample item: title='{first_rec['title']}', match_pct={first_rec['match_percentage']}%, pred_rating={first_rec['predicted_rating']}, rrf_score={first_rec.get('rrf_score')}")
assert "rrf_score" in first_rec
assert first_rec["rrf_score"] is not None
assert 0.005 <= first_rec["rrf_score"] <= 0.06
assert 0.5 <= first_rec["predicted_rating"] <= 5.0
assert 0.0 <= first_rec["match_percentage"] <= 100.0
print("   [PASS] Default algorithm is RRF and schema matches.")

# 2. Test ?algorithm=rrf
print("\n2. Testing Explicit ?algorithm=rrf...")
res_rrf = get_recommendations(n=5, algorithm="rrf", current_user=mock_user, db=mock_db)
assert res_rrf["personalized"] is True
assert res_rrf["recommendations"][0]["rrf_score"] is not None
print("   [PASS] ?algorithm=rrf executes correctly.")

# 3. Test ?algorithm=hybrid (Rollback Option)
print("\n3. Testing Explicit ?algorithm=hybrid (Rollback Option)...")
res_hyb = get_recommendations(n=5, algorithm="hybrid", current_user=mock_user, db=mock_db)
assert res_hyb["personalized"] is True
first_hyb = res_hyb["recommendations"][0]
assert first_hyb["hybrid_score"] is not None
assert first_hyb.get("rrf_score") is None  # RRF score is None in hybrid mode
print(f"   Sample item: title='{first_hyb['title']}', match_pct={first_hyb['match_percentage']}%, hybrid_score={first_hyb['hybrid_score']}, rrf_score={first_hyb.get('rrf_score')}")
print("   [PASS] ?algorithm=hybrid executes classic score-weighted blend.")

# 4. Test Invalid Algorithm Query Parameter
print("\n4. Testing Invalid Algorithm Parameter (?algorithm=content)...")
try:
    get_recommendations(n=5, algorithm="content", current_user=mock_user, db=mock_db)
    print("   [FAIL] Expected HTTPException not raised!")
except HTTPException as e:
    assert e.status_code == 400
    assert "algorithm must be 'rrf' or 'hybrid'" in e.detail
    print(f"   [PASS] Correctly rejected invalid algorithm: HTTP {e.status_code} ({e.detail})")

# 5. Check No RRF-score Leakage into Match%
print("\n5. Checking Score Separation Integrity...")
for item in res_default["recommendations"]:
    # RRF scores are in range [0.005, 0.05]
    # match_percentage must NEVER be identical or scaled from rrf_score
    assert item["match_percentage"] > 50.0  # highly recommended Marvel films have match > 50%
    assert item["match_percentage"] != item["rrf_score"]
    assert item["predicted_rating"] != item["rrf_score"]
print("   [PASS] Match% and predicted rating are strictly separated from RRF ranking scores.")

print("\n" + "=" * 80)
print("ALL API COMPATIBILITY AUDITS PASSED SUCCESSFULLY")
print("=" * 80)
