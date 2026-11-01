# -*- coding: utf-8 -*-
"""
backend/scripts/audit_sparse_weighting.py
==========================================
Controlled Evaluation of Sparse-User Weighting in RRF:
Compares:
1. Equal Weights: UserCF 1.0, ItemCF 1.0, SVD 1.0
2. Sparse Weights: UserCF 0.20, ItemCF 0.60, SVD 0.20

Evaluated on:
- Sparse User Group (Simulated Given N=2 Ratings)
- Mature User Group (Full 80% Train, N >= 16 Ratings)

Identical candidate catalog, identical holdout test sets, identical evaluation metrics.
"""

import os
import sys
import math
import numpy as np
import pandas as pd

ML_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "ml")
K = 10
K_RRF = 60
CAND_DEPTH = 50
REL_THRESH = 4.0
MIN_CANDIDATE_COUNT = 10
SEED = 42

df_ratings = pd.read_csv(os.path.join(ML_DIR, "ratings.csv"))
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

df_train = df_ratings.loc[np.concatenate(train_indices_list)].reset_index(drop=True)
df_test = df_ratings.loc[np.concatenate(test_indices_list)].reset_index(drop=True)

# Training-only matrices
global_mean_train = float(df_train["rating"].mean())
R_train = np.full((n_users, n_items), np.nan, dtype=np.float32)
for _, row in df_train.iterrows():
    R_train[u2i[int(row["userId"])], m2j[int(row["movieId"])]] = float(row["rating"])

mask_train = ~np.isnan(R_train)
train_counts = mask_train.sum(axis=0)
eligible_catalog_mask = (train_counts >= MIN_CANDIDATE_COUNT)
n_eligible_catalog = int(eligible_catalog_mask.sum())

user_means_train = np.full(n_users, global_mean_train, dtype=np.float32)
for ui in range(n_users):
    vals = R_train[ui, mask_train[ui]]
    if len(vals) > 0:
        user_means_train[ui] = float(np.mean(vals))

Rc_train = np.where(mask_train, R_train - user_means_train[:, None], 0.0).astype(np.float32)
user_norm_train = np.linalg.norm(Rc_train, axis=1)
item_norm_train = np.linalg.norm(Rc_train, axis=0)

denom_item = item_norm_train[:, None] * item_norm_train[None, :] + 1e-9
item_sim_mat = (Rc_train.T @ Rc_train) / denom_item
np.fill_diagonal(item_sim_mat, 0.0)
pos_item_sim_mat = np.maximum(0.0, item_sim_mat)

U_svd, S_svd, Vt_svd = np.linalg.svd(Rc_train, full_matrices=False)
K_SVD = 20
P_train = U_svd[:, :K_SVD] * S_svd[:K_SVD]
Q_train = Vt_svd[:K_SVD, :].T

item_biases_train = np.zeros(n_items, dtype=np.float32)
for j in range(n_items):
    u_idx = np.where(mask_train[:, j])[0]
    if len(u_idx) > 0:
        item_biases_train[j] = float(np.mean(R_train[u_idx, j] - user_means_train[u_idx]))

test_by_user = {}
for _, row in df_test.iterrows():
    test_by_user.setdefault(int(row["userId"]), []).append((int(row["movieId"]), float(row["rating"])))


