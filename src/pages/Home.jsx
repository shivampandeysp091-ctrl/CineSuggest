import "./Home.css";
import { Link, useNavigate } from "react-router-dom";
import { useState, useEffect } from "react";
import { getCurrentUser } from "../auth/auth";
import { api } from "../api/client";
import MovieCard from "../components/MovieCard";

function Home() {
  const navigate = useNavigate();

  // ================= USER INFORMATION =================
  const user = getCurrentUser();
  const userName =
    user?.name ||
    user?.username ||
    user?.fullName ||
    "User";

  const userInitial = userName
    .trim()
    .charAt(0)
    .toUpperCase();

  // ================= STATE =================
  const [searchQuery, setSearchQuery] = useState("");
  const [trendingMovies, setTrendingMovies] = useState([]);
  const [topRatedMovies, setTopRatedMovies] = useState([]);
  const [browseMovies, setBrowseMovies] = useState([]);
  const [isLoading, setIsLoading] = useState(true);

  // ================= FETCH MOVIES FROM BACKEND =================
  useEffect(() => {
    let isMounted = true;

    async function loadAllSections() {
      setIsLoading(true);
      try {
        // 1. Trending Movies (from TMDB /trending/movie/week)
        const trendingPromise = api.getTrending().catch((err) => {
          console.warn("Error fetching trending movies:", err);
          return [];
        });

        // 2. Top Rated Movies (from database tmdb_rating DESC)
        const topRatedPromise = api.getTopRated(10).catch((err) => {
          console.warn("Error fetching top rated movies:", err);
          return [];
        });

        // 3. Browse Catalog (from database /movies/)
        const browsePromise = api.getMovies().catch((err) => {
          console.warn("Error fetching browse movies:", err);
          return [];
        });

        const [trendingData, topRatedData, browseData] = await Promise.all([
          trendingPromise,
          topRatedPromise,
          browsePromise,
        ]);

        if (isMounted) {
          if (Array.isArray(trendingData)) setTrendingMovies(trendingData);
          if (Array.isArray(topRatedData)) setTopRatedMovies(topRatedData);
          if (Array.isArray(browseData)) setBrowseMovies(browseData);
        }
      } catch (err) {
        console.error("Home sections load error:", err);
      } finally {
        if (isMounted) setIsLoading(false);
      }
    }

    loadAllSections();
    return () => {
      isMounted = false;
    };
  }, []);

  const handleSearch = (e) => {
    e.preventDefault();
    const query = searchQuery.trim();
    if (!query) {
      navigate("/search");
      return;
    }
    navigate(`/search?query=${encodeURIComponent(query)}`);
  };

  return (
    <div className="home-page">
      {/* ================= NAVBAR ================= */}
      <nav className="navbar">
        <div className="logo">
          <span>🎬</span> CineSuggest
        </div>

        <div className="nav-links">
          <Link className="active" to="/home">
            Discover
          </Link>
          <Link to="/recommendations">My Recommendations</Link>
          <Link to="/my-list">My List</Link>
          <Link to="/history">History</Link>
        </div>

        <Link to="/profile" className="profile-circle" title={userName}>
          {userInitial}
        </Link>
      </nav>

      {/* ================= WELCOME / HERO SECTION ================= */}
      <section className="welcome-section">
        <div className="welcome-content">
          <p className="small-title">YOUR PERSONAL AI MOVIE GUIDE</p>
          <h1>
            Welcome to <span>CineSuggest</span>
          </h1>
          <p className="welcome-text">
            Discover movies you'll love, powered by collaborative AI and real TMDB insights.
          </p>

          {/* SEARCH BOX */}
          <form className="search-box" onSubmit={handleSearch}>
            <span>🔍</span>
            <input
              type="text"
              placeholder="Search movies by title, actors, genres..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              autoComplete="off"
            />
            <button type="submit">Search</button>
          </form>
        </div>
      </section>

      {/* ================= SECTION 1: TRENDING MOVIES (GET /movies/trending) ================= */}
      <section className="movie-section">
        <div className="section-heading">
          <div>
            <p className="section-label">HOT THIS WEEK</p>
            <h2>Trending Movies</h2>
          </div>
          <button className="view-all" onClick={() => navigate("/search")}>
            View All →
          </button>
        </div>

        <div className="movie-grid">
          {trendingMovies.length > 0 ? (
            trendingMovies.slice(0, 10).map((m) => {
              const targetId = m.in_catalog === false ? `tmdb-${m.tmdb_id}` : (m.movie_id || m.id);
              const year = m.release_date ? m.release_date.slice(0, 4) : m.release_year;
              return (
                <MovieCard
                  key={m.tmdb_id || m.movie_id}
                  id={targetId}
                  title={m.title}
                  posterUrl={m.poster_url}
                  releaseYear={year}
                  genres={m.genres}
                  tmdbRating={m.tmdb_rating}
                  inCatalog={m.in_catalog !== false}
                  showCatalogBadge={true}
                />
              );
            })
          ) : (
            isLoading && <p className="loading-text">Loading trending movies...</p>
          )}
        </div>
      </section>

      {/* ================= SECTION 2: TOP RATED (GET /movies/top-rated) ================= */}
      <section className="movie-section">
        <div className="section-heading">
          <div>
            <p className="section-label">CRITICALLY ACCLAIMED</p>
            <h2>Top Rated</h2>
          </div>
          <button className="view-all" onClick={() => navigate("/search")}>
            Explore All →
          </button>
        </div>

        <div className="movie-grid">
          {topRatedMovies.length > 0 ? (
            topRatedMovies.slice(0, 10).map((m) => (
              <MovieCard
                key={m.movie_id}
                id={m.movie_id}
                title={m.title}
                posterUrl={m.poster_url}
                releaseYear={m.release_year}
                genres={m.genres}
                tmdbRating={m.tmdb_rating}
                inCatalog={true}
              />
            ))
          ) : (
            isLoading && <p className="loading-text">Loading top rated movies...</p>
          )}
        </div>
      </section>

      {/* ================= SECTION 3: BROWSE CATALOG (GET /movies) ================= */}
      <section className="movie-section">
        <div className="section-heading">
          <div>
            <p className="section-label">CATALOG</p>
            <h2>Browse Movies</h2>
          </div>
          <button className="view-all" onClick={() => navigate("/search")}>
            Full Catalog →
          </button>
        </div>

        <div className="movie-grid">
          {browseMovies.length > 0 ? (
            browseMovies.slice(0, 10).map((m) => (
              <MovieCard
                key={m.movie_id}
                id={m.movie_id}
                title={m.title}
                posterUrl={m.poster_url}
                releaseYear={m.release_year}
                genres={m.genres}
                tmdbRating={m.tmdb_rating}
                inCatalog={true}
              />
            ))
          ) : (
            isLoading && <p className="loading-text">Loading catalog movies...</p>
          )}
        </div>
      </section>

      {/* ================= AI RECOMMENDATIONS CTA ================= */}
      <section className="movie-section">
        <div className="section-heading">
          <div>
            <p className="section-label">AI PICKS FOR YOU</p>
            <h2>Recommended For You</h2>
          </div>
        </div>

        <div className="recommendation-box">
          <div className="ai-icon">✦</div>
          <div>
            <h3>AI-Powered Recommendations</h3>
            <p>
              Our machine learning recommender learns your taste as you rate movies and suggests titles tailored to you.
            </p>
          </div>
          <Link to="/recommendations" className="recommendation-button">
            Explore Recommendations
          </Link>
        </div>
      </section>
    </div>
  );
}

export default Home;