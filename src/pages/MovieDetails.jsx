import "./MovieDetails.css";
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

function MovieDetails() {
  const { id } = useParams();

  const movies = {
    spiderman: {
      title: "Spider-Man: Brand New Day",
      image: "/images/spiderman-brand-new-day.jpg",
      rating: "8.0",
      year: "2026",
      genres: ["Action", "Sci-Fi"],
      description:
        "Peter Parker returns for a new adventure as Spider-Man faces a powerful new threat that challenges everything he knows.",
      cast: ["Tom Holland", "Zendaya", "Jacob Batalon"],
    },

    odyssey: {
      title: "The Odyssey",
      image: "/images/the-odyssey.jpg",
      rating: "8.4",
      year: "2026",
      genres: ["Adventure", "Drama"],
      description:
        "A legendary journey filled with danger, mystery and courage as a hero struggles to find his way home.",
      cast: ["Matt Damon", "Tom Holland", "Anne Hathaway"],
    },

    "demon-slayer": {
      title: "Demon Slayer",
      image: "/images/demon-slayer.jpg",
      rating: "8.6",
      year: "2026",
      genres: ["Anime", "Action"],
      description:
        "Tanjiro continues his journey as a Demon Slayer while facing powerful enemies and protecting the people he loves.",
      cast: ["Natsuki Hanae", "Akari Kito", "Hiro Shimono"],
    },

    "jujutsu-kaisen": {
      title: "Jujutsu Kaisen",
      image: "/images/jujutsu-kaisen.jpg",
      rating: "8.5",
      year: "2026",
      genres: ["Anime", "Action"],
      description:
        "Yuji Itadori and his allies battle dangerous cursed spirits while uncovering secrets about the world of Jujutsu.",
      cast: ["Junya Enoki", "Yuma Uchida", "Megumi Ogata"],
    },

    "inside-out-2": {
      title: "Inside Out 2",
      image: "/images/inside-out-2.jpg",
      rating: "8.1",
      year: "2024",
      genres: ["Animation", "Comedy"],
      description:
        "Riley enters a new stage of life as new emotions arrive and create unexpected changes inside her mind.",
      cast: ["Amy Poehler", "Maya Hawke", "Kensington Tallman"],
    },

    "knives-out": {
      title: "Knives Out",
      image: "/images/knives-out.jpg",
      rating: "8.0",
      year: "2019",
      genres: ["Mystery", "Crime"],
      description:
        "A detective investigates the mysterious death of a wealthy author while uncovering secrets within his unusual family.",
      cast: ["Daniel Craig", "Chris Evans", "Ana de Armas"],
    },

    "how-to-train-your-dragon": {
      title: "How to Train Your Dragon",
      image: "/images/how-to-train-your-dragon.jpg",
      rating: "8.1",
      year: "2025",
      genres: ["Fantasy", "Adventure"],
      description:
        "A young Viking forms an unexpected friendship with a dragon and changes the relationship between humans and dragons.",
      cast: ["Mason Thames", "Nico Parker", "Gerard Butler"],
    },

    "fantastic-four": {
      title: "The Fantastic Four: First Steps",
      image: "/images/fantastic-four-first-steps.jpg",
      rating: "7.8",
      year: "2025",
      genres: ["Superhero", "Sci-Fi"],
      description:
        "The Fantastic Four face their greatest challenge yet as they protect their world from a powerful cosmic threat.",
      cast: ["Pedro Pascal", "Vanessa Kirby", "Joseph Quinn"],
    },
  };

  const movie = movies[id];

  const [isSaved, setIsSaved] = useState(() => {
    const savedMovies =
      JSON.parse(localStorage.getItem("myList")) || [];

    return savedMovies.some(
      (savedMovie) => savedMovie.id === id
    );
  });

  // ================= WATCH HISTORY =================

  useEffect(() => {
    if (!movie) return;

    const history =
      JSON.parse(localStorage.getItem("watchHistory")) || [];

    const movieToSave = {
      id: id,
      title: movie.title,
      image: movie.image,
      rating: movie.rating,
      year: movie.year,
      genres: movie.genres,
      info: `${movie.year} • ${movie.genres.join(" / ")}`,
    };

    // Remove duplicate movie
    const filteredHistory = history.filter(
      (item) => item.id !== id
    );

    // Add latest movie at the beginning
    const updatedHistory = [
      movieToSave,
      ...filteredHistory,
    ];

    localStorage.setItem(
      "watchHistory",
      JSON.stringify(updatedHistory)
    );
  }, [id, movie]);

  // ================= MY LIST =================

  const handleMyList = () => {
    const savedMovies =
      JSON.parse(localStorage.getItem("myList")) || [];

    if (isSaved) {
      const updatedMovies = savedMovies.filter(
        (savedMovie) => savedMovie.id !== id
      );

      localStorage.setItem(
        "myList",
        JSON.stringify(updatedMovies)
      );

      setIsSaved(false);
    } else {
      const movieToSave = {
        id: id,
        title: movie.title,
        image: movie.image,
        rating: movie.rating,
        year: movie.year,
        genres: movie.genres,
        info: `${movie.year} • ${movie.genres.join(" / ")}`,
      };

      const updatedMovies = [
        ...savedMovies,
        movieToSave,
      ];

      localStorage.setItem(
        "myList",
        JSON.stringify(updatedMovies)
      );

      setIsSaved(true);
    }
  };

  // ================= MOVIE NOT FOUND =================

  if (!movie) {
    return (
      <div className="movie-details-page">
        <div className="movie-not-found">
          <h1>Movie Not Found</h1>
          <Link to="/home">← Back to Discover</Link>
        </div>
      </div>
    );
  }

  // ================= SIMILAR MOVIES =================

  const similarMovies = Object.entries(movies)
    .filter(([movieId]) => movieId !== id)
    .filter(([, similarMovie]) =>
      similarMovie.genres.some((genre) =>
        movie.genres.includes(genre)
      )
    )
    .slice(0, 4);

  return (
    <div className="movie-details-page">

      {/* ================= NAVBAR ================= */}

      <nav className="navbar">
        <div className="logo">
          <span>🎬</span> Cinematic AI
        </div>

        <div className="nav-links">
          <Link to="/home">Discover</Link>
          <Link to="/recommendations">
            My Recommendations
          </Link>
          <Link to="/my-list">My List</Link>
          <Link to="/history">History</Link>
        </div>

        <div className="profile-circle">A</div>
      </nav>

      {/* ================= MOVIE HERO ================= */}

      <section className="movie-hero">

        <div className="movie-backdrop">
          <img
            src={movie.image}
            alt={movie.title}
          />
        </div>

        <div className="movie-overlay"></div>

        <div className="movie-content">

          <div className="movie-poster-large">
            <img
              src={movie.image}
              alt={movie.title}
            />
          </div>

          <div className="movie-info">

            <p className="movie-label">
              MOVIE DETAILS
            </p>

            <h1>{movie.title}</h1>

            <div className="movie-meta">
              <span className="movie-rating">
                ★ {movie.rating}
              </span>

              <span>{movie.year}</span>

              {movie.genres.map((genre) => (
                <span key={genre}>
                  {genre}
                </span>
              ))}
            </div>

            <p className="movie-description">
              {movie.description}
            </p>

            {/* ================= ACTION BUTTON ================= */}

            <div className="movie-actions">

              <button
                className="list-button"
                onClick={handleMyList}
              >
                {isSaved
                  ? "♥ Remove from My List"
                  : "♡ Add to My List"}
              </button>

            </div>

            {/* ================= CAST ================= */}

            <div className="cast-section">

              <h3>Cast</h3>

              <div className="cast-list">
                {movie.cast.map((actor) => (
                  <span key={actor}>
                    {actor}
                  </span>
                ))}
              </div>

            </div>

          </div>

        </div>
      </section>

      {/* ================= SIMILAR MOVIES ================= */}

      {similarMovies.length > 0 && (
        <section className="similar-section">

          <div className="similar-heading">
            <div>
              <p>YOU MAY ALSO LIKE</p>
              <h2>Similar Movies</h2>
            </div>

            <Link to="/search">
              View All →
            </Link>
          </div>

          <div className="similar-grid">

            {similarMovies.map(
              ([movieId, similarMovie]) => (

                <Link
                  key={movieId}
                  to={`/movie-details/${movieId}`}
                  className="similar-card"
                >

                  <div className="similar-poster">

                    <img
                      src={similarMovie.image}
                      alt={similarMovie.title}
                    />

                    <span>
                      ★ {similarMovie.rating}
                    </span>

                  </div>

                  <h3>{similarMovie.title}</h3>

                  <p>
                    {similarMovie.year} •{" "}
                    {similarMovie.genres.join(" / ")}
                  </p>

                </Link>

              )
            )}

          </div>

        </section>
      )}

      {/* ================= BACK BUTTON ================= */}

      <div className="back-section">

        <Link to="/home">
          ← Back to Discover
        </Link>

      </div>

    </div>
  );
}

export default MovieDetails;