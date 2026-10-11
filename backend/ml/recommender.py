"""
CineSuggest AI - recommender (backend version 4)
================================================
Ye file backend/ml/recommender.py ki jagah jaati hai. Purane function names aur columns
same rakhe gaye hain, to routes/recommendations.py na toote.

PUBLIC FUNCTIONS
    get_hybrid_recommendations(user_id, n=10)        # MovieLens user (1-610)
    get_new_user_recommendations(user_ratings, n=10) # app ka naya user: [{"movieId":1,"rating":5.0}, ...]
    get_user_based_recommendations(user_id, n=10)    # debug
    get_item_based_recommendations(user_id, n=10)    # debug
    get_svd_recommendations(user_id, n=10)           # debug
    popular_movies(n=10)                             # fallback
    warmup()   # server start par ek baar chalao (data + matrices load)
    reload()   # naya model/data aane par

OUTPUT (DataFrame)
    hybrid:   movieId, title, genres, user_score, item_score, svd_score, hybrid_score, match_percentage
              (*_score = us model ki predicted rating 0.5-5, hybrid_score = blend, match_percentage 0-100)
    new user: movieId, title, genres, recommendation_score, match_percentage, predicted_rating
              (recommendation_score = match_percentage, purane route ke liye)
    NaN kahin nahi aata (JSON safe): missing values None hoti hain.

FILES (isi folder mein)
    movies.csv, ratings.csv (ya ratings.csv.csv)
    svd_factors.npz  (best: surprise ki zarurat nahi)  YA  svd_final.pkl / svd_model.pkl (surprise chahiye)

RULES
    max n movies | predicted rating >= min_rating (default 3.5) | movie ki kam se kam 10 ratings
    | already-rated aur exclude_movie_ids (jaise watch history) nahi aayengi.
"""
import os

import numpy as np
import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

MIN_RATING, MAX_RATING = 0.5, 5.0

# ---- Tunable (evaluate_models ke baad update karo) ----
DEFAULT_MIN_RATING = 3.5            # isse kam predicted rating wali movie recommend nahi hogi
DEFAULT_MIN_MOVIE_RATINGS = 10      # itni ratings se kam wali movies skip (prediction bharosemand nahi)
DEFAULT_WEIGHTS = (0.3, 0.3, 0.4)   # (user-based, item-based, svd)
K_USER, K_ITEM = 30, 20             # neighbors
USER_MIN_SUPPORT = 3                # user-based: kam se kam itne neighbors ne movie rate ki ho
USER_SHRINK_K = 2.0                 # kam support par prediction user ki average ki taraf
PRIOR_M = 5                         # naye user ki average ko global average ki taraf khichne ke pseudo-ratings
SVD_FOLD_LAMBDA = 2.0               # naye user ke SVD vector ki ridge regularization

OUT_STD = ["movieId", "title", "genres", "predicted_rating", "match_percentage"]
OUT_HYBRID = ["movieId", "title", "genres", "user_score", "item_score",
              "svd_score", "hybrid_score", "match_percentage"]
OUT_NEW = ["movieId", "title", "genres", "recommendation_score", "match_percentage", "predicted_rating"]

_S = {}


def _first_existing(*names):
    for name in names:
        path = os.path.join(BASE_DIR, name)
        if os.path.exists(path):
            return path
    raise FileNotFoundError(f"{names} mein se koi file {BASE_DIR} mein nahi mili")


# ------------------------------------------------------------------ SVD factors
class _Factors:
    """SVD ke learned factors (surprise ke bina bhi chalte hain)."""

    def __init__(self, mu, bu, bi, pu, qi, user_ids, item_ids):
        self.mu = float(mu)
        self.bu = np.asarray(bu, dtype=np.float64)
        self.bi = np.asarray(bi, dtype=np.float64)
        self.pu = np.asarray(pu, dtype=np.float64)
        self.qi = np.asarray(qi, dtype=np.float64)
        self.uid_to_inner = {int(u): i for i, u in enumerate(user_ids)}
        self.iid_to_inner = {int(m): i for i, m in enumerate(item_ids)}


def _load_factors():
    npz_path = os.path.join(BASE_DIR, "svd_factors.npz")
    if os.path.exists(npz_path):
        z = np.load(npz_path, allow_pickle=False)
        return _Factors(z["mu"], z["bu"], z["bi"], z["pu"], z["qi"], z["user_ids"], z["item_ids"])

    path = _first_existing("svd_final.pkl", "svd_model.pkl")
    try:
        import joblib
        model = joblib.load(path)       # joblib aur plain pickle dono padh leta hai
    except ImportError:
        import pickle
        with open(path, "rb") as f:
            model = pickle.load(f)
    ts = model.trainset
    users = [ts.to_raw_uid(i) for i in ts.all_users()]
    items = [ts.to_raw_iid(i) for i in ts.all_items()]
    return _Factors(ts.global_mean, model.bu, model.bi, model.pu, model.qi, users, items)


