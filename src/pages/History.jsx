import "./History.css";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

function History() {
  const [movies, setMovies] = useState([]);

  // Load watch history
  useEffect(() => {
    const savedHistory =
      JSON.parse(localStorage.getItem("watchHistory")) || [];

    setMovies(savedHistory);
  }, []);

  // Remove one movie from history
  const removeMovie = (id) => {
    const updatedHistory = movies.filter(
      (movie) => movie.id !== id
    );

    localStorage.setItem(
      "watchHistory",
      JSON.stringify(updatedHistory)
    );

    setMovies(updatedHistory);
  };

  // Clear complete history
  const clearHistory = () => {
    localStorage.removeItem("watchHistory");
    setMovies([]);
  };

  return (
    <div className="history-page">

      {/* ================= NAVBAR ================= */}

      <nav className="navbar">

        <div className="logo">
          <span>🎬</span> Cinematic AI
        </div>

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

        <div className="profile-circle">
          A
        </div>

      </nav>


      {/* ================= HEADER ================= */}

      <div className="history-header">

        <div>
          <p>YOUR ACTIVITY</p>

          <h1>Watch History</h1>

          <span>
            Movies you've recently viewed.
          </span>
        </div>

        {movies.length > 0 && (
          <button
            className="clear-history-button"
            onClick={clearHistory}
          >
            Clear History
          </button>
        )}

      </div>


      {/* ================= MOVIES ================= */}

      {movies.length > 0 ? (

        <div className="history-grid">

          {movies.map((movie) => (

            <div
              className="history-card"
              key={movie.id}
            >

              <Link
                to={`/movie-details/${movie.id}`}
                className="history-movie-link"
              >

                <div className="history-poster">

                  <img
                    src={movie.image}
                    alt={movie.title}
                  />

                  <span className="history-rating">
                    ★ {movie.rating}
                  </span>

                </div>

                <h3>
                  {movie.title}
                </h3>

                <p>
                  {movie.info}
                </p>

              </Link>


              {/* Remove button */}

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

        /* ================= EMPTY STATE ================= */

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