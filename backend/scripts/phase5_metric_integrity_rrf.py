# -*- coding: utf-8 -*-
"""
backend/scripts/phase5_metric_integrity_rrf.py
===============================================
CineSuggest AI — Phase 5 Metric Integrity Audit & Reciprocal Rank Fusion (RRF) Experiment.

Audits:
1. Precision@10 calculation when an algorithm returns < 10 recommendations.
2. Catalog coverage calculation: verified over all users.
3. Intra-list diversity (ILD) verification: uses training-only cosine distance matrix.
4. User selection & test set consistency across Given-N groups:
   - Uses an identical 20% test holdout for all groups (cleanly isolating profile depth from test set size).
5. Exact candidate catalog consistency across all algorithms (train_counts >= 10, not in train).
6. Reciprocal Rank Fusion (RRF) implementation:
   - Combines ranked lists of User CF, Item CF, and SVD.
   - Uses fixed literature constant k_rrf = 60 (Cormack et al., SIGIR 2009). No test set tuning.
7. Evaluates and compares:
   - Popularity
   - User-Based CF
   - Item-Based CF
   - SVD
   - Existing Hybrid CF (production-gated)
   - RRF (Reciprocal Rank Fusion)
"""

import os
import sys
import math
import numpy as np
import pandas as pd

ML_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "ml")
SEED = 42
K = 10
K_RRF = 60  # Standard fixed constant from Cormack et al. 2009
REL_THRESH = 4.0
MIN_CANDIDATE_COUNT = 10

print("=" * 90)
print("PHASE 5 METRIC INTEGRITY AUDIT & RRF CONTROLLED EXPERIMENT")
print("=" * 90)

# ── 1. Load Raw Dataset & Construct Split ─────────────────────────────────────
movies_csv = os.path.join(ML_DIR, "movies.csv")
ratings_csv = os.path.join(ML_DIR, "ratings.csv")
if not os.path.exists(ratings_csv):
    ratings_csv = os.path.join(ML_DIR, "ratings.csv.csv")

df_movies = pd.read_csv(movies_csv)
df_ratings = pd.read_csv(ratings_csv)

all_user_ids = np.sort(df_ratings["userId"].unique())
all_movie_ids = np.sort(df_ratings["movieId"].unique())
u2i = {uid: i for i, uid in enumerate(all_user_ids)}
m2j = {mid: j for j, mid in enumerate(all_movie_ids)}
n_users = len(all_user_ids)
n_items = len(all_movie_ids)

# Stratified 80/20 train/test split per user (Seed 42)
rng = np.random.default_rng(SEED)
train_indices_list = []
test_indices_list = []

for uid, group in df_ratings.groupby("userId"):
    idx = group.index.values.copy()
    rng.shuffle(idx)
    n_hold = max(1, int(round(len(idx) * 0.20)))
    test_indices_list.append(idx[:n_hold])
    train_indices_list.append(idx[n_hold:])

all_train_idx = np.concatenate(train_indices_list)
all_test_idx = np.concatenate(test_indices_list)
df_train = df_ratings.loc[all_train_idx].reset_index(drop=True)
df_test = df_ratings.loc[all_test_idx].reset_index(drop=True)

# ── 2. Training-Only Model Fitting (No Leakage) ──────────────────────────────
global_mean_train = float(df_train["rating"].mean())

R_train = np.full((n_users, n_items), np.nan, dtype=np.float32)
for _, row in df_train.iterrows():
    R_train[u2i[int(row["userId"])], m2j[int(row["movieId"])]] = float(row["rating"])

mask_train = ~np.isnan(R_train)
train_counts = mask_train.sum(axis=0)

# Eligible candidate catalog (train_counts >= 10)
eligible_catalog_mask = (train_counts >= MIN_CANDIDATE_COUNT)
eligible_catalog_indices = np.where(eligible_catalog_mask)[0]
n_eligible_catalog = len(eligible_catalog_indices)
print(f"Eligible Candidate Catalog: {n_eligible_catalog:,} items (review count >= {MIN_CANDIDATE_COUNT}).")