# ------------------------------------------------------------------------ state
def _load():
    if _S:
        return _S
    movies = pd.read_csv(_first_existing("movies.csv"))
    ratings = pd.read_csv(_first_existing("ratings.csv", "ratings.csv.csv"))

    uim = ratings.pivot_table(index="userId", columns="movieId", values="rating")
    user_ids = uim.index.values
    movie_ids = uim.columns.values
    R = uim.values.astype(np.float32)                      # NaN = unrated
    mask = ~np.isnan(R)
    means = uim.mean(axis=1).values.astype(np.float32)
    Rc = np.where(mask, R - means[:, None], 0).astype(np.float32)   # mean-centered, unrated = 0

    factors = _load_factors()
    k = factors.qi.shape[1]
    Q = np.zeros((len(movie_ids), k))
    B = np.zeros(len(movie_ids))
    known = np.zeros(len(movie_ids), dtype=bool)
    for j, mid in enumerate(movie_ids):
        inner = factors.iid_to_inner.get(int(mid))
        if inner is not None:
            Q[j] = factors.qi[inner]
            B[j] = factors.bi[inner]
            known[j] = True

    _S.update(
        movies=movies,
        movie_info=movies.drop_duplicates("movieId").set_index("movieId")[["title", "genres"]],
        user_ids=user_ids,
        user_index={int(u): i for i, u in enumerate(user_ids)},
        movie_ids=movie_ids,
        col_index={int(m): j for j, m in enumerate(movie_ids)},
        R=R, mask=mask, means=means, Rc=Rc,
        user_norm=np.linalg.norm(Rc, axis=1),
        item_norm=np.linalg.norm(Rc, axis=0),
        counts=mask.sum(axis=0),
        item_mean=np.where(mask.sum(axis=0) > 0, np.nansum(np.where(mask, R, 0), axis=0) / np.maximum(mask.sum(axis=0), 1), np.nan),
        global_mean=float(ratings["rating"].mean()),
        factors=factors, Q=Q, B=B, known=known,
    )
    return _S


def warmup():
    """FastAPI startup par ek baar chalao taaki pehli request slow na ho."""
    _load()
    return True


def reload():
    _S.clear()


# --------------------------------------------------------------------- profiles
def _profile_known_user(S, user_id):
    ui = S["user_index"].get(int(user_id))
    if ui is None:
        raise ValueError(f"User {user_id} does not exist in MovieLens ratings.")
    return dict(rated=S["mask"][ui].copy(), mean=float(S["means"][ui]), rc=S["Rc"][ui].copy(),
                raw=S["R"][ui].copy(), self_idx=ui, user_id=int(user_id))


def _profile_from_ratings(S, user_ratings):
    """App ke naye user ki ratings [{"movieId", "rating"}] se profile. Catalog ke bahar ki movies ignore."""
    n_items = len(S["movie_ids"])
    raw = np.full(n_items, np.nan, dtype=np.float32)
    for item in user_ratings or []:
        j = S["col_index"].get(int(item["movieId"]))
        if j is not None:
            raw[j] = float(item["rating"])
    rated = ~np.isnan(raw)
    if not rated.any():
        return None
    # Kam ratings par average ko global average ki taraf khicho, warna ek hi rating (jaise 5.0)
    # se mean = 5.0 ho jaata hai aur centered rating 0 -> koi signal nahi.
    total, cnt = float(raw[rated].sum()), int(rated.sum())
    mean = (total + PRIOR_M * S["global_mean"]) / (cnt + PRIOR_M)
    rc = np.where(rated, raw - mean, 0).astype(np.float32)
    return dict(rated=rated, mean=float(mean), rc=rc, raw=raw, self_idx=None, user_id=None)


# -------------------------------------------------------------------- predictors
def _user_based(S, p, k=K_USER):
    n_items = len(p["rc"])
    nan = np.full(n_items, np.nan)
    nrm = float(np.linalg.norm(p["rc"]))
    if nrm == 0:
        return nan
    sims = (S["Rc"] @ p["rc"]) / (S["user_norm"] * nrm + 1e-9)
    if p["self_idx"] is not None:
        sims[p["self_idx"]] = -1.0
    k = min(k, len(sims) - 1)
    top = np.argpartition(-sims, k - 1)[:k]
    top = top[sims[top] > 0]
    if top.size == 0:
        return nan
    w = sims[top].astype(np.float32)
    M = S["mask"][top].astype(np.float32)
    num = w @ S["Rc"][top]
    den = w @ M
    support = M.sum(axis=0)
    shrink = support / (support + USER_SHRINK_K)
    with np.errstate(divide="ignore", invalid="ignore"):
        pred = p["mean"] + shrink * (num / den)
    pred = pred.astype(np.float64)
    pred[(den <= 0) | (support < USER_MIN_SUPPORT)] = np.nan
    return pred