def run_weight_comparison(sparse_simulation=False):
    rng_sim = np.random.default_rng(SEED + (123 if sparse_simulation else 456))
    
    configs = ["Equal Weights (1.0, 1.0, 1.0)", "Sparse Weights (0.20, 0.60, 0.20)"]
    prec_lists = {cfg: [] for cfg in configs}
    rec_lists = {cfg: [] for cfg in configs}
    ndcg_lists = {cfg: [] for cfg in configs}
    all_recs = {cfg: set() for cfg in configs}
    
    for uid in all_user_ids:
        ui = u2i[uid]
        full_train_j = np.where(mask_train[ui])[0]
        
        if sparse_simulation:
            if len(full_train_j) <= 2:
                train_j = full_train_j
            else:
                shuf = rng_sim.permutation(full_train_j)
                train_j = shuf[:2]
        else:
            train_j = full_train_j
            
        if len(train_j) == 0:
            continue
            
        train_ratings = R_train[ui, train_j]
        u_mean = float(np.mean(train_ratings))
        train_rc = np.zeros(n_items, dtype=np.float32)
        train_rc[train_j] = train_ratings - u_mean
        
        test_items = test_by_user.get(uid, [])
        if not test_items:
            continue
            
        # 1. User CF
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
            
        # 2. Item CF
        sim_sub = pos_item_sim_mat[train_j, :]
        sim_sum = sim_sub.sum(axis=0)
        dev_r = train_rc[train_j]
        weighted_dev = sim_sub.T @ dev_r
        p_ib = np.where(sim_sum > 0, u_mean + weighted_dev / (sim_sum + 0.5), np.nan)
        
        # 3. SVD
        if len(train_j) > 0:
            Q_r = Q_train[train_j]
            rc_r = train_rc[train_j]
            reg = 2.0 * np.eye(K_SVD)
            p_u = np.linalg.solve(Q_r.T @ Q_r + reg, Q_r.T @ rc_r)
            p_svd = u_mean + item_biases_train + (p_u @ Q_train.T)
        else:
            p_svd = np.full(n_items, u_mean)
            
        # Candidate eligibility
        base_eligible = eligible_catalog_mask.copy()
        base_eligible[train_j] = False
        
        # Affinity check
        min_sim = 0.25 if len(train_j) <= 3 else 0.15
        has_collab = (~np.isnan(p_ub)) | (sim_sum >= min_sim)
        
        def rank_cands(score_arr, top_n=CAND_DEPTH):
            cand_mask = base_eligible & has_collab & (~np.isnan(score_arr)) & np.isfinite(score_arr)
            cand_j = np.where(cand_mask)[0]
            if len(cand_j) == 0:
                return []
            cand_scores = score_arr[cand_j]
            top_local = np.argsort(-cand_scores)[:top_n]
            return cand_j[top_local].tolist()
            
        list_ub = rank_cands(p_ub)
        list_ib = rank_cands(p_ib)
        list_svd = rank_cands(p_svd)
        
        # Build RRF with Equal vs Sparse weights
        for cfg, weights in [
            ("Equal Weights (1.0, 1.0, 1.0)", (1.0, 1.0, 1.0)),
            ("Sparse Weights (0.20, 0.60, 0.20)", (0.20, 0.60, 0.20)),
        ]:
            rrf_map = {}
            for w, cand_list in zip(weights, (list_ub, list_ib, list_svd)):
                for r_idx, j in enumerate(cand_list, 1):
                    rrf_map[j] = rrf_map.get(j, 0.0) + w * (1.0 / (K_RRF + r_idx))
                    
            if rrf_map:
                sorted_items = sorted(
                    rrf_map.items(),
                    key=lambda x: (x[1], train_counts[x[0]], -int(all_movie_ids[x[0]])),
                    reverse=True
                )
                top_recs = [j for j, _ in sorted_items[:K]]
            else:
                top_recs = []
                
            all_recs[cfg].update(top_recs)
            
            # Ranking metrics on test items
            rel_test_j = set(m2j[mid] for mid, r_true in test_items if mid in m2j and r_true >= REL_THRESH)
            if len(rel_test_j) > 0:
                idcg = sum(1.0 / math.log2(rk + 2) for rk in range(min(len(rel_test_j), K)))
                hits = len(rel_test_j.intersection(top_recs))
                prec = hits / K
                rec = hits / len(rel_test_j)
                dcg = sum(1.0 / math.log2(rk + 2) for rk, j in enumerate(top_recs) if j in rel_test_j)
                ndcg = dcg / idcg if idcg > 0 else 0.0
                
                prec_lists[cfg].append(prec)
                rec_lists[cfg].append(rec)
                ndcg_lists[cfg].append(ndcg)
                
    results = {}
    for cfg in configs:
        cov_pct = (len(all_recs[cfg]) / n_eligible_catalog) * 100.0
        results[cfg] = {
            "prec": float(np.mean(prec_lists[cfg])),
            "rec": float(np.mean(rec_lists[cfg])),
            "ndcg": float(np.mean(ndcg_lists[cfg])),
            "cov_pct": cov_pct,
            "unique_items": len(all_recs[cfg]),
        }
    return results


def main():
    print("=" * 90)
    print("CONTROLLED EVALUATION: EQUAL WEIGHTS VS SPARSE WEIGHTS IN RRF")
    print("=" * 90)
    
    print("\n1. SPARSE USER GROUP (Simulated Given N=2 Ratings, Identical 20% Holdout Test):")
    print("-" * 90)
    print(f"{'Configuration':<35} {'Prec@10':<10} {'Rec@10':<10} {'NDCG@10':<10} {'CatCov%':<10} {'Unique Items'}")
    print("-" * 90)
    sparse_res = run_weight_comparison(sparse_simulation=True)
    for cfg, m in sparse_res.items():
        print(f"{cfg:<35} {m['prec']:.4f}     {m['rec']:.4f}     {m['ndcg']:.4f}     {m['cov_pct']:.1f}%      {m['unique_items']}")
        
    print("\n2. MATURE USER GROUP (Full 80% Train, N >= 16 Ratings):")
    print("-" * 90)
    print(f"{'Configuration':<35} {'Prec@10':<10} {'Rec@10':<10} {'NDCG@10':<10} {'CatCov%':<10} {'Unique Items'}")
    print("-" * 90)
    mature_res = run_weight_comparison(sparse_simulation=False)
    for cfg, m in mature_res.items():
        print(f"{cfg:<35} {m['prec']:.4f}     {m['rec']:.4f}     {m['ndcg']:.4f}     {m['cov_pct']:.1f}%      {m['unique_items']}")
    print("=" * 90)


if __name__ == "__main__":
    main()
