
import "./MyList.css";
import "../components/MovieCard.css";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getCurrentUser } from "../auth/auth";

import { api } from "../api/client";

function MyList() {
  const [movies, setMovies] = useState([]);

  // =========================
  // GET CURRENT USER
  // =========================

  const user = getCurrentUser();

  const userName =
    user?.name ||
    user?.username ||
    user?.fullName ||
    "User";

  const userInitial = userName.trim().charAt(0).toUpperCase();

  // =========================
  // LOAD SAVED MOVIES
  // =========================

  useEffect(() => {
    let isMounted = true;
    async function loadFavorites() {
      try {
        const data = await api.getFavorites();
        if (isMounted && data?.favorites && data.favorites.length > 0) {
          const formatted = data.favorites.map((f) => ({
            id: f.movie_id,
            numericId: f.movie_id,
            title: f.title,
            image: f.poster_url || null,
            poster: f.poster_url || null,
            tmdbRating: f.tmdb_rating ? Number(f.tmdb_rating).toFixed(1) : null,
            rating: f.tmdb_rating ? `TMDB ${Number(f.tmdb_rating).toFixed(1)}` : "Saved",
            info: (f.genres || "").split("|").filter(Boolean).slice(0, 2).join(" • "),
          }));
          setMovies(formatted);
          return;
        }
      } catch (error) {
        console.warn("Unable to load favorites from API, using local storage:", error);
      }

      try {
        const savedMovies = JSON.parse(
          localStorage.getItem("myList") || "[]"
        );
        if (isMounted) setMovies(Array.isArray(savedMovies) ? savedMovies : []);
      } catch (error) {
        if (isMounted) setMovies([]);
      }
    }

    loadFavorites();
    return () => { isMounted = false; };
  }, []);

  // =========================
  // REMOVE MOVIE FROM MY LIST
  // =========================

  const removeMovie = (id) => {
    const numId = parseInt(id, 10);
    if (!isNaN(numId)) {
      api.removeFavorite(numId).catch(() => {});
    }

    const updatedMovies = movies.filter(
      (movie) => movie.id !== id
    );

    try {
      localStorage.setItem("myList", JSON.stringify(updatedMovies));
      setMovies(updatedMovies);
    } catch (error) {
      console.error("Unable to update My List:", error);
    }
  };

  return (
    <div className="my-list-page">

      {/* =========================
          NAVBAR
      ========================= */}

      <nav className="navbar">
        <Link to="/home" className="logo">
          <span>🎬</span> CineSuggest
        </Link>

        <div className="nav-links">
          <Link to="/home">
            Discover
          </Link>

          <Link to="/recommendations">
            My Recommendations
          </Link>

          <Link to="/my-list" className="active">
            My List
          </Link>

          <Link to="/history">
            History
          </Link>
        </div>

        <Link
          to="/profile"
          className="profile-circle"
          title={userName}
        >
          {userInitial}
        </Link>
      </nav>

      {/* =========================
          HEADER
      ========================= */}

      <div className="my-list-header">
        <p>YOUR COLLECTION</p>

        <h1>My List</h1>

        <span>
          Movies you've saved to watch later.
        </span>
      </div>

      {/* =========================
          SAVED MOVIES
      ========================= */}

      {movies.length > 0 ? (
        <div className="my-list-grid">
          {movies.map((movie) => (
            <div className="my-list-card" key={movie.id}>

              <Link
                to={`/movie-details/${movie.id}`}
                className="my-list-movie-link"
              >
                <div className="my-list-poster">
                  {movie.image ? (
                    <img
                      src={movie.image}
                      alt={movie.title || "Movie poster"}
                      onError={(e) => { e.currentTarget.style.display = "none"; }}
                    />
                  ) : (
                    <div className="movie-card-placeholder" style={{ width: "100%", height: "100%" }}>
                      <span className="placeholder-clapper">🎬</span>
                      <span className="placeholder-text">{movie.title}</span>
                    </div>
                  )}

                  {movie.rating && (
                    <span className="my-list-rating">
                      ★ {movie.rating}
                    </span>
                  )}
                </div>

                <h3>{movie.title}</h3>

                <p>{movie.info}</p>
              </Link>

              <button
                type="button"
                className="remove-button"
                onClick={() => removeMovie(movie.id)}
                title="Remove from My List"
                aria-label={`Remove ${movie.title || "movie"} from My List`}
              >
                ♥
              </button>
            </div>
          ))}
        </div>
      ) : (
        /* =========================
            EMPTY LIST
        ========================= */

        <div className="empty-list">
          <div className="empty-icon">♡</div>

          <h2>Your List is Empty</h2>

          <p>
            Save movies you want to watch later.
          </p>

          <Link to="/home" className="browse-button">
            Discover Movies
          </Link>
        </div>
      )}

    </div>
  );
}

export default MyList;