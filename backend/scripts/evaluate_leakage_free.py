# -*- coding: utf-8 -*-
"""
backend/scripts/evaluate_leakage_free.py
=========================================
Leakage-Free Offline Evaluation Pipeline for CineSuggest AI.

Integrity Guarantees:
1. Starts directly from raw ratings.csv and movies.csv.
2. Splits ratings per user into 80% train / 20% test using a fixed seed (42).
3. Fits ALL components strictly on training data:
   - Global mean
   - User means and centered rating matrix
   - Item norms and Item-Item cosine similarity matrix
   - SVD decomposition (U, Sigma, Vt) fitted only on R_train
   - Training counts for popularity baseline
4. ZERO precomputed artifacts (svd_factors.npz, full-dataset Rc) are loaded.
5. All models evaluated on identical test records.
6. Evaluates:
   - Rating prediction: RMSE and MAE
   - Ranking (K=10, Threshold=4.0 stars): Precision@10, Recall@10, NDCG@10
   - Compares with non-personalized Popularity Baseline and earlier transductive metrics.
"""

import os
import sys
import math
import numpy as np
import pandas as pd

ML_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "ml")
SEED = 42
K = 10
REL_THRESH = 4.0

print("=" * 80)
print("CINESUGGEST AI - LEAKAGE-FREE OFFLINE EVALUATION PIPELINE")
print("=" * 80)

# ── 1. Load Raw Datasets ──────────────────────────────────────────────────────
movies_csv = os.path.join(ML_DIR, "movies.csv")
ratings_csv = os.path.join(ML_DIR, "ratings.csv")
if not os.path.exists(ratings_csv):
    ratings_csv = os.path.join(ML_DIR, "ratings.csv.csv")

print(f"Loading raw datasets from: {ML_DIR}")
df_movies = pd.read_csv(movies_csv)
df_ratings = pd.read_csv(ratings_csv)

total_ratings = len(df_ratings)
n_users_total = df_ratings["userId"].nunique()
n_movies_total = df_ratings["movieId"].nunique()
print(f"Total raw ratings: {total_ratings:,} across {n_users_total:,} users and {n_movies_total:,} movies.")

# Index mappings
all_user_ids = np.sort(df_ratings["userId"].unique())
all_movie_ids = np.sort(df_ratings["movieId"].unique())
u2i = {uid: i for i, uid in enumerate(all_user_ids)}
m2j = {mid: j for j, mid in enumerate(all_movie_ids)}
n_users = len(all_user_ids)
n_items = len(all_movie_ids)

# ── 2. Reproducible 80/20 Train/Test Split (No Leakage) ──────────────────────
print(f"\nPerforming 80/20 stratified split per user (Random Seed: {SEED})...")
rng = np.random.default_rng(SEED)

train_rows = []
test_rows = []

for uid, group in df_ratings.groupby("userId"):
    indices = group.index.values.copy()
    rng.shuffle(indices)
    n_total = len(indices)
    n_hold = max(1, int(round(n_total * 0.20)))
    test_idx = indices[:n_hold]
    train_idx = indices[n_hold:]
    test_rows.append(test_idx)
    train_rows.append(train_idx)

all_train_idx = np.concatenate(train_rows)
all_test_idx = np.concatenate(test_rows)
df_train = df_ratings.loc[all_train_idx].reset_index(drop=True)
df_test = df_ratings.loc[all_test_idx].reset_index(drop=True)

print(f"Training split: {len(df_train):,} ratings ({len(df_train)/total_ratings*100:.1f}%)")
print(f"Test split:     {len(df_test):,} ratings ({len(df_test)/total_ratings*100:.1f}%)")
print(f"Overlap check:  {len(set(all_train_idx).intersection(set(all_test_idx)))} overlapping records (Guaranteed 0)")

# ── 3. Fit Training-Only Models & Matrices ───────────────────────────────────
print("\nFitting models strictly on df_train (Test data completely isolated)...")

# Global mean
global_mean_train = float(df_train["rating"].mean())

# Build R_train matrix
R_train = np.full((n_users, n_items), np.nan, dtype=np.float32)
for _, row in df_train.iterrows():
    ui = u2i[int(row["userId"])]
    mj = m2j[int(row["movieId"])]
    R_train[ui, mj] = float(row["rating"])

mask_train = ~np.isnan(R_train)
train_counts_per_item = mask_train.sum(axis=0)

# User means
user_means_train = np.full(n_users, global_mean_train, dtype=np.float32)
for ui in range(n_users):
    rated_vals = R_train[ui, mask_train[ui]]
    if len(rated_vals) > 0:
        user_means_train[ui] = float(np.mean(rated_vals))

# Centered matrix Rc_train
Rc_train = np.where(mask_train, R_train - user_means_train[:, None], 0.0).astype(np.float32)
user_norm_train = np.linalg.norm(Rc_train, axis=1)
item_norm_train = np.linalg.norm(Rc_train, axis=0)