user_means_train = np.full(n_users, global_mean_train, dtype=np.float32)
for ui in range(n_users):
    vals = R_train[ui, mask_train[ui]]
    if len(vals) > 0:
        user_means_train[ui] = float(np.mean(vals))

Rc_train = np.where(mask_train, R_train - user_means_train[:, None], 0.0).astype(np.float32)
user_norm_train = np.linalg.norm(Rc_train, axis=1)
item_norm_train = np.linalg.norm(Rc_train, axis=0)

# Item-Item Cosine Similarity Matrix (training data only)
denom_item = item_norm_train[:, None] * item_norm_train[None, :] + 1e-9
item_sim_mat = (Rc_train.T @ Rc_train) / denom_item
np.fill_diagonal(item_sim_mat, 0.0)
pos_item_sim_mat = np.maximum(0.0, item_sim_mat)

# User-User Cosine Similarity Matrix (training data only)
denom_user = user_norm_train[:, None] * user_norm_train[None, :] + 1e-9
user_sim_mat = (Rc_train @ Rc_train.T) / denom_user
np.fill_diagonal(user_sim_mat, 0.0)
pos_user_sim_mat = np.maximum(0.0, user_sim_mat)

# SVD (training data only)
U_svd, S_svd, Vt_svd = np.linalg.svd(Rc_train, full_matrices=False)
K_SVD = 20
P_train = U_svd[:, :K_SVD] * S_svd[:K_SVD]
Q_train = Vt_svd[:K_SVD, :].T

# Item biases from train
item_biases_train = np.zeros(n_items, dtype=np.float32)
for j in range(n_items):
    u_idx = np.where(mask_train[:, j])[0]
    if len(u_idx) > 0:
        item_biases_train[j] = float(np.mean(R_train[u_idx, j] - user_means_train[u_idx]))

# Popularity rank across eligible catalog
pop_ranked_candidates = [j for j in np.argsort(-train_counts) if eligible_catalog_mask[j]]

# Intra-list diversity distance matrix: 1.0 - CosineSimilarity (training data only)
ild_dist_matrix = 1.0 - np.clip(item_sim_mat, 0.0, 1.0)
np.fill_diagonal(ild_dist_matrix, 0.0)

# Pre-map test items by user: identical 20% test holdout used for ALL groups
test_by_user = {}
for _, row in df_test.iterrows():
    uid = int(row["userId"])
    mid = int(row["movieId"])
    r = float(row["rating"])
    test_by_user.setdefault(uid, []).append((mid, r))

# ── 3. Evaluation Function ───────────────────────────────────────────────────

