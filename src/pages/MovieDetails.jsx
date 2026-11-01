import "./MovieDetails.css";
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { getCurrentUser, getScopedKey } from "../auth/auth";
import { api } from "../api/client";

function normalizeId(value) {
  return String(value || "")
    .toLowerCase()
    .replace(/[^a-z0-9]/g, "");
}

function MovieDetails() {
  const { id } = useParams();
  const [movie, setMovie] = useState(null);
  const [loading, setLoading] = useState(true);
  const [importing, setImporting] = useState(false);
  const user = getCurrentUser();

  const userName =
    user?.name || user?.username || user?.fullName || "User";

  const userInitial =
    userName.trim().charAt(0).toUpperCase() || "U";

  const [isSaved, setIsSaved] = useState(false);
  const [userRating, setUserRating] = useState(0);
  const [selectedRating, setSelectedRating] = useState(0);
  const [posterFailed, setPosterFailed] = useState(false);

  // 1. Fetch movie from backend (handles numeric ID or tmdb-xxx)
  useEffect(() => {
    let isMounted = true;
    setLoading(true);
    setPosterFailed(false);

    async function loadMovieDetails() {
      try {
        const rawId = String(id || "").trim();
        const isTmdbPrefix = rawId.toLowerCase().startsWith("tmdb-");

        if (isTmdbPrefix) {
          // It's a TMDB movie: e.g. "tmdb-550"
          const tmdbId = parseInt(rawId.replace(/^tmdb-/i, ""), 10);
          if (!isNaN(tmdbId)) {
            const tmdbMovie = await api.getTmdbMovie(tmdbId);
            if (isMounted && tmdbMovie) {
              const genresArr = typeof tmdbMovie.genres === "string"
                ? tmdbMovie.genres.split("|").map((g) => g.trim()).filter(Boolean)
                : (Array.isArray(tmdbMovie.genres) ? tmdbMovie.genres : []);

              setMovie({
                id: tmdbMovie.movie_id || `tmdb-${tmdbMovie.tmdb_id}`,
                numericId: tmdbMovie.movie_id || null,
                tmdbId: tmdbMovie.tmdb_id,
                title: tmdbMovie.title,
                year: tmdbMovie.release_year || (tmdbMovie.release_date ? tmdbMovie.release_date.slice(0, 4) : ""),
                tmdbRating: tmdbMovie.rating != null ? Number(tmdbMovie.rating).toFixed(1) : null,
                genres: genresArr.length ? genresArr : ["Feature"],
                poster: tmdbMovie.poster_url || null,
                backdrop: tmdbMovie.backdrop_url || tmdbMovie.poster_url || null,
                description: tmdbMovie.overview || "Overview coming soon.",
                cast: ["Information sourced from TMDB"],
                inCatalog: tmdbMovie.in_catalog === true,
                source: tmdbMovie.source || (tmdbMovie.in_catalog ? "movielens" : null),
              });
              setLoading(false);
              return;
            }
          }
        }

        const numId = parseInt(rawId, 10);
        if (!isNaN(numId)) {
          // Catalog movie lookup
          try {
            const backendMovie = await api.getMovie(numId);
            if (isMounted && backendMovie) {
              const genresArr = (backendMovie.genres || "").split("|").map((g) => g.trim()).filter(Boolean);
              setMovie({
                id: backendMovie.movie_id,
                numericId: backendMovie.movie_id,
                tmdbId: backendMovie.tmdb_id,
                title: backendMovie.title,
                year: backendMovie.release_year || "",
                tmdbRating: backendMovie.tmdb_rating ? Number(backendMovie.tmdb_rating).toFixed(1) : null,
                genres: genresArr.length ? genresArr : ["Feature"],
                poster: backendMovie.poster_url || null,
                backdrop: backendMovie.backdrop_url || backendMovie.poster_url || null,
                description: backendMovie.overview || "Discovered on CineSuggest.",
                cast: ["Cast information coming soon"],
                inCatalog: true,
                source: backendMovie.source || "movielens",
              });
              setLoading(false);
              return;
            }
          } catch (e) {
            // If getMovie failed, try tmdb lookup if it was a TMDB id
            try {
              const tmdbFallback = await api.getTmdbMovie(numId);
              if (isMounted && tmdbFallback) {
                const genresArr = typeof tmdbFallback.genres === "string"
                  ? tmdbFallback.genres.split("|").map((g) => g.trim()).filter(Boolean)
                  : [];
                setMovie({
                  id: tmdbFallback.movie_id || `tmdb-${tmdbFallback.tmdb_id}`,
                  numericId: tmdbFallback.movie_id || null,
                  tmdbId: tmdbFallback.tmdb_id,
                  title: tmdbFallback.title,
                  year: tmdbFallback.release_year || "",
                  tmdbRating: tmdbFallback.rating != null ? Number(tmdbFallback.rating).toFixed(1) : null,
                  genres: genresArr.length ? genresArr : ["Feature"],
                  poster: tmdbFallback.poster_url || null,
                  backdrop: tmdbFallback.backdrop_url || null,
                  description: tmdbFallback.overview || "",
                  cast: ["Sourced from TMDB"],
                  inCatalog: tmdbFallback.in_catalog === true,
                  source: tmdbFallback.source || null,
                });
                setLoading(false);
                return;
              }
            } catch (err2) {}
          }
        }

        // Try reading from saved movies
        const savedKey = getScopedKey("myList");
        const savedMovies = JSON.parse(localStorage.getItem(savedKey) || "[]");
        const found = savedMovies.find((m) => String(m.id) === rawId);
        if (isMounted && found) {
          setMovie({
            ...found,
            inCatalog: Boolean(found.numericId),
          });
        }
      } catch (err) {
        console.error("Error loading movie:", err);
      } finally {
        if (isMounted) setLoading(false);
      }
    }

    loadMovieDetails();
    return () => {
      isMounted = false;
    };
  }, [id]);

  // 2. Sync user rating and favorite status
  useEffect(() => {
    if (!movie) {
      setIsSaved(false);
      setUserRating(0);
      setSelectedRating(0);
      return;
    }

    const numId = movie.numericId;

    if (numId) {
      api.addWatchHistory(numId).catch(() => {});
      api.checkFavorite(numId).then((res) => {
        if (res && typeof res.is_favorite === "boolean") {
          setIsSaved(res.is_favorite);
        }
      }).catch(() => {});
    }

    // Save to user-scoped watch history
    try {
      const histKey = getScopedKey("watchHistory");
      const history = JSON.parse(localStorage.getItem(histKey) || "[]");
      const filtered = history.filter((m) => normalizeId(m.id) !== normalizeId(movie.id));
      filtered.unshift({
        id: movie.id,
        numericId: movie.numericId,
        title: movie.title,
        genres: movie.genres || [],
        poster: movie.poster,
        image: movie.poster,
        year: movie.year,
        tmdbRating: movie.tmdbRating,
      });
      localStorage.setItem(histKey, JSON.stringify(filtered.slice(0, 50)));
    } catch (e) {}

    // Load rating from backend and scoped localStorage
    try {
      const rateKey = getScopedKey("movieRatings");
      const ratings = JSON.parse(localStorage.getItem(rateKey) || "{}");
      const savedRating = ratings[movie.id] ?? (movie.numericId ? ratings[movie.numericId] : 0);
      const parsedRating = Number(savedRating);
      const validRating = parsedRating >= 1 && parsedRating <= 5 ? parsedRating : 0;
      setUserRating(validRating);
      setSelectedRating(validRating);

      // Also verify with backend user ratings if we have a numericId
      if (numId) {
        api.getRatings().then((res) => {
          if (Array.isArray(res)) {
            const foundRating = res.find((r) => r.movie_id === numId);
            if (foundRating && foundRating.rating) {
              const rVal = Number(foundRating.rating);
              setUserRating(rVal);
              setSelectedRating(rVal);
            }
          }
        }).catch(() => {});
      }
    } catch (error) {
      console.error("Unable to load rating:", error);
    }
  }, [movie?.id, movie?.numericId]);

  function toggleMyList() {
    if (!movie) return;

    const numId = movie.numericId;
    const nextSavedState = !isSaved;
    setIsSaved(nextSavedState);

    if (numId) {
      if (nextSavedState) {
        api.addFavorite(numId).catch((err) => console.warn("addFavorite err:", err));
      } else {
        api.removeFavorite(numId).catch((err) => console.warn("removeFavorite err:", err));
      }
    }

    try {
      const listKey = getScopedKey("myList");
      const storedMovies = JSON.parse(localStorage.getItem(listKey) || "[]");
      const savedMovies = Array.isArray(storedMovies) ? storedMovies : [];
      const updatedMovies = !nextSavedState
        ? savedMovies.filter((item) => normalizeId(item.id) !== normalizeId(movie.id))
        : [
            ...savedMovies,
            {
              id: movie.id,
              numericId: movie.numericId,
              title: movie.title,
              image: movie.poster,
              poster: movie.poster,
              tmdbRating: movie.tmdbRating,
              info: Array.isArray(movie.genres) ? movie.genres.join(" • ") : movie.genres,
              description: movie.description,
              year: movie.year,
              genres: movie.genres,
            },
          ];
      localStorage.setItem(listKey, JSON.stringify(updatedMovies));
    } catch (error) {
      console.error("Unable to update My List:", error);
    }
  }

  async function handleRatingSubmit() {
    if (!movie || selectedRating < 1 || selectedRating > 5) return;

    let targetMovieId = movie.numericId;

    // If not in catalog, import it from TMDB first!
    if (!movie.inCatalog && movie.tmdbId) {
      try {
        setImporting(true);
        const importRes = await api.importTmdbMovie(movie.tmdbId);
        if (importRes && importRes.movie_id) {
          targetMovieId = importRes.movie_id;
          setMovie((prev) => ({
            ...prev,
            numericId: importRes.movie_id,
            inCatalog: true,
            source: "tmdb_import",
          }));
        } else {
          alert("Could not import TMDB movie. Please try again.");
          return;
        }
      } catch (err) {
        console.error("TMDB import error:", err);
        alert("Could not import TMDB movie into catalog.");
        return;
      } finally {
        setImporting(false);
      }
    }

    if (targetMovieId) {
      api.rateMovie(targetMovieId, selectedRating).catch((err) => console.warn("rateMovie err:", err));
    }

    try {
      const rateKey = getScopedKey("movieRatings");
      const ratings = JSON.parse(localStorage.getItem(rateKey) || "{}");
      ratings[movie.id] = selectedRating;
      if (targetMovieId) ratings[targetMovieId] = selectedRating;
      localStorage.setItem(rateKey, JSON.stringify(ratings));
      setUserRating(selectedRating);
    } catch (error) {
      console.error("Unable to save rating:", error);
    }
  }

  return (
    <div className="movie-details-page">
      <nav className="navbar">
        <Link to="/home" className="logo">
          <span>🎬</span> CineSuggest
        </Link>

        <div className="nav-links">
          <Link to="/home">Discover</Link>
          <Link to="/recommendations">My Recommendations</Link>
          <Link to="/my-list">My List</Link>
          <Link to="/history">History</Link>
        </div>

        <Link to="/profile" className="profile-circle" title={userName}>
          {userInitial}
        </Link>
      </nav>

      {loading ? (
        <div className="movie-not-found">
          <p>Loading movie details...</p>
        </div>
      ) : !movie ? (
        <div className="movie-not-found">
          <h1>Movie details not found</h1>
          <p>
            This movie could not be found in the current catalog.
            Please return to Discover.
          </p>
          <Link to="/home">← Back to Discover</Link>
        </div>
      ) : (
        <>
          <section className="movie-hero">
            {/* BACKDROP */}
            {movie.backdrop && !posterFailed && (
              <div className="movie-backdrop">
                <img
                  src={movie.backdrop}
                  alt=""
                  onError={(e) => { e.currentTarget.style.display = "none"; }}
                />
              </div>
            )}

            <div className="movie-overlay" />

            <div className="movie-content">
              {/* POSTER */}
              <div className="movie-poster-large">
                {movie.poster && !posterFailed ? (
                  <img
                    src={movie.poster}
                    alt={movie.title + " poster"}
                    onError={() => setPosterFailed(true)}
                  />
                ) : (
                  <div className="details-neutral-placeholder">
                    <span className="placeholder-clapper-large">🎬</span>
                    <span className="placeholder-title-large">{movie.title}</span>
                    {movie.year && <span className="placeholder-year-large">({movie.year})</span>}
                  </div>
                )}
              </div>

              {/* INFO */}
              <div className="movie-info">
                <div className="movie-meta-header">
                  <p className="movie-label">MOVIE DETAILS</p>
                  {!movie.inCatalog ? (
                    <span className="tmdb-only-badge" title="This movie can be imported by rating it">
                      TMDB Movie (Rate to Import)
                    </span>
                  ) : movie.source === "tmdb_import" ? (
                    <span className="tmdb-only-badge" style={{ borderColor: "#10b981", color: "#34d399", background: "rgba(16, 185, 129, 0.1)" }} title="Imported by community">
                      Community Catalog
                    </span>
                  ) : null}
                </div>

                <h1>{movie.title}</h1>

                <div className="movie-meta">
                  {movie.year && <span>{movie.year}</span>}

                  {/* 3) TMDB Rating only when present, formatted with TMDB label */}
                  {movie.tmdbRating && (
                    <span className="movie-rating-badge" title="TMDB 10-scale Rating">
                      ★ TMDB {movie.tmdbRating}
                    </span>
                  )}

                  {/* User Rating badge if already rated */}
                  {userRating > 0 && (
                    <span className="movie-user-rating-badge" title="Your Rating">
                      ★ You: {userRating}/5
                    </span>
                  )}

                  {(() => {
                    const rawList = Array.isArray(movie.genres)
                      ? movie.genres
                      : (typeof movie.genres === "string" ? movie.genres.split("|") : []);
                    const cleaned = rawList
                      .map((g) => (typeof g === "string" ? g.trim() : ""))
                      .filter((g) => Boolean(g) && g !== "(no genres listed)" && g.toUpperCase() !== "IMAX");
                    return cleaned.length > 0 ? <span>{cleaned.join(" • ")}</span> : null;
                  })()}
                </div>

                <p className="movie-description">
                  {movie.description}
                </p>

                {/* 4) TMDB movie banner */}
                {!movie.inCatalog ? (
                  <div className="catalog-notice-box">
                    <span>ℹ️</span>
                    <p>
                      <strong>TMDB Movie:</strong> This title is not yet in our internal catalog.
                      Rate it below to add it to the catalog! Note: Collaborative AI predictions for this title will become active as more users rate it.
                    </p>
                  </div>
                ) : movie.source === "tmdb_import" ? (
                  <div className="catalog-notice-box" style={{ borderColor: "rgba(16, 185, 129, 0.3)" }}>
                    <span>✨</span>
                    <p>
                      <strong>Community Catalog:</strong> This movie was imported from TMDB. Your rating helps train future AI recommendations for this title.
                    </p>
                  </div>
                ) : null}

                <div className="movie-actions">
                  <button
                    type="button"
                    className={isSaved ? "list-button added" : "list-button"}
                    onClick={toggleMyList}
                  >
                    {isSaved ? "♥ Remove from My List" : "♡ Add to My List"}
                  </button>
                </div>

                {movie.cast?.length > 0 && (
                  <div className="cast-section">
                    <h3>Cast</h3>
                    <div className="cast-list">
                      {movie.cast.map((actor) => (
                        <span key={actor}>{actor}</span>
                      ))}
                    </div>
                  </div>
                )}

                {/* 4) RATING SECTION: Enabled for both catalog and TMDB movies */}
                <div className="rating-section">
                  <div className="rating-left">
                    <p className="rating-label">YOUR RATING</p>
                    <p className="rating-question">
                      {movie.inCatalog
                        ? "Rate this movie (1 to 5 stars)"
                        : "Rate to add this TMDB movie to catalog"}
                    </p>

                    <div className="rating-stars">
                      {[1, 2, 3, 4, 5].map((star) => (
                        <button
                          key={star}
                          type="button"
                          className={star <= selectedRating ? "star active" : "star"}
                          onClick={() => setSelectedRating(star)}
                          disabled={importing}
                          aria-label={`Rate ${star} out of 5`}
                          title={`Rate ${star} out of 5 stars`}
                        >
                          ★
                        </button>
                      ))}
                    </div>
                  </div>

                  <div className="rating-middle">
                    <p className="rating-number">
                      {userRating || "—"}
                      <span>/5</span>
                    </p>
                    <p className="rating-status">
                      {userRating > 0 ? "Your rating" : "Not rated"}
                    </p>
                  </div>

                  {/* 4) Rate button with import indicator */}
                  <div className="rate-button-container">
                    <button
                      type="button"
                      className="submit-rating"
                      onClick={handleRatingSubmit}
                      disabled={selectedRating === 0 || importing}
                    >
                      {importing
                        ? "Importing..."
                        : movie.inCatalog
                        ? "Rate Movie"
                        : "Import & Rate"}
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </section>

          <div className="back-section">
            <Link to="/home">← Back to Discover</Link>
          </div>
        </>
      )}
    </div>
  );
}

export default MovieDetails;