import "./MyList.css";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

function MyList() {
  const [movies, setMovies] = useState([]);

  // Load saved movies when the page opens
  useEffect(() => {
    const savedMovies =
      JSON.parse(localStorage.getItem("myList")) || [];

    setMovies(savedMovies);
  }, []);

  // Remove movie from My List
  const removeMovie = (id) => {
    const updatedMovies = movies.filter(
      (movie) => movie.id !== id
    );

    localStorage.setItem(
      "myList",
      JSON.stringify(updatedMovies)
    );

    setMovies(updatedMovies);
  };

  return (
    <div className="my-list-page">

      {/* ================= HEADER ================= */}

      <div className="my-list-header">

        <p>
          YOUR COLLECTION
        </p>

        <h1>
          My List
        </h1>

        <span>
          Movies you've saved to watch later.
        </span>

      </div>


      {/* ================= SAVED MOVIES ================= */}

      {movies.length > 0 ? (

        <div className="my-list-grid">

          {movies.map((movie) => (

            <div
              className="my-list-card"
              key={movie.id}
            >

              <Link
                to={`/movie-details/${movie.id}`}
                className="my-list-movie-link"
              >

                <div className="my-list-poster">

                  <img
                    src={movie.image}
                    alt={movie.title}
                  />

                  <span className="my-list-rating">
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


              {/* REMOVE BUTTON */}

              <button
                className="remove-button"
                onClick={() => removeMovie(movie.id)}
                title="Remove from My List"
              >
                ♥
              </button>

            </div>

          ))}

        </div>

      ) : (

        /* ================= EMPTY LIST ================= */

        <div className="empty-list">

          <div className="empty-icon">
            ♡
          </div>

          <h2>
            Your List is Empty
          </h2>

          <p>
            Save movies you want to watch later.
          </p>

          <Link
            to="/home"
            className="browse-button"
          >
            Discover Movies
          </Link>

        </div>

      )}

    </div>
  );
}

export default MyList;