def run_evaluation(group_label, sample_uids, given_n=None):
    """
    Evaluates:
    - Popularity
    - User-Based CF
    - Item-Based CF
    - SVD
    - Hybrid CF (production-gated)
    - RRF (Reciprocal Rank Fusion of User CF, Item CF, and SVD)
    """
    rng_sub = np.random.default_rng(SEED + (given_n or 777))

    algorithms = ["Popularity", "User-Based CF", "Item-Based CF", "SVD", "Hybrid CF", "RRF"]

    rmse_errs = {alg: [] for alg in algorithms if alg not in ("Popularity", "RRF")}
    mae_errs  = {alg: [] for alg in algorithms if alg not in ("Popularity", "RRF")}

    prec_list = {alg: [] for alg in algorithms}
    rec_list  = {alg: [] for alg in algorithms}
    ndcg_list = {alg: [] for alg in algorithms}

    recommended_items_set = {alg: set() for alg in algorithms}
    pop_sum_list          = {alg: [] for alg in algorithms}
    ild_list              = {alg: [] for alg in algorithms}
    users_with_lt10       = {alg: 0 for alg in algorithms}

    valid_eval_users = 0
    total_users = 0

    for uid in sample_uids:
        ui = u2i[uid]
        full_train_j = np.where(mask_train[ui])[0]

        # In this clean Given-N setup:
        # We sample given_n ratings from the user's available training ratings.
        # The test set remains IDENTICAL: the user's 20% holdout from df_test!
        if given_n is not None:
            if len(full_train_j) <= given_n:
                train_j = full_train_j
            else:
                shuf = rng_sub.permutation(full_train_j)
                train_j = shuf[:given_n]
        else:
            train_j = full_train_j

        if len(train_j) == 0:
            continue

        total_users += 1

        # Profile vector on training ratings only
        train_ratings = R_train[ui, train_j]
        u_mean = float(np.mean(train_ratings))
        train_rc = np.zeros(n_items, dtype=np.float32)
        train_rc[train_j] = train_ratings - u_mean

        test_items = test_by_user.get(uid, [])
        if len(test_items) == 0:
            continue

        # ── 1. User-Based CF ──
        nrm = float(np.linalg.norm(train_rc))
        if nrm > 0:
            u_sims = (Rc_train @ train_rc) / (user_norm_train * nrm + 1e-9)
            u_sims[ui] = 0.0
            pos_u = np.maximum(0.0, u_sims)
            top_u = np.argsort(-pos_u)[:30]
            top_u = top_u[pos_u[top_u] > 0]
            if len(top_u) > 0:
                w_s = pos_u[top_u]
                m_s = mask_train[top_u].astype(np.float32)
                sup = m_s.sum(axis=0)
                num = w_s @ Rc_train[top_u]
                den = w_s @ m_s
                shrink = sup / (sup + 2.0)
                with np.errstate(divide="ignore", invalid="ignore"):
                    p_ub = u_mean + shrink * (num / (den + 1e-9))
                p_ub[(den <= 0) | (sup < 3)] = np.nan
            else:
                p_ub = np.full(n_items, np.nan)
        else:
            p_ub = np.full(n_items, np.nan)

        # ── 2. Item-Based CF ──
        sim_sub = pos_item_sim_mat[train_j, :]
        sim_sum = sim_sub.sum(axis=0)
        dev_r = train_rc[train_j]
        weighted_dev = sim_sub.T @ dev_r
        p_ib = np.where(sim_sum > 0, u_mean + weighted_dev / (sim_sum + 0.5), np.nan)

        # ── 3. SVD ──
        if len(train_j) > 0:
            Q_r = Q_train[train_j]
            rc_r = train_rc[train_j]
            reg = 2.0 * np.eye(K_SVD)
            p_u = np.linalg.solve(Q_r.T @ Q_r + reg, Q_r.T @ rc_r)
            p_svd = u_mean + item_biases_train + (p_u @ Q_train.T)
        else:
            p_svd = np.full(n_items, u_mean)

        # ── 4. Hybrid CF (Production Gating) ──
        n_r = len(train_j)
        weights = (0.20, 0.60, 0.20) if n_r <= 3 else (0.30, 0.40, 0.30)
        min_sim = 0.25 if n_r <= 3 else 0.15

        profile_counts = train_counts[train_j]
        has_anchor = bool((profile_counts >= 10).any() or (profile_counts.sum() >= 15))
        has_user_cf = bool((~np.isnan(p_ub)).any())

        if not has_anchor and not has_user_cf:
            p_hybrid = np.full(n_items, np.nan)
        else:
            has_collab = (~np.isnan(p_ub)) | (sim_sum >= min_sim)
            preds_m = np.column_stack([p_ub, p_ib, p_svd])
            w_v = np.asarray(weights, dtype=float)[None, :] * ~np.isnan(preds_m)
            tw = w_v.sum(axis=1)
            # Un-collaborative items receive NaN (no artificial user-mean filling)
            p_hybrid = np.where(has_collab & (tw > 0), (np.nan_to_num(preds_m) * w_v).sum(axis=1) / tw, np.nan)

        # ── Point Prediction Errors (RMSE / MAE) ──
        for mid, r_true in test_items:
            if mid not in m2j:
                continue
            mj = m2j[mid]
            p_u_val = p_ub[mj] if not np.isnan(p_ub[mj]) else u_mean
            p_i_val = p_ib[mj] if not np.isnan(p_ib[mj]) else u_mean
            p_h_val = p_hybrid[mj] if not np.isnan(p_hybrid[mj]) else u_mean

            rmse_errs["User-Based CF"].append(p_u_val - r_true)
            mae_errs["User-Based CF"].append(abs(p_u_val - r_true))
            rmse_errs["Item-Based CF"].append(p_i_val - r_true)
            mae_errs["Item-Based CF"].append(abs(p_i_val - r_true))
            rmse_errs["SVD"].append(p_svd[mj] - r_true)
            mae_errs["SVD"].append(abs(p_svd[mj] - r_true))
            rmse_errs["Hybrid CF"].append(p_h_val - r_true)
            mae_errs["Hybrid CF"].append(abs(p_h_val - r_true))

        # ── Candidate Ranking Generation ──
        base_eligible = eligible_catalog_mask.copy()
        base_eligible[train_j] = False  # training rated movies excluded

        def rank_candidates(score_arr, top_n=50):
            cand_mask = base_eligible & (~np.isnan(score_arr)) & np.isfinite(score_arr)
            cand_j = np.where(cand_mask)[0]
            if len(cand_j) == 0:
                return []
            cand_scores = score_arr[cand_j]
            top_local = np.argsort(-cand_scores)[:top_n]
            return cand_j[top_local].tolist()

        # Top ranked lists for base algorithms
        list_pop = [j for j in pop_ranked_candidates if base_eligible[j]][:K]
        list_ub = rank_candidates(p_ub, top_n=50)
        list_ib = rank_candidates(p_ib, top_n=50)
        list_svd = rank_candidates(p_svd, top_n=50)
        list_hyb = rank_candidates(p_hybrid, top_n=K)

        # ── 5. Reciprocal Rank Fusion (RRF) ──
        # Formula: RRF_score(d) = sum_{m in models} 1 / (k_rrf + rank_m(d))
        # k_rrf = 60 fixed constant
        rrf_scores = {}
        for ranked_list in (list_ub, list_ib, list_svd):
            for rank_pos, item_j in enumerate(ranked_list, 1):
                rrf_scores[item_j] = rrf_scores.get(item_j, 0.0) + (1.0 / (K_RRF + rank_pos))

        if rrf_scores:
            sorted_rrf = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)
            list_rrf = [item_j for item_j, _ in sorted_rrf[:K]]
        else:
            list_rrf = []

        recs_dict = {
            "Popularity": list_pop,
            "User-Based CF": list_ub[:K],
            "Item-Based CF": list_ib[:K],
            "SVD": list_svd[:K],
            "Hybrid CF": list_hyb,
            "RRF": list_rrf,
        }

        # Catalog coverage, popularity, diversity
        for alg, rec_j_list in recs_dict.items():
            if len(rec_j_list) < K:
                users_with_lt10[alg] += 1
            if len(rec_j_list) > 0:
                recommended_items_set[alg].update(rec_j_list)
                pop_sum_list[alg].append(float(np.mean(train_counts[rec_j_list])))
                if len(rec_j_list) >= 2:
                    pairs_d = [
                        ild_dist_matrix[rec_j_list[a], rec_j_list[b]]
                        for a in range(len(rec_j_list))
                        for b in range(a + 1, len(rec_j_list))
                    ]
                    ild_list[alg].append(float(np.mean(pairs_d)))

        # Relevant test items (Threshold >= 4.0 stars)
        rel_test_j = set(m2j[mid] for mid, r_true in test_items if mid in m2j and r_true >= REL_THRESH)
        if len(rel_test_j) > 0:
            valid_eval_users += 1
            idcg = sum(1.0 / math.log2(rk + 2) for rk in range(min(len(rel_test_j), K)))

            for alg, rec_j_list in recs_dict.items():
                hits = len(rel_test_j.intersection(rec_j_list))
                # Standard IR Precision@K: hits / K (strictly penalized if list < K)
                prec = hits / K
                rec = hits / len(rel_test_j)
                dcg = sum(1.0 / math.log2(rk + 2) for rk, j in enumerate(rec_j_list) if j in rel_test_j)
                ndcg = dcg / idcg if idcg > 0 else 0.0

                prec_list[alg].append(prec)
                rec_list[alg].append(rec)
                ndcg_list[alg].append(ndcg)

    # Print results table
    print(f"\n{'='*98}")
    print(f"RATING GROUP: {group_label}")
    print(f"Total Users: {total_users} | Users with >= 1 Relevant Test Item: {valid_eval_users}")
    print(f"{'='*98}")
    print(f"{'Algorithm':<16} {'RMSE':<8} {'MAE':<8} {'Prec@10':<9} {'Rec@10':<9} {'NDCG@10':<9} {'CatCov%':<9} {'AvgPop':<8} {'ILD':<7} {'<10Recs'}")
    print("-" * 98)

    for alg in algorithms:
        if alg in rmse_errs:
            rmse_val = f"{np.sqrt(np.mean(np.array(rmse_errs[alg])**2)):.4f}"
            mae_val  = f"{np.mean(mae_errs[alg]):.4f}"
        else:
            rmse_val, mae_val = "  N/A  ", "  N/A  "

        p10 = f"{np.mean(prec_list[alg]):.4f}" if len(prec_list[alg]) > 0 else "0.0000"
        r10 = f"{np.mean(rec_list[alg]):.4f}"  if len(rec_list[alg]) > 0 else "0.0000"
        nd  = f"{np.mean(ndcg_list[alg]):.4f}"  if len(ndcg_list[alg]) > 0 else "0.0000"

        cov_pct = f"{(len(recommended_items_set[alg]) / n_eligible_catalog) * 100:.1f}%"
        avg_pop = f"{np.mean(pop_sum_list[alg]):.1f}" if len(pop_sum_list[alg]) > 0 else "N/A"
        ild_val = f"{np.mean(ild_list[alg]):.3f}" if len(ild_list[alg]) > 0 else "N/A"
        lt10    = f"{users_with_lt10[alg]}/{total_users}"

        print(f"{alg:<16} {rmse_val:<8} {mae_val:<8} {p10:<9} {r10:<9} {nd:<9} {cov_pct:<9} {avg_pop:<8} {ild_val:<7} {lt10}")


# Sample 150 test users for Given-N experiments
test_sample_uids = all_user_ids[rng.choice(len(all_user_ids), size=150, replace=False)]

print("\n1. Running Group 1: 1–2 training ratings (Given N=2, Identical 20% Holdout Test)...")
run_evaluation("1–2 Training Ratings (Given N=2)", test_sample_uids, given_n=2)

print("\n2. Running Group 2: 3–5 training ratings (Given N=4, Identical 20% Holdout Test)...")
run_evaluation("3–5 Training Ratings (Given N=4)", test_sample_uids, given_n=4)

print("\n3. Running Group 3: 6–10 training ratings (Given N=8, Identical 20% Holdout Test)...")
run_evaluation("6–10 Training Ratings (Given N=8)", test_sample_uids, given_n=8)

print("\n4. Running Group 4: >10 training ratings (Full 80% Train, All 610 Users)...")
run_evaluation(">10 Training Ratings (Full 80% Train, N >= 16)", all_user_ids, given_n=None)

print("\n" + "=" * 98)
print("PHASE 5 METRIC INTEGRITY AUDIT & RRF EXPERIMENT COMPLETE")
print("=" * 98)
