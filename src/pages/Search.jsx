import "./Search.css";
import { useState } from "react";
import { Link } from "react-router-dom";

function Search() {
  const [query, setQuery] = useState("");

  const movies = [
    {
      id: "spiderman",
      title: "Spider-Man: Brand New Day",
      image: "/images/spiderman-brand-new-day.jpg",
      rating: "8.0",
      info: "2026 • Action / Sci-Fi",
    },
    {
      id: "odyssey",
      title: "The Odyssey",
      image: "/images/the-odyssey.jpg",
      rating: "8.4",
      info: "2026 • Adventure / Drama",
    },
    {
      id: "demon-slayer",
      title: "Demon Slayer",
      image: "/images/demon-slayer.jpg",
      rating: "8.6",
      info: "2026 • Anime / Action",
    },
    {
      id: "jujutsu-kaisen",
      title: "Jujutsu Kaisen",
      image: "/images/jujutsu-kaisen.jpg",
      rating: "8.5",
      info: "2026 • Anime / Action",
    },
    {
      id: "inside-out-2",
      title: "Inside Out 2",
      image: "/images/inside-out-2.jpg",
      rating: "8.1",
      info: "2024 • Animation / Comedy",
    },
    {
      id: "knives-out",
      title: "Knives Out",
      image: "/images/knives-out.jpg",
      rating: "8.0",
      info: "2019 • Mystery / Crime",
    },
    {
      id: "how-to-train-your-dragon",
      title: "How to Train Your Dragon",
      image: "/images/how-to-train-your-dragon.jpg",
      rating: "8.1",
      info: "2025 • Fantasy / Adventure",
    },
    {
      id: "fantastic-four",
      title: "The Fantastic Four: First Steps",
      image: "/images/fantastic-four-first-steps.jpg",
      rating: "7.8",
      info: "2025 • Superhero / Sci-Fi",
    },
  ];

  const searchText = query.trim().toLowerCase();

  const filteredMovies = movies.filter((movie) => {
    return movie.title.toLowerCase().includes(searchText);
  });

  return (
    <div className="search-page">

      {/* NAVBAR */}
      <nav className="navbar">

        <div className="logo">
          <span>🎬</span> Cinematic AI
        </div>

        <div className="nav-links">
          <Link to="/home">Discover</Link>

          <Link to="/recommendations">
            My Recommendations
          </Link>

          <Link to="/my-list">
            My List
          </Link>

          <Link to="/history">
            History
          </Link>
        </div>

        <div className="profile-circle">
          A
        </div>

      </nav>


      {/* SEARCH HEADER */}
      <section className="search-header">

        <p>SEARCH MOVIES</p>

        <h1>Find Your Next Movie</h1>

        <span>
          Search for movies by title, genre or your
          favorite characters.
        </span>

        <div className="search-large">

          <span>🔍</span>

          <input
            type="text"
            placeholder="Search for movies..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />

        </div>

      </section>


      {/* SEARCH RESULTS */}
      <section className="search-results">

        <div className="results-heading">

          <h2>
            {searchText === ""
              ? "All Movies"
              : `Search Results for "${query}"`}
          </h2>

          <span>
            {filteredMovies.length}{" "}
            {filteredMovies.length === 1
              ? "movie"
              : "movies"}{" "}
            found
          </span>

        </div>


        {/* MOVIES */}
        {filteredMovies.length > 0 ? (

          <div className="search-grid">

            {filteredMovies.map((movie) => (

              <Link
                key={movie.id}
                to={`/movie-details/${movie.id}`}
                className="search-card"
              >

                <div className="search-poster">

                  <img
                    src={movie.image}
                    alt={movie.title}
                  />

                  <span className="search-rating">
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

            ))}

          </div>

        ) : (

          /* NO RESULTS */
          <div className="no-results">

            <div>🔍</div>

            <h2>
              No Movies Found
            </h2>

            <p>
              Try searching with another movie title.
            </p>

          </div>

        )}

      </section>

    </div>
  );
}

export default Search;