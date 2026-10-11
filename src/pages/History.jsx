import "./History.css";
import "../components/MovieCard.css";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getCurrentUser } from "../auth/auth";
import { api } from "../api/client";

function History() {
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

  const userInitial =
    userName.trim().charAt(0).toUpperCase();

  // =========================
  // LOAD WATCH HISTORY
  // =========================

  useEffect(() => {
    let isMounted = true;
    async function loadHistory() {
      try {
        const data = await api.getWatchHistory();
        const formatted = data.watch_history.map((h) => {
          const genresArr = (h.genres || "").split("|").filter(Boolean);
          const genresStr = genresArr.slice(0, 2).join(" • ");
          return {
            id: h.movie_id,
            numericId: h.movie_id,
            title: h.title,
            image: h.poster_url || null,
            poster: h.poster_url || null,
            genres: genresArr,
            info: h.release_year ? `${h.release_year}${genresStr ? ` • ${genresStr}` : ""}` : genresStr,
            rating: "Watched",
            watchedAt: h.watched_at ? new Date(h.watched_at).toLocaleDateString() : "",
          };
        });
        if (isMounted) setMovies(formatted);
        return;
      } catch (e) {
        console.warn("Unable to load watch history from API, using local storage:", e);
      }
      const savedHistory = JSON.parse(localStorage.getItem("watchHistory") || "[]");
      if (isMounted) setMovies(savedHistory);
    }
    loadHistory();
    return () => { isMounted = false; };
  }, []);

  // =========================
  // REMOVE ONE MOVIE
  // =========================

  const removeMovie = (id) => {
    const numId = parseInt(id, 10);
    if (!isNaN(numId)) {
      api.removeWatchHistory(numId).catch(() => {});
    }

    const updatedHistory = movies.filter(
      (movie) => movie.id !== id
    );

    localStorage.setItem(
      "watchHistory",
      JSON.stringify(updatedHistory)
    );

    setMovies(updatedHistory);
  };

  // =========================
  // CLEAR COMPLETE HISTORY
  // =========================

  const clearHistory = () => {
    movies.forEach((m) => {
      const numId = parseInt(m.numericId || m.id, 10);
      if (!isNaN(numId)) {
        api.removeWatchHistory(numId).catch(() => {});
      }
    });
    localStorage.removeItem("watchHistory");
    setMovies([]);
  };

  return (
    <div className="history-page">

      {/* =====================================================
          NAVBAR
      ===================================================== */}

      <nav className="navbar">

        {/* LOGO */}

        <div className="logo">
          <span>🎬</span> CineSuggest
        </div>


        {/* NAVIGATION */}

        <div className="nav-links">

          <Link to="/home">
            Discover
          </Link>

          <Link to="/recommendations">
            My Recommendations
          </Link>

          <Link to="/my-list">
            My List
          </Link>

          <Link
            to="/history"
            className="active"
          >
            History
          </Link>

        </div>


        {/* USER PROFILE */}

        <Link
          to="/profile"
          className="profile-circle"
          title={userName}
        >
          {userInitial}
        </Link>

      </nav>


      {/* =====================================================
          HEADER
      ===================================================== */}

      <div className="history-header">

        <div>

          <p>
            YOUR ACTIVITY
          </p>

          <h1>
            Watch History
          </h1>

          <span>
            Movies you've recently viewed.
          </span>

        </div>


        {/* CLEAR HISTORY */}

        {movies.length > 0 && (

          <button
            className="clear-history-button"
            onClick={clearHistory}
          >
            Clear History
          </button>

        )}

      </div>


      {/* =====================================================
          MOVIES
      ===================================================== */}

      {movies.length > 0 ? (

        <div className="history-grid">

          {movies.map((movie) => (

            <div
              className="history-card"
              key={movie.id}
            >

              {/* MOVIE LINK */}

              <Link
                to={`/movie-details/${movie.id}`}
                className="history-movie-link"
              >

                {/* POSTER */}

                <div className="history-poster">
                  {movie.image ? (
                    <img
                      src={movie.image}
                      alt={movie.title}
                      onError={(e) => { e.currentTarget.style.display = "none"; }}
                    />
                  ) : (
                    <div className="movie-card-placeholder" style={{ width: "100%", height: "100%" }}>
                      <span className="placeholder-clapper">🎬</span>
                      <span className="placeholder-text">{movie.title}</span>
                    </div>
                  )}

                  <span className="history-rating">
                    ★ {movie.rating}
                  </span>
                </div>


                {/* TITLE */}

                <h3>
                  {movie.title}
                </h3>


                {/* MOVIE INFO */}

                <p>
                  {movie.info}
                </p>

              </Link>


              {/* REMOVE BUTTON */}

              <button
                className="remove-history-button"
                onClick={() => removeMovie(movie.id)}
                title="Remove from History"
              >
                ×
              </button>

            </div>

          ))}

        </div>

      ) : (

        /* ===================================================
           EMPTY STATE
        =================================================== */

        <div className="empty-history">

          <div className="empty-history-icon">
            ◷
          </div>

          <h2>
            No Watch History
          </h2>

          <p>
            Movies you view will appear here.
          </p>

          <Link
            to="/home"
            className="browse-history-button"
          >
            Discover Movies
          </Link>

        </div>

      )}

    </div>
  );
}

export default History;