# Item-Item Cosine Similarity Matrix from training data only
# (Rc_train.T @ Rc_train) / norms
print("Computing Item-Item similarity matrix from R_train...")
denom_item = item_norm_train[:, None] * item_norm_train[None, :] + 1e-9
item_sim_mat = (Rc_train.T @ Rc_train) / denom_item
np.fill_diagonal(item_sim_mat, 0.0)
pos_item_sim_mat = np.maximum(0.0, item_sim_mat)

# User-User Cosine Similarity Matrix from training data only
print("Computing User-User similarity matrix from R_train...")
denom_user = user_norm_train[:, None] * user_norm_train[None, :] + 1e-9
user_sim_mat = (Rc_train @ Rc_train.T) / denom_user
np.fill_diagonal(user_sim_mat, 0.0)
pos_user_sim_mat = np.maximum(0.0, user_sim_mat)

# SVD Decomposition strictly on Rc_train
print("Fitting SVD (k=20 components) strictly on Rc_train...")
# Full SVD of (610 x 9724)
U_svd, S_svd, Vt_svd = np.linalg.svd(Rc_train, full_matrices=False)
K_SVD = 20
P_train = U_svd[:, :K_SVD] * S_svd[:K_SVD]           # (610, 20) user latent factors
Q_train = Vt_svd[:K_SVD, :].T                       # (9724, 20) item latent factors

# Item biases from train:
item_biases_train = np.zeros(n_items, dtype=np.float32)
for j in range(n_items):
    u_idx = np.where(mask_train[:, j])[0]
    if len(u_idx) > 0:
        item_biases_train[j] = float(np.mean(R_train[u_idx, j] - user_means_train[u_idx]))

# Popularity Baseline Order (ranked by training set review count)
pop_ranked_items = np.argsort(-train_counts_per_item)

print("All model parameters and matrices fitted cleanly.")

# ── 4. Evaluation Loop on Unseen Test Set ─────────────────────────────────────
print(f"\nEvaluating on {len(df_test):,} unseen test ratings across identical instances...")

# Structure test instances by user for efficient prediction & ranking
test_by_user = {}
for _, row in df_test.iterrows():
    uid = int(row["userId"])
    mid = int(row["movieId"])
    r = float(row["rating"])
    test_by_user.setdefault(uid, []).append((mid, r))

# Prediction error tracking
errors = {
    "global_mean": [],
    "user_mean": [],
    "user_based_cf": [],
    "item_based_cf": [],
    "svd": [],
    "hybrid_cf": [],
}

# Ranking metrics tracking
precisions_hybrid, recalls_hybrid, ndcgs_hybrid = [], [], []
precisions_pop, recalls_pop, ndcgs_pop = [], [], []

for uid, test_items in test_by_user.items():
    ui = u2i[uid]
    train_rated_j = np.where(mask_train[ui])[0]
    train_rc = Rc_train[ui]
    u_mean = user_means_train[ui]

    # Precompute model predictions across all candidate items for this user:
    # 1. User-Based CF
    w_users = pos_user_sim_mat[ui]
    top_u = np.argsort(-w_users)[:30]
    top_u = top_u[w_users[top_u] > 0]
    if len(top_u) > 0:
        w_sub = w_users[top_u]
        m_sub = mask_train[top_u].astype(np.float32)
        support = m_sub.sum(axis=0)
        num_u = w_sub @ Rc_train[top_u]
        den_u = w_sub @ m_sub
        shrink_u = support / (support + 2.0)
        with np.errstate(divide="ignore", invalid="ignore"):
            pred_ub_all = u_mean + shrink_u * (num_u / (den_u + 1e-9))
        pred_ub_all[(den_u <= 0) | (support < 3)] = np.nan
    else:
        pred_ub_all = np.full(n_items, np.nan)

    # 2. Item-Based CF
    sim_sub = pos_item_sim_mat[train_rated_j, :]  # shape: (n_train_rated, n_items)
    sim_sum_all = sim_sub.sum(axis=0)
    dev_rated = train_rc[train_rated_j]
    weighted_dev_all = sim_sub.T @ dev_rated
    pred_ib_all = np.where(sim_sum_all > 0, u_mean + weighted_dev_all / (sim_sum_all + 0.5), np.nan)

    # 3. SVD
    pred_svd_all = u_mean + item_biases_train + (P_train[ui] @ Q_train.T)

    # 4. Hybrid CF
    has_collab_all = (~np.isnan(pred_ub_all)) | (sim_sum_all >= 0.15)
    preds_mat = np.column_stack([pred_ub_all, pred_ib_all, pred_svd_all])
    w_vec = np.array([0.30, 0.40, 0.30])[None, :] * ~np.isnan(preds_mat)
    tw_vec = w_vec.sum(axis=1)
    pred_hybrid_all = np.where(has_collab_all & (tw_vec > 0), (np.nan_to_num(preds_mat) * w_vec).sum(axis=1) / tw_vec, u_mean)

    # Record point prediction errors on test instances:
    for mid, r_true in test_items:
        if mid not in m2j:
            continue
        mj = m2j[mid]

        p_gm = global_mean_train
        p_um = u_mean
        p_ub = pred_ub_all[mj] if not np.isnan(pred_ub_all[mj]) else u_mean
        p_ib = pred_ib_all[mj] if not np.isnan(pred_ib_all[mj]) else u_mean
        p_sv = pred_svd_all[mj]
        p_hy = pred_hybrid_all[mj]

        errors["global_mean"].append(p_gm - r_true)
        errors["user_mean"].append(p_um - r_true)
        errors["user_based_cf"].append(p_ub - r_true)
        errors["item_based_cf"].append(p_ib - r_true)
        errors["svd"].append(p_sv - r_true)
        errors["hybrid_cf"].append(p_hy - r_true)

    # Ranking evaluation:
    # Relevant holdout items: items in test set with r_true >= REL_THRESH
    rel_test_j = set(m2j[mid] for mid, r_true in test_items if mid in m2j and r_true >= REL_THRESH)
    if len(rel_test_j) > 0:
        # Hybrid CF ranking (candidate must have train_counts >= 10 and not be in train_rated)
        scores_h = pred_hybrid_all.copy()
        scores_h[train_rated_j] = -np.inf
        scores_h[train_counts_per_item < 10] = -np.inf
        top_k_h = np.argsort(-scores_h)[:K]

        hits_h = len(rel_test_j.intersection(top_k_h))
        precisions_hybrid.append(hits_h / K)
        recalls_hybrid.append(hits_h / len(rel_test_j))
        dcg_h = sum(1.0 / math.log2(rk + 2) for rk, j in enumerate(top_k_h) if j in rel_test_j)
        idcg = sum(1.0 / math.log2(rk + 2) for rk in range(min(len(rel_test_j), K)))
        ndcgs_hybrid.append(dcg_h / idcg if idcg > 0 else 0.0)

        # Popularity Baseline ranking
        pop_candidates = [j for j in pop_ranked_items if j not in train_rated_j][:K]
        hits_pop = len(rel_test_j.intersection(pop_candidates))
        precisions_pop.append(hits_pop / K)
        recalls_pop.append(hits_pop / len(rel_test_j))
        dcg_p = sum(1.0 / math.log2(rk + 2) for rk, j in enumerate(pop_candidates) if j in rel_test_j)
        ndcgs_pop.append(dcg_p / idcg if idcg > 0 else 0.0)

