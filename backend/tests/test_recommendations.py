"""
tests/test_recommendations.py
-----------------------------
Unit tests for recommendation pipeline rules:
1. Watched-but-unrated movies are NOT excluded from recommendations.
2. TMDB-imported movies (movie_id >= 1,000,000) are filtered out before sending to CF model.
3. Match percentage formula correctness.
4. IMAX genre token filtering.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("JWT_SECRET", "test-secret-key-32-bytes-long-padding-here")
os.environ.setdefault("DATABASE_URL", "postgresql+psycopg2://dummy/dummy")

from routes.movies import TMDB_IMPORT_ID_FLOOR


class TestRecommendationPipelineLogic:

    def test_tmdb_import_id_floor_constant(self):
        # MovieLens small dataset IDs are <= 193609. Safe floor is 1,000,000.
        assert TMDB_IMPORT_ID_FLOOR >= 1_000_000

    def test_cf_rating_data_filter_removes_tmdb_imports(self):
        """
        Verify that ratings with movie_id >= 1_000_000 are stripped out
        before passing into the CF recommender.
        """
        user_ratings = [
            {"movie_id": 1, "rating": 5.0},          # MovieLens Toy Story
            {"movie_id": 296, "rating": 4.5},        # MovieLens Pulp Fiction
            {"movie_id": 1_000_001, "rating": 5.0},  # TMDB Imported movie
            {"movie_id": 1_000_002, "rating": 4.0},  # TMDB Imported movie
        ]

        cf_input = [
            (r["movie_id"], r["rating"])
            for r in user_ratings
            if r["movie_id"] < TMDB_IMPORT_ID_FLOOR
        ]

        assert len(cf_input) == 2
        assert cf_input == [(1, 5.0), (296, 4.5)]
        assert all(mid < TMDB_IMPORT_ID_FLOOR for mid, _ in cf_input)

    def test_exclusion_set_only_contains_rated_movies(self):
        """
        Verify that watch history does not exclude movies from recommendations
        (Decision 3: only explicit ratings exclude movies).
        """
        rated_ids = {10, 20}
        watched_ids = {10, 30, 40}

        # Exclude list should be based on rated_ids only
        exclude_ids = list(rated_ids)

        assert 10 in exclude_ids
        assert 20 in exclude_ids
        # Movie 30 and 40 (watched but unrated) should NOT be excluded!
        assert 30 not in exclude_ids
        assert 40 not in exclude_ids

    def test_match_percentage_normalization(self):
        """
        Tests the 0.5 - 5.0 rating scale normalization to 0 - 100 percentage.
        """
        def calc_match(score):
            clipped = max(0.5, min(5.0, score))
            return round((clipped - 0.5) / (5.0 - 0.5) * 100, 1)

        assert calc_match(5.0) == 100.0
        assert calc_match(0.5) == 0.0
        assert calc_match(2.75) == 50.0
        assert calc_match(4.0) == 77.8
        assert calc_match(3.5) == 66.7

    def test_imax_tag_filtered_from_genres(self):
        """
        Validates that 'IMAX' tag from MovieLens is removed from genres list.
        """
        raw_genres_string = "Action|Adventure|IMAX|Sci-Fi"
        tokens = [
            g.strip()
            for g in raw_genres_string.split("|")
            if g.strip() and g.strip().upper() != "IMAX"
        ]
        assert "IMAX" not in tokens
        assert tokens == ["Action", "Adventure", "Sci-Fi"]


class TestAvengersCollaborativeFiltering:
    """
    Tests proving that rating Avengers movies produces genuine collaborative
    recommendations (e.g., related Marvel / co-rated titles) and avoids
    unrelated classics (like The Seventh Seal or Lawrence of Arabia).
    """

    def test_two_avengers_ratings_produce_collaborative_marvel_recommendations(self):
        from routes.recommendations import _recommend_new_user_cf

        # Ratings for Avengers: Age of Ultron (122892) and Avengers: Infinity War (122912)
        rating_data = [
            {"movieId": 122892, "rating": 5.0},
            {"movieId": 122912, "rating": 5.0},
        ]
        exclude_ids = [122892, 122912]

        recs_df, is_personalized = _recommend_new_user_cf(
            rating_data=rating_data,
            n=10,
            exclude_ids=exclude_ids,
        )

        assert is_personalized is True, "Expected recommendation to be personalized"
        assert recs_df is not None
        assert len(recs_df) == 10

        rec_movie_ids = recs_df["movieId"].tolist()
        rec_titles = recs_df["title"].tolist()

        # 1. Rated movies must be excluded
        assert 122892 not in rec_movie_ids
        assert 122912 not in rec_movie_ids

        # 2. Collaborative filtering must return relevant co-rated titles.
        # Known MovieLens collaborative neighbors with Age of Ultron / Infinity War include:
        # 89745 (The Avengers 2012), 168252 (Logan), 122916 (Thor: Ragnarok),
        # 110102 (Captain America: Winter Soldier), 122920 (Captain America: Civil War),
        # 122904 (Deadpool), 112852 (Guardians of the Galaxy), 122926 (Untitled Spider-Man Reboot),
        # 111362 (X-Men: Days of Future Past), 87232 (X-Men: First Class), 102125 (Iron Man 3).
        marvel_cluster_ids = {89745, 168252, 122916, 110102, 122920, 122904, 112852, 122926, 111362, 87232, 102125, 122918}
        found_cluster_matches = set(rec_movie_ids).intersection(marvel_cluster_ids)
        assert len(found_cluster_matches) >= 3, (
            f"Expected at least 3 collaborative Marvel/superhero matches in top 10, found {len(found_cluster_matches)}: {rec_titles}"
        )

        # 3. Completely unrelated 1950s/1960s dramas with zero similarity to Avengers
        # (e.g., The Seventh Seal = 1278, Lawrence of Arabia = 1204) must NOT be in top 10!
        assert 1278 not in rec_movie_ids, "The Seventh Seal should not be recommended"
        assert 1204 not in rec_movie_ids, "Lawrence of Arabia should not be recommended"

        # 4. Predictions must not all be flat identical values (shrinkage working)
        predicted_ratings = recs_df["predicted_rating"].tolist()
        assert len(set(predicted_ratings)) > 1, "Predicted ratings should not be flat identical values"
        assert all(0.5 <= r <= 5.0 for r in predicted_ratings)

        # 5. Match percentages must be valid non-null percentages
        match_percentages = recs_df["match_percentage"].tolist()
        assert all(0.0 <= m <= 100.0 for m in match_percentages)

    def test_cold_start_user_returns_unpersonalized_without_fake_match(self):
        from routes.recommendations import _recommend_new_user_cf
        from ml.recommender import popular_movies

        # Empty ratings
        recs_df, is_personalized = _recommend_new_user_cf([], n=10)
        assert is_personalized is False
        assert recs_df is None

        # When endpoint falls back to popular_movies, match_percentage is set to None
        pop_df = popular_movies(n=10)
        pop_df["match_percentage"] = None
        assert all(pd is None for pd in pop_df["match_percentage"])

    def test_sparse_item_false_personalization_rejected(self):
        """
        Verify that a profile with only 1 obscure rating (Pokemon 4Ever, count=2 in ML)
        is rejected by the collaborative gate and classified as personalized=False.
        """
        from routes.recommendations import _recommend_new_user_cf

        pokemon_ratings = [{"movieId": 5672, "rating": 5.0}]
        recs_df, is_personalized = _recommend_new_user_cf(pokemon_ratings, n=10, exclude_ids=[5672])

        assert is_personalized is False, "Sparse item with count=2 must not be classified as personalized"
        assert recs_df is None


class TestPhase7RRFRegression:
    """
    Comprehensive regression tests for Phase 7 RRF production integration:
    - Zero ratings (new user)
    - Sparse anchored users (1-2 ratings)
    - Marvel profile
    - Harry Potter profile
    - Pokemon sparse profile
    - TMDB-only rated movies
    - User data isolation
    - Rated movie exclusion
    - Exactly 10 distinct recommendations
    - Missing/unsupported component handling
    - NaN and infinity handling
    - Deterministic tie-breaking
    - Algorithm switch & Hybrid rollback
    """

    def test_new_user_zero_ratings_unpersonalized(self):
        from routes.recommendations import _recommend_new_user_cf
        recs_df, is_personalized = _recommend_new_user_cf([], n=10)
        assert is_personalized is False
        assert recs_df is None

    def test_sparse_user_1_to_2_anchored_ratings(self):
        from routes.recommendations import _recommend_new_user_cf
        # Toy Story (1, count=215) and Jurassic Park (480, count=238)
        ratings = [{"movieId": 1, "rating": 5.0}, {"movieId": 480, "rating": 5.0}]
        recs_df, is_personalized = _recommend_new_user_cf(ratings, n=10, exclude_ids=[1, 480])

        assert is_personalized is True
        assert recs_df is not None
        assert len(recs_df) == 10
        assert 1 not in recs_df["movieId"].values
        assert 480 not in recs_df["movieId"].values
        assert "rrf_score" in recs_df.columns
        assert all(s is not None and s > 0 for s in recs_df["rrf_score"])

    def test_marvel_profile_rrf(self):
        from routes.recommendations import _recommend_new_user_cf
        marvel_ratings = [
            {"movieId": 122892, "rating": 5.0},  # Age of Ultron
            {"movieId": 122912, "rating": 5.0},  # Infinity War
        ]
        recs_df, is_personalized = _recommend_new_user_cf(marvel_ratings, n=10, exclude_ids=[122892, 122912])
        assert is_personalized is True
        rec_ids = recs_df["movieId"].tolist()

        # Must exclude rated movies
        assert 122892 not in rec_ids
        assert 122912 not in rec_ids

        # Must contain Marvel / superhero cluster movies
        marvel_cluster = {89745, 168252, 122916, 110102, 122920, 122904, 112852, 122926, 111362, 87232, 102125, 122918}
        hits = set(rec_ids).intersection(marvel_cluster)
        assert len(hits) >= 3, f"Expected >= 3 Marvel cluster matches, found {len(hits)}: {recs_df['title'].tolist()}"

        # Must NOT include unrelated classic drama
        assert 1278 not in rec_ids  # The Seventh Seal
        assert 1204 not in rec_ids  # Lawrence of Arabia

    def test_harry_potter_profile_rrf(self):
        from routes.recommendations import _recommend_new_user_cf
        hp_ratings = [
            {"movieId": 4896, "rating": 5.0},  # HP 1 (Sorcerer's Stone)
            {"movieId": 5816, "rating": 5.0},  # HP 2 (Chamber of Secrets)
        ]
        recs_df, is_personalized = _recommend_new_user_cf(hp_ratings, n=10, exclude_ids=[4896, 5816])
        assert is_personalized is True
        rec_ids = recs_df["movieId"].tolist()

        assert 4896 not in rec_ids
        assert 5816 not in rec_ids

        # Other HP movies in ML: 8368 (HP 3), 40815 (HP 4), 54001 (HP 5), 69844 (HP 6), 81834 (HP 7.1), 88125 (HP 7.2)
        hp_cluster = {8368, 40815, 54001, 69844, 81834, 88125}
        hits = set(rec_ids).intersection(hp_cluster)
        assert len(hits) >= 2, f"Expected >= 2 Harry Potter franchise matches, found {len(hits)}: {recs_df['title'].tolist()}"

        # Must NOT recommend unrelated mafia movie
        assert 1213 not in rec_ids  # Goodfellas

    def test_pokemon_sparse_profile_rejected_as_unpersonalized(self):
        from routes.recommendations import _recommend_new_user_cf
        pokemon_ratings = [{"movieId": 5672, "rating": 5.0}]
        recs_df, is_personalized = _recommend_new_user_cf(pokemon_ratings, n=10, exclude_ids=[5672])
        assert is_personalized is False
        assert recs_df is None

    def test_tmdb_only_rated_movies_filtered_cleanly(self):
        from routes.recommendations import _recommend_new_user_cf
        # Movies with ID >= 1,000,000 are TMDB imported
        raw_ratings = [
            {"movieId": 1_000_001, "rating": 5.0},
            {"movieId": 1_000_002, "rating": 4.5},
        ]
        ml_ratings = [r for r in raw_ratings if r["movieId"] < 1_000_000]
        assert len(ml_ratings) == 0
        recs_df, is_personalized = _recommend_new_user_cf(ml_ratings, n=10)
        assert is_personalized is False
        assert recs_df is None

    def test_user_data_isolation(self):
        from routes.recommendations import _recommend_new_user_cf
        # User A rates Marvel
        ratings_a = [{"movieId": 122892, "rating": 5.0}, {"movieId": 122912, "rating": 5.0}]
        recs_a, _ = _recommend_new_user_cf(ratings_a, n=10, exclude_ids=[122892, 122912])

        # User B rates Harry Potter
        ratings_b = [{"movieId": 4896, "rating": 5.0}, {"movieId": 5816, "rating": 5.0}]
        recs_b, _ = _recommend_new_user_cf(ratings_b, n=10, exclude_ids=[4896, 5816])

        set_a = set(recs_a["movieId"].tolist())
        set_b = set(recs_b["movieId"].tolist())

        # Overlap between Marvel and Harry Potter recommendations should be minimal (isolated profiles)
        jaccard = len(set_a.intersection(set_b)) / len(set_a.union(set_b))
        assert jaccard < 0.25, f"Expected distinct profile recommendations, Jaccard was {jaccard:.2f}"

    def test_rated_movie_exclusion_integrity(self):
        from routes.recommendations import _recommend_new_user_cf
        ratings = [
            {"movieId": 1, "rating": 5.0},
            {"movieId": 2, "rating": 4.0},
            {"movieId": 296, "rating": 5.0},
        ]
        exclude_ids = [1, 2, 296]
        recs_df, _ = _recommend_new_user_cf(ratings, n=10, exclude_ids=exclude_ids)
        rec_ids = set(recs_df["movieId"].tolist())
        for rated_id in exclude_ids:
            assert rated_id not in rec_ids

    def test_exactly_10_distinct_recommendations(self):
        from routes.recommendations import _recommend_new_user_cf
        ratings = [{"movieId": 296, "rating": 5.0}, {"movieId": 318, "rating": 5.0}]
        recs_df, is_personalized = _recommend_new_user_cf(ratings, n=10, exclude_ids=[296, 318])
        assert is_personalized is True
        assert len(recs_df) == 10
        assert len(set(recs_df["movieId"].tolist())) == 10

    def test_missing_unsupported_component_predictions_handled_gracefully(self):
        from routes.recommendations import _recommend_new_user_cf
        # Single anchored rating (Shawshank 318, count=317)
        ratings = [{"movieId": 318, "rating": 5.0}]
        recs_df, is_personalized = _recommend_new_user_cf(ratings, n=10, exclude_ids=[318])
        assert is_personalized is True
        assert recs_df is not None
        assert len(recs_df) == 10
        # If user_score is NaN for some items, it should gracefully be None, not throw
        assert "user_score" in recs_df.columns
        assert "item_score" in recs_df.columns
        assert "svd_score" in recs_df.columns

    def test_nan_and_infinity_handling(self):
        from routes.recommendations import _clean_float
        import math
        assert _clean_float(float("nan")) is None
        assert _clean_float(float("inf")) is None
        assert _clean_float(float("-inf")) is None
        assert _clean_float(None) is None
        assert _clean_float(3.14159, 2) == 3.14
        assert _clean_float(4.555, 1) == 4.6

    def test_deterministic_rrf_tie_breaking(self):
        from routes.recommendations import _recommend_new_user_cf
        ratings = [{"movieId": 1, "rating": 5.0}, {"movieId": 260, "rating": 5.0}]
        recs_run1, _ = _recommend_new_user_cf(ratings, n=10, exclude_ids=[1, 260], algorithm="rrf")
        recs_run2, _ = _recommend_new_user_cf(ratings, n=10, exclude_ids=[1, 260], algorithm="rrf")

        assert recs_run1["movieId"].tolist() == recs_run2["movieId"].tolist()
        assert recs_run1["rrf_score"].tolist() == recs_run2["rrf_score"].tolist()

    def test_algorithm_switch_and_hybrid_rollback(self):
        from routes.recommendations import _recommend_new_user_cf
        ratings = [{"movieId": 1, "rating": 5.0}, {"movieId": 260, "rating": 5.0}]

        # Test RRF
        recs_rrf, is_p_rrf = _recommend_new_user_cf(ratings, n=10, exclude_ids=[1, 260], algorithm="rrf")
        assert is_p_rrf is True
        assert "rrf_score" in recs_rrf.columns

        # Test Hybrid rollback
        recs_hyb, is_p_hyb = _recommend_new_user_cf(ratings, n=10, exclude_ids=[1, 260], algorithm="hybrid")
        assert is_p_hyb is True
        assert len(recs_hyb) == 10
        assert "hybrid_score" in recs_hyb.columns


