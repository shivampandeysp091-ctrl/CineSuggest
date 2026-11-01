import "./Onboarding.css";
import "../components/MovieCard.css";
import { useState, useEffect } from "react";
import { useNavigate, Link } from "react-router-dom";
import { getCurrentUser, getScopedKey } from "../auth/auth";
import { api } from "../api/client";

const TARGET_COUNT = 8;

function Onboarding() {
  const navigate = useNavigate();
  const user = getCurrentUser();

  const [movies, setMovies] = useState([]);
  const [ratings, setRatings] = useState({});
  const [savingIds, setSavingIds] = useState({});
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState("");

  const userName =
    user?.name ||
    user?.username ||
    user?.fullName ||
    "Movie Lover";

  // Load existing ratings and fetch onboarding movies
  useEffect(() => {
    let isMounted = true;

    // Load any ratings from scoped localStorage
    try {
      const storedRatings = JSON.parse(
        localStorage.getItem(getScopedKey("movieRatings")) || "{}"
      );
      setRatings(storedRatings);
    } catch (e) {}

    // Hydrate ratings from backend API
    api.getRatings().then((res) => {
      if (isMounted && Array.isArray(res)) {
        const ratingMap = {};
        res.forEach((r) => {
          if (r.movie_id && r.rating) ratingMap[r.movie_id] = r.rating;
        });
        setRatings((prev) => ({ ...prev, ...ratingMap }));
        try {
          localStorage.setItem(
            getScopedKey("movieRatings"),
            JSON.stringify({ ...ratings, ...ratingMap })
          );
        } catch (_) {}
      }
    }).catch(() => {});

    async function loadOnboarding() {
      setLoading(true);
      setErrorMsg("");
      try {
        const data = await api.getOnboardingMovies(12);
        if (isMounted && Array.isArray(data) && data.length > 0) {
          setMovies(data);
        } else {
          // Fallback to top-rated if needed
          const fallback = await api.getTopRated(12);
          if (isMounted && Array.isArray(fallback)) {
            setMovies(fallback);
          }
        }
      } catch (err) {
        console.warn("Failed to fetch onboarding movies:", err);
        try {
          const fallback = await api.getTopRated(12);
          if (isMounted && Array.isArray(fallback)) {
            setMovies(fallback);
          }
        } catch (e2) {
          if (isMounted) setErrorMsg("Unable to load onboarding movies. Please try again.");
        }
      } finally {
        if (isMounted) setLoading(false);
      }
    }

    loadOnboarding();
    return () => {
      isMounted = false;
    };
  }, []);

  const ratedCount = Object.keys(ratings).length;
  const progressPercent = Math.min(100, Math.round((ratedCount / TARGET_COUNT) * 100));

  // Handle rating a movie via POST /ratings
  const handleRate = async (movieId, starValue) => {
    const numId = parseInt(movieId, 10);
    if (isNaN(numId)) return;

    // Optimistic state update
    const updated = { ...ratings, [movieId]: starValue };
    setRatings(updated);
    try {
      localStorage.setItem(getScopedKey("movieRatings"), JSON.stringify(updated));
    } catch (e) {}

    // Call backend POST /ratings/
    setSavingIds((prev) => ({ ...prev, [movieId]: true }));
    try {
      await api.rateMovie(numId, starValue);
    } catch (err) {
      console.warn(`Error submitting rating for movie ${numId}:`, err);
    } finally {
      setSavingIds((prev) => {
        const next = { ...prev };
        delete next[movieId];
        return next;
      });
    }
  };

  const handleFinish = () => {
    navigate("/recommendations");
  };

  return (
    <div className="onboarding-page">
      {/* ================= NAVBAR ================= */}
      <nav className="onboarding-navbar">
        <div className="logo">
          <span>🎬</span> CineSuggest
        </div>
        <div className="onboarding-user-info">
          <span>Welcome, <strong>{userName}</strong></span>
        </div>
      </nav>

      {/* ================= HEADER SECTION ================= */}
      <section className="onboarding-hero">
        <div className="onboarding-pill">✦ AI TASTE CALIBRATION</div>
        <h1>Rate 8 to 10 Movies You've Seen</h1>
        <p className="onboarding-desc">
          Help our machine learning recommender understand your taste. Rate any of the popular titles
          below from 1 to 5 stars, and we will personalize your recommendations immediately.
        </p>

        {/* ================= PROGRESS BAR ================= */}
        <div className="progress-card">
          <div className="progress-header">
            <div className="progress-counter">
              <span className="counter-number">{ratedCount}</span>
              <span className="counter-target">/ {TARGET_COUNT} rated</span>
            </div>
            <div className="progress-hint">
              {ratedCount >= TARGET_COUNT ? (
                <span className="hint-success">🎉 Excellent! Your AI profile is calibrated.</span>
              ) : (
                <span>Rate {TARGET_COUNT - ratedCount} more to unlock full personalization</span>
              )}
            </div>
          </div>

          <div className="progress-bar-track">
            <div
              className={`progress-bar-fill ${ratedCount >= TARGET_COUNT ? "complete" : ""}`}
              style={{ width: `${progressPercent}%` }}
            />
          </div>
        </div>
      </section>

      {/* ================= MOVIE CARDS ================= */}
      <section className="onboarding-grid-section">
        {loading ? (
          <p className="onboarding-loading">Loading popular movies for you...</p>
        ) : errorMsg ? (
          <div className="onboarding-error-box">
            <p>{errorMsg}</p>
            <button type="button" onClick={() => window.location.reload()}>Retry</button>
          </div>
        ) : (
          <div className="onboarding-grid">
            {movies.map((m) => {
              const currentRating = ratings[m.movie_id] || 0;
              const isSaving = savingIds[m.movie_id];
              const year = m.release_year || "";
              const genres = (m.genres || "").split("|").filter(Boolean).slice(0, 2).join(" • ");

              return (
                <div
                  key={m.movie_id}
                  className={`onboarding-card ${currentRating > 0 ? "is-rated" : ""}`}
                >
                  <div className="onboarding-poster-wrap">
                    {m.poster_url ? (
                      <img
                        src={m.poster_url}
                        alt={m.title}
                        className="onboarding-poster-img"
                        onError={(e) => { e.currentTarget.style.display = "none"; }}
                        loading="lazy"
                      />
                    ) : (
                      <div className="movie-card-placeholder">
                        <span className="placeholder-clapper">🎬</span>
                        <span className="placeholder-text">{m.title}</span>
                        {year && <span className="placeholder-year">({year})</span>}
                      </div>
                    )}

                    {m.tmdb_rating && (
                      <span className="onboarding-tmdb-badge">
                        ★ TMDB {m.tmdb_rating}
                      </span>
                    )}

                    {currentRating > 0 && (
                      <span className="onboarding-rated-tag">
                        ✓ {currentRating}/5
                      </span>
                    )}
                  </div>

                  <div className="onboarding-card-body">
                    <h3 className="onboarding-movie-title" title={m.title}>
                      {m.title}
                    </h3>
                    <p className="onboarding-movie-meta">
                      {[year, genres].filter(Boolean).join(" • ")}
                    </p>

                    {/* Interactive Star Rating */}
                    <div className="onboarding-rating-row">
                      <div className="onboarding-stars" role="radiogroup" aria-label={`Rate ${m.title}`}>
                        {[1, 2, 3, 4, 5].map((star) => (
                          <button
                            key={star}
                            type="button"
                            className={`onboarding-star-btn ${star <= currentRating ? "active" : ""}`}
                            onClick={() => handleRate(m.movie_id, star)}
                            title={`Rate ${star} out of 5 stars`}
                            aria-label={`Rate ${star} out of 5`}
                          >
                            ★
                          </button>
                        ))}
                      </div>
                      <span className="onboarding-star-feedback">
                        {isSaving ? "Saving..." : currentRating > 0 ? `${currentRating}★` : "Rate"}
                      </span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </section>

      {/* ================= STICKY BOTTOM ACTION BAR ================= */}
      <footer className="onboarding-footer">
        <div className="footer-content">
          <div className="footer-status">
            <span>
              {ratedCount >= TARGET_COUNT
                ? "Profile calibrated! You can continue or rate more movies."
                : `Rated ${ratedCount} of ${TARGET_COUNT} recommended movies.`}
            </span>
          </div>

          <div className="footer-buttons">
            <Link to="/recommendations" className="skip-link">
              Skip for now
            </Link>

            <button
              type="button"
              className={`finish-button ${ratedCount >= TARGET_COUNT ? "ready" : ""}`}
              onClick={handleFinish}
            >
              Continue to Recommendations →
            </button>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default Onboarding;