# ── 5. Compile and Format Results ─────────────────────────────────────────────
print("\n" + "=" * 80)
print("FINAL EVALUATION METRICS REPORT")
print("=" * 80)

print(f"\n1. RATING PREDICTION ACCURACY (N={len(errors['hybrid_cf']):,} unseen test instances)")
print(f"{'Model / Algorithm':<26} {'RMSE':<10} {'MAE':<10} {'Status'}")
print("-" * 60)
results_table = []
for name, err_list in errors.items():
    e_arr = np.array(err_list)
    rmse = float(np.sqrt(np.mean(e_arr**2)))
    mae = float(np.mean(np.abs(e_arr)))
    status = "Baseline" if "mean" in name else "Collaborative Model"
    results_table.append((name, rmse, mae))
    print(f"{name:<26} {rmse:<10.4f} {mae:<10.4f} {status}")

n_ranking_users = len(precisions_hybrid)
print(f"\n2. RECOMMENDATION RANKING ACCURACY (K={K}, Relevant Threshold={REL_THRESH} Stars)")
print(f"   Evaluated across {n_ranking_users} users with >= 1 relevant item in test set.")
print(f"{'Metric':<18} {'Non-Personalized Popularity':<30} {'Hybrid CF Model':<20} {'Relative Lift'}")
print("-" * 80)

p_pop = np.mean(precisions_pop)
p_hyb = np.mean(precisions_hybrid)
r_pop = np.mean(recalls_pop)
r_hyb = np.mean(recalls_hybrid)
n_pop = np.mean(ndcgs_pop)
n_hyb = np.mean(ndcgs_hybrid)

print(f"{'Precision@10':<18} {p_pop:<30.4f} {p_hyb:<20.4f} {((p_hyb - p_pop)/p_pop)*100:+.1f}%")
print(f"{'Recall@10':<18} {r_pop:<30.4f} {r_hyb:<20.4f} {((r_hyb - r_pop)/r_pop)*100:+.1f}%")
print(f"{'NDCG@10':<18} {n_pop:<30.4f} {n_hyb:<20.4f} {((n_hyb - n_pop)/n_pop)*100:+.1f}%")

print("\n3. METHODOLOGICAL COMPARISON (Leakage vs. Leakage-Free):")
print("-" * 80)
print(f"{'Evaluation Pipeline':<35} {'Split Protocol':<25} {'RMSE (Hybrid)':<15} {'Integrity Status'}")
print("-" * 80)
print(f"{'Earlier Audit Evaluation':<35} {'Full-Data Precomputed':<25} {'0.6506':<15} {'NOT VALIDATED (Transductive Leakage)'}")
print(f"{'New Isolated Pipeline (Current)':<35} {'Strict 80/20 Isolated':<25} {f'{results_table[-1][1]:.4f}':<15} {'VALIDATED (Leakage-Free)'}")
print("=" * 80)
