import "./Home.css";
import { Link, useNavigate } from "react-router-dom";

function Home() {
  const navigate = useNavigate();

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

  return (
    <div className="home-page">

      {/* ================= NAVBAR ================= */}

      <nav className="navbar">

        <div className="logo">
          <span>🎬</span> Cinematic AI
        </div>

        <div className="nav-links">
          <Link className="active" to="/home">
            Discover
          </Link>

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

        <div className="profile">
          <div className="profile-circle">
            A
          </div>
        </div>

      </nav>


      {/* ================= WELCOME SECTION ================= */}

      <section className="welcome-section">

        <div className="welcome-content">

          <p className="small-title">
            YOUR PERSONAL AI MOVIE GUIDE
          </p>

          <h1>
            Welcome to <span>Cinematic AI</span>
          </h1>

          <p className="welcome-text">
            Discover movies you'll love, personalized just for you.
          </p>


          {/* SEARCH */}

          <div className="search-box">

            <span>🔍</span>

            <input
              type="text"
              placeholder="Search for movies, actors, genres..."
            />

            <button
              onClick={() => navigate("/search")}
            >
              Search
            </button>

          </div>

        </div>

      </section>


      {/* ================= TRENDING MOVIES ================= */}

      <section className="movie-section">

        <div className="section-heading">

          <div>

            <p className="section-label">
              TRENDING NOW
            </p>

            <h2>
              Trending Movies
            </h2>

          </div>

          <button
            className="view-all"
            onClick={() => navigate("/search")}
          >
            View All →
          </button>

        </div>


        <div className="movie-grid">

          {movies.map((movie) => (

            <Link
              key={movie.id}
              to={`/movie-details/${movie.id}`}
              className="movie-card"
            >

              <div className="movie-poster">

                <img
                  src={movie.image}
                  alt={movie.title}
                />

                <span className="rating">
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

      </section>


      {/* ================= AI RECOMMENDATIONS ================= */}

      <section className="movie-section">

        <div className="section-heading">

          <div>

            <p className="section-label">
              AI PICKS FOR YOU
            </p>

            <h2>
              Recommended For You
            </h2>

          </div>

        </div>


        <div className="recommendation-box">

          <div className="ai-icon">
            ✦
          </div>

          <div>

            <h3>
              AI-Powered Recommendations
            </h3>

            <p>
              Our AI learns your taste and finds movies
              that match your interests.
            </p>

          </div>


          <Link
            to="/recommendations"
            className="recommendation-button"
          >
            Explore Recommendations
          </Link>

        </div>

      </section>

    </div>
  );
}

export default Home;