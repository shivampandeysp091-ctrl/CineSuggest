import "./Recommendations.css";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

function Recommendations() {
  const [recommendations, setRecommendations] = useState([]);
  const [topGenres, setTopGenres] = useState([]);
  const [historyCount, setHistoryCount] = useState(0);

  const movies = [
    {
      id: "spiderman",
      title: "Spider-Man: Brand New Day",
      image: "/images/spiderman-brand-new-day.jpg",
      rating: "8.0",
      year: "2026",
      genres: ["Action", "Sci-Fi"],
    },
    {
      id: "odyssey",
      title: "The Odyssey",
      image: "/images/the-odyssey.jpg",
      rating: "8.4",
      year: "2026",
      genres: ["Adventure", "Drama"],
    },
    {
      id: "demon-slayer",
      title: "Demon Slayer",
      image: "/images/demon-slayer.jpg",
      rating: "8.6",
      year: "2026",
      genres: ["Anime", "Action"],
    },
    {
      id: "jujutsu-kaisen",
      title: "Jujutsu Kaisen",
      image: "/images/jujutsu-kaisen.jpg",
      rating: "8.5",
      year: "2026",
      genres: ["Anime", "Action"],
    },
    {
      id: "inside-out-2",
      title: "Inside Out 2",
      image: "/images/inside-out-2.jpg",
      rating: "8.1",
      year: "2024",
      genres: ["Animation", "Comedy"],
    },
    {
      id: "knives-out",
      title: "Knives Out",
      image: "/images/knives-out.jpg",
      rating: "8.0",
      year: "2019",
      genres: ["Mystery", "Crime"],
    },
    {
      id: "how-to-train-your-dragon",
      title: "How to Train Your Dragon",
      image: "/images/how-to-train-your-dragon.jpg",
      rating: "8.1",
      year: "2025",
      genres: ["Fantasy", "Adventure"],
    },
    {
      id: "fantastic-four",
      title: "The Fantastic Four: First Steps",
      image: "/images/fantastic-four-first-steps.jpg",
      rating: "7.8",
      year: "2025",
      genres: ["Superhero", "Sci-Fi"],
    },
  ];

  useEffect(() => {
    const history =
      JSON.parse(localStorage.getItem("watchHistory")) || [];

    setHistoryCount(history.length);

    if (history.length === 0) {
      setRecommendations([]);
      setTopGenres([]);
      return;
    }

    // =========================
    // ANALYZE USER GENRES
    // =========================

    const genreCount = {};

    history.forEach((movie) => {
      movie.genres.forEach((genre) => {
        genreCount[genre] =
          (genreCount[genre] || 0) + 1;
      });
    });

    // Sort genres according to how frequently
    // the user has watched them
    const sortedGenres = Object.entries(genreCount)
      .sort((a, b) => b[1] - a[1])
      .map(([genre]) => genre);

    // Keep top 3 preferred genres
    setTopGenres(sortedGenres.slice(0, 3));

    // =========================
    // GENERATE RECOMMENDATIONS
    // =========================

    const watchedIds = history.map(
      (movie) => movie.id
    );

    const recommendedMovies = movies
      // Don't recommend movies the user already watched
      .filter(
        (movie) => !watchedIds.includes(movie.id)
      )
      // Calculate how many preferred genres match
      .map((movie) => {
        const matchingGenres =
          movie.genres.filter((genre) =>
            sortedGenres.includes(genre)
          );

        return {
          ...movie,
          score: matchingGenres.length,
          matchingGenres: matchingGenres,
        };
      })
      // Only keep movies with at least one matching genre
      .filter((movie) => movie.score > 0)
      // Sort by genre match first, then rating
      .sort((a, b) => {
        if (b.score !== a.score) {
          return b.score - a.score;
        }

        return (
          parseFloat(b.rating) -
          parseFloat(a.rating)
        );
      })
      // Show maximum 4 recommendations
      .slice(0, 4);

    setRecommendations(recommendedMovies);
  }, []);

  return (
    <div className="recommendations-page">

      {/* =========================
          NAVBAR
      ========================= */}

      <nav className="navbar">

        <div className="logo">
          <span>🎬</span> Cinematic AI
        </div>

        <div className="nav-links">

          <Link to="/home">
            Discover
          </Link>

          <Link
            to="/recommendations"
            className="active"
          >
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


      {/* =========================
          HEADER
      ========================= */}

      <div className="recommendations-header">

        <p>AI POWERED</p>

        <h1>
          My Recommendations
        </h1>

        <span>
          Movies selected by AI based on your
          watch history and preferences.
        </span>

      </div>


      {/* =========================
          AI MESSAGE
      ========================= */}

      <div className="ai-message">

        <div className="ai-icon">
          ✦
        </div>

        <div>

          <h3>
            Your AI Movie Guide
          </h3>

          {historyCount > 0 ? (
            <p>
              We've analyzed {historyCount} movie
              {historyCount > 1 ? "s" : ""} from your
              watch history and found your favorite
              genres.
            </p>
          ) : (
            <p>
              Start watching movies to help our AI
              understand your taste.
            </p>
          )}

        </div>

      </div>


      {/* =========================
          TOP GENRES
      ========================= */}

      {historyCount > 0 && (
        <div className="preference-box">

          <div>

            <p className="preference-label">
              YOUR TOP GENRES
            </p>

            <div className="genre-tags">

              {topGenres.map((genre) => (
                <span key={genre}>
                  {genre}
                </span>
              ))}

            </div>

          </div>

        </div>
      )}


      {/* =========================
          RECOMMENDED MOVIES
      ========================= */}

      {recommendations.length > 0 ? (

        <section className="recommendation-section">

          <div className="section-heading">

            <div>

              <p>
                PERSONALIZED FOR YOU
              </p>

              <h2>
                Recommended Movies
              </h2>

            </div>

          </div>


          <div className="recommendation-grid">

            {recommendations.map((movie) => (

              <Link
                key={movie.id}
                to={`/movie-details/${movie.id}`}
                className="recommendation-card"
              >

                {/* Movie Poster */}

                <div className="recommendation-poster">

                  <img
                    src={movie.image}
                    alt={movie.title}
                  />

                  <span>
                    ★ {movie.rating}
                  </span>

                </div>


                {/* Movie Information */}

                <h3>
                  {movie.title}
                </h3>

                <p>
                  {movie.year} •{" "}
                  {movie.genres.join(" / ")}
                </p>


                {/* Why Recommended */}

                <div className="why-recommended">

                  ✦ Recommended because you like{" "}

                  <strong>
                    {movie.matchingGenres.join(" + ")}
                  </strong>

                </div>

              </Link>

            ))}

          </div>

        </section>

      ) : (

        /* =========================
           EMPTY STATE
        ========================= */

        <div className="no-recommendations">

          <div className="empty-ai-icon">
            ✦
          </div>

          <h2>
            We Need More Data
          </h2>

          <p>
            Watch a few movies and our AI will
            start creating personalized
            recommendations for you.
          </p>

          <Link
            to="/home"
            className="discover-button"
          >
            Discover Movies
          </Link>

        </div>

      )}

    </div>
  );
}

export default Recommendations;