def _item_based(S, p, k=K_ITEM):
    r_idx = np.where(p["rated"])[0]
    rc_r = p["rc"][r_idx]
    Rc = S["Rc"]
    sims = Rc[:, r_idx].T @ Rc                                           # (n_rated, n_items)
    sims = sims / (S["item_norm"][r_idx][:, None] * S["item_norm"][None, :] + 1e-9)
    sims = sims.T                                                         # (n_items, n_rated)
    kk = min(k, sims.shape[1])
    top = np.argpartition(-sims, kk - 1, axis=1)[:, :kk]
    s_top = np.take_along_axis(sims, top, axis=1)
    s_top = np.where(s_top > 0, s_top, 0)
    den = s_top.sum(axis=1)
    num = (s_top * rc_r[top]).sum(axis=1)
    pred = np.where(den > 0, p["mean"] + num / np.where(den > 0, den, 1), np.nan)
    return pred.astype(np.float64)


def _svd(S, p):
    f, Q, B = S["factors"], S["Q"], S["B"]
    inner = f.uid_to_inner.get(p["user_id"]) if p["user_id"] is not None else None
    if inner is not None:                       # model ne ye user train time par dekha hai
        bu, pu = f.bu[inner], f.pu[inner]
    else:                                       # naya user: ridge regression se vector nikalo (retrain nahi)
        idx = np.where(p["rated"] & S["known"])[0]
        if idx.size == 0:
            return np.full(len(B), np.nan)
        y = p["raw"][idx].astype(np.float64) - f.mu - B[idx]
        X = np.hstack([np.ones((idx.size, 1)), Q[idx]])
        A = X.T @ X + SVD_FOLD_LAMBDA * np.eye(X.shape[1])
        theta = np.linalg.solve(A, X.T @ y)
        bu, pu = theta[0], theta[1:]
    est = f.mu + bu + B + Q @ pu
    est = np.where(S["known"], est, np.nan)     # jo movie SVD ne dekhi hi nahi, uska score nahi
    return est


def _blend(preds, weights):
    """preds: (n_items, 3). Jo model score nahi de paya uska weight 0 (baaki ka average)."""
    w = np.asarray(weights, dtype=float)[None, :] * ~np.isnan(preds)
    tw = w.sum(axis=1)
    with np.errstate(divide="ignore", invalid="ignore"):
        out = (np.nan_to_num(preds) * w).sum(axis=1) / tw
    out[tw == 0] = np.nan
    return out


# ------------------------------------------------------------------------ output
def _clean(df):
    """NaN -> None (FastAPI JSON NaN par fail hota hai)."""
    return df.astype(object).where(df.notna(), None)


def _match(pred):
    return np.round((np.clip(pred, MIN_RATING, MAX_RATING) - MIN_RATING) / (MAX_RATING - MIN_RATING) * 100, 1)


def _top_indices(S, score, rated, n, min_ratings, min_rating, exclude_movie_ids):
    pred = np.clip(score, MIN_RATING, MAX_RATING)
    ok = (~rated) & (S["counts"] >= min_ratings) & ~np.isnan(score) & (pred >= min_rating)
    if exclude_movie_ids:
        for mid in exclude_movie_ids:
            j = S["col_index"].get(int(mid))
            if j is not None:
                ok[j] = False
    idx = np.where(ok)[0]
    return idx[np.argsort(-pred[idx], kind="stable")][:n], pred


def _info(S, idx):
    mids = S["movie_ids"][idx]
    info = S["movie_info"].reindex(mids)
    return mids, info["title"].values, info["genres"].values


def _empty(cols):
    return pd.DataFrame(columns=cols)


def _standard(S, p, score, n, min_ratings, min_rating, exclude):
    idx, pred = _top_indices(S, score, p["rated"], n, min_ratings, min_rating, exclude)
    if idx.size == 0:
        return _empty(OUT_STD)
    mids, titles, genres = _info(S, idx)
    df = pd.DataFrame({"movieId": mids.astype(int), "title": titles, "genres": genres,
                       "predicted_rating": np.round(pred[idx], 2), "match_percentage": _match(pred[idx])})
    return _clean(df)[OUT_STD]


def _hybrid_frame(S, p, n, weights, min_ratings, min_rating, exclude):
    u, i, s = _user_based(S, p), _item_based(S, p), _svd(S, p)
    preds = np.column_stack([u, i, s])
    blend = _blend(preds, weights)
    idx, hyb = _top_indices(S, blend, p["rated"], n, min_ratings, min_rating, exclude)
    return idx, hyb, u, i, s


