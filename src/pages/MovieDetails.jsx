import "./MovieDetails.css";
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { getCurrentUser } from "../auth/auth";
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
                });
                setLoading(false);
                return;
              }
            } catch (err2) {}
          }
        }

        // Try reading from saved movies
        const savedMovies = JSON.parse(localStorage.getItem("myList") || "[]");
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

    // Save to localStorage watch history
    try {
      const history = JSON.parse(localStorage.getItem("watchHistory") || "[]");
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
      localStorage.setItem("watchHistory", JSON.stringify(filtered.slice(0, 50)));
    } catch (e) {}

    // Load rating from localStorage
    try {
      const ratings = JSON.parse(localStorage.getItem("movieRatings") || "{}");
      const savedRating = ratings[movie.id] ?? localStorage.getItem("movie-rating-" + movie.id) ?? 0;
      const parsedRating = Number(savedRating);
      const validRating = parsedRating >= 1 && parsedRating <= 5 ? parsedRating : 0;
      setUserRating(validRating);
      setSelectedRating(validRating);
    } catch (error) {
      console.error("Unable to load rating:", error);
    }
  }, [movie?.id]);

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
      const storedMovies = JSON.parse(localStorage.getItem("myList") || "[]");
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
      localStorage.setItem("myList", JSON.stringify(updatedMovies));
    } catch (error) {
      console.error("Unable to update My List:", error);
    }
  }

  function handleRatingSubmit() {
    if (!movie || selectedRating < 1 || selectedRating > 5) return;

    if (!movie.inCatalog) {
      alert("Ye movie abhi AI catalog mein nahi hai. Isse rate nahi kiya ja sakta.");
      return;
    }

    const numId = movie.numericId;
    if (numId) {
      api.rateMovie(numId, selectedRating).catch((err) => console.warn("rateMovie err:", err));
    }

    try {
      const ratings = JSON.parse(localStorage.getItem("movieRatings") || "{}");
      ratings[movie.id] = selectedRating;
      localStorage.setItem("movieRatings", JSON.stringify(ratings));
      localStorage.setItem("movie-rating-" + movie.id, String(selectedRating));
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
                  {!movie.inCatalog && (
                    <span className="tmdb-only-badge" title="Ye movie abhi AI catalog mein nahi hai">
                      TMDB Only (View Only)
                    </span>
                  )}
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

                  {movie.genres?.length > 0 && (
                    <span>{movie.genres.join(" • ")}</span>
                  )}
                </div>

                <p className="movie-description">
                  {movie.description}
                </p>

                {/* 4) TMDB-only movie banner if not in AI catalog */}
                {!movie.inCatalog && (
                  <div className="catalog-notice-box">
                    <span>ℹ️</span>
                    <p>
                      <strong>TMDB-Only Movie:</strong> Ye movie abhi CineSuggest ke AI catalog mein nahi hai.
                      Aap iske details dekh sakte hain, par ratings aur AI recommendations ke liye ye movie abhi uplabdh nahi hai.
                    </p>
                  </div>
                )}

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

                {/* 4) RATING SECTION: Hide/disable if in_catalog is false */}
                <div className={`rating-section ${!movie.inCatalog ? "rating-disabled" : ""}`}>
                  <div className="rating-left">
                    <p className="rating-label">YOUR RATING</p>
                    <p className="rating-question">
                      {movie.inCatalog ? "Rate this movie (1 to 5 stars)" : "AI Catalog Rating (Disabled)"}
                    </p>

                    <div className="rating-stars">
                      {[1, 2, 3, 4, 5].map((star) => (
                        <button
                          key={star}
                          type="button"
                          className={star <= selectedRating ? "star active" : "star"}
                          onClick={() => {
                            if (movie.inCatalog) {
                              setSelectedRating(star);
                            }
                          }}
                          disabled={!movie.inCatalog}
                          aria-label={`Rate ${star} out of 5`}
                          title={
                            movie.inCatalog
                              ? `Rate ${star} out of 5`
                              : "Ye movie abhi AI catalog mein nahi hai"
                          }
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

                  {/* 4) Rate button with Tooltip when in_catalog is false */}
                  <div
                    className="rate-button-container"
                    title={!movie.inCatalog ? "Ye movie abhi AI catalog mein nahi hai" : ""}
                  >
                    <button
                      type="button"
                      className="submit-rating"
                      onClick={handleRatingSubmit}
                      disabled={!movie.inCatalog || selectedRating === 0}
                    >
                      {movie.inCatalog ? "Rate Movie" : "Catalog Only"}
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