# ---------------------------------------------------------------- public: hybrid
def get_hybrid_recommendations(user_id, n=10, weights=None, min_ratings=DEFAULT_MIN_MOVIE_RATINGS,
                               min_rating=DEFAULT_MIN_RATING, exclude_movie_ids=None):
    """MovieLens user (1-610) ke liye hybrid recommendations."""
    S = _load()
    p = _profile_known_user(S, user_id)
    idx, hyb, u, i, s = _hybrid_frame(S, p, n, weights or DEFAULT_WEIGHTS, min_ratings, min_rating, exclude_movie_ids)
    if idx.size == 0:
        return _empty(OUT_HYBRID)
    mids, titles, genres = _info(S, idx)
    df = pd.DataFrame({
        "movieId": mids.astype(int), "title": titles, "genres": genres,
        "user_score": np.round(np.clip(u[idx], MIN_RATING, MAX_RATING), 2),
        "item_score": np.round(np.clip(i[idx], MIN_RATING, MAX_RATING), 2),
        "svd_score": np.round(np.clip(s[idx], MIN_RATING, MAX_RATING), 2),
        "hybrid_score": np.round(hyb[idx], 2),
        "match_percentage": _match(hyb[idx]),
    })
    return _clean(df)[OUT_HYBRID]


# ------------------------------------------------------------- public: new user
def get_new_user_recommendations(user_ratings, n=10, weights=None, min_ratings=DEFAULT_MIN_MOVIE_RATINGS,
                                 min_rating=DEFAULT_MIN_RATING, exclude_movie_ids=None):
    """
    App ke naye user ke liye (retrain ke bina).
    user_ratings: [{"movieId": 1, "rating": 5.0}, ...]  (MovieLens movieId)
    Catalog ke bahar ki movies ignore hoti hain. Koi bhi rated movie catalog mein na ho to empty DataFrame.
    """
    S = _load()
    p = _profile_from_ratings(S, user_ratings)
    if p is None:
        return _empty(OUT_NEW)
    idx, hyb, _, _, _ = _hybrid_frame(S, p, n, weights or DEFAULT_WEIGHTS, min_ratings, min_rating, exclude_movie_ids)
    if idx.size == 0:
        return _empty(OUT_NEW)
    mids, titles, genres = _info(S, idx)
    match = _match(hyb[idx])
    df = pd.DataFrame({"movieId": mids.astype(int), "title": titles, "genres": genres,
                       "recommendation_score": match, "match_percentage": match,
                       "predicted_rating": np.round(hyb[idx], 2)})
    return _clean(df)[OUT_NEW]


# --------------------------------------------------------- public: single models
def get_user_based_recommendations(user_id, n=10, min_ratings=DEFAULT_MIN_MOVIE_RATINGS,
                                   min_rating=DEFAULT_MIN_RATING, exclude_movie_ids=None):
    S = _load()
    p = _profile_known_user(S, user_id)
    return _standard(S, p, _user_based(S, p), n, min_ratings, min_rating, exclude_movie_ids)


def get_item_based_recommendations(user_id, n=10, min_ratings=DEFAULT_MIN_MOVIE_RATINGS,
                                   min_rating=DEFAULT_MIN_RATING, exclude_movie_ids=None):
    S = _load()
    p = _profile_known_user(S, user_id)
    return _standard(S, p, _item_based(S, p), n, min_ratings, min_rating, exclude_movie_ids)


def get_svd_recommendations(user_id, n=10, min_ratings=DEFAULT_MIN_MOVIE_RATINGS,
                            min_rating=DEFAULT_MIN_RATING, exclude_movie_ids=None):
    S = _load()
    p = _profile_known_user(S, user_id)
    return _standard(S, p, _svd(S, p), n, min_ratings, min_rating, exclude_movie_ids)


# --------------------------------------------------------------------- fallback
def popular_movies(n=10, min_ratings=50, exclude_movie_ids=None):
    """Fallback (jab personalized list na bane): zyada rating wali + achhi average wali movies."""
    S = _load()
    cnt = S["counts"].astype(float)
    gm = S["global_mean"]
    im = np.nan_to_num(S["item_mean"], nan=gm)
    bayes = (cnt * im + 10 * gm) / (cnt + 10)
    ok = cnt >= min_ratings
    if exclude_movie_ids:
        for mid in exclude_movie_ids:
            j = S["col_index"].get(int(mid))
            if j is not None:
                ok[j] = False
    idx = np.where(ok)[0]
    idx = idx[np.argsort(-bayes[idx], kind="stable")][:n]
    if idx.size == 0:
        return _empty(OUT_STD)
    mids, titles, genres = _info(S, idx)
    df = pd.DataFrame({"movieId": mids.astype(int), "title": titles, "genres": genres,
                       "predicted_rating": np.round(bayes[idx], 2), "match_percentage": _match(bayes[idx])})
    return _clean(df)[OUT_STD]
