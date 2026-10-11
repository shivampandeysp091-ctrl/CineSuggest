import "./Recommendations.css";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getCurrentUser } from "../auth/auth";
import { api } from "../api/client";
import MovieCard from "../components/MovieCard";

function Recommendations() {
  const [recommendations, setRecommendations] = useState([]);
  const [topGenres, setTopGenres] = useState([]);
  const [ratingsCount, setRatingsCount] = useState(0);
  const [isPersonalized, setIsPersonalized] = useState(true);
  const [loading, setLoading] = useState(true);

  // ================= CURRENT USER =================
  const user = getCurrentUser();
  const userName =
    user?.name ||
    user?.username ||
    user?.fullName ||
    "User";

  const userInitial =
    userName.trim().charAt(0).toUpperCase();

  // ================= FETCH RECOMMENDATIONS & USER RATINGS =================
  useEffect(() => {
    let isMounted = true;

    async function loadData() {
      setLoading(true);
      try {
        // 1. Calculate how many ratings the user has
        let totalRatings = 0;
        try {
          const localRatings = JSON.parse(localStorage.getItem("movieRatings") || "{}");
          totalRatings = Object.keys(localRatings).length;
        } catch (e) {}

        if (isMounted) setRatingsCount(totalRatings);

        // 2. Fetch backend recommendations
        const recRes = await api.getRecommendations(12);

        if (isMounted && recRes?.recommendations && recRes.recommendations.length > 0) {
          const personalizedFlag = recRes.personalized === true;
          setIsPersonalized(personalizedFlag);

          const formatted = recRes.recommendations.map((r) => {
            const genreList = typeof r.genres === "string"
              ? r.genres.split("|").map((g) => g.trim()).filter(Boolean)
              : (Array.isArray(r.genres) ? r.genres : []);

            return {
              id: r.movie_id,
              numericId: r.movie_id,
              title: r.title,
              posterUrl: r.poster_url,
              releaseYear: r.release_year,
              genres: genreList,
              tmdbRating: r.tmdb_rating,
              matchPercentage: r.match_percentage ? Math.round(r.match_percentage) : (personalizedFlag ? 88 : null),
              matchingGenres: genreList.slice(0, 2),
            };
          });

          // Extract top genres from recommendations
          const genresFrequency = {};
          formatted.forEach((m) => {
            m.genres.forEach((g) => {
              genresFrequency[g] = (genresFrequency[g] || 0) + 1;
            });
          });
          const sorted = Object.entries(genresFrequency)
            .sort((a, b) => b[1] - a[1])
            .map(([g]) => g);

          setTopGenres(sorted.slice(0, 3));
          setRecommendations(formatted);
          setLoading(false);
          return;
        }
      } catch (err) {
        console.warn("Backend recommendations fetch failed, trying top rated fallback:", err);
        if (isMounted) {
          setIsPersonalized(false);
          try {
            const fallback = await api.getTopRated(8);
            if (isMounted && Array.isArray(fallback)) {
              setRecommendations(fallback.map((f) => ({
                id: f.movie_id,
                title: f.title,
                posterUrl: f.poster_url,
                releaseYear: f.release_year,
                genres: f.genres,
                tmdbRating: f.tmdb_rating,
                matchPercentage: null,
              })));
            }
          } catch (e2) {}
        }
      } finally {
        if (isMounted) setLoading(false);
      }
    }

    loadData();
    return () => {
      isMounted = false;
    };
  }, []);

  return (
    <div className="recommendations-page">
      {/* ================= NAVBAR ================= */}
      <nav className="navbar">
        <div className="logo">
          <span>🎬</span> CineSuggest
        </div>

        <div className="nav-links">
          <Link to="/home">Discover</Link>
          <Link to="/recommendations" className="active">
            My Recommendations
          </Link>
          <Link to="/my-list">My List</Link>
          <Link to="/history">History</Link>
        </div>

        <Link to="/profile" className="profile-circle" title={userName}>
          {userInitial}
        </Link>
      </nav>

      {/* ================= HEADER ================= */}
      <div className="recommendations-header">
        <p>AI POWERED</p>
        <h1>My Recommendations</h1>
        <span>
          Movies selected by AI based on your ratings and preferences.
        </span>
      </div>

      {/* ================= 6) UNPERSONALIZED BANNER ================= */}
      {!isPersonalized && (
        <div className="onboarding-unpersonalized-banner">
          <div className="banner-icon">🎯</div>
          <div className="banner-content">
            <h4>Pehle kuch movies rate karo, tab AI personalize karega</h4>
            <p>
              Abhi aapko popular movies dikhai ja rahi hain. Hamara collaborative AI model tab activate hota hai jab aap movies ko star rating dete hain.
            </p>
          </div>
          <Link to="/onboarding" className="banner-onboarding-link">
            Rate Movies Now →
          </Link>
        </div>
      )}

      {/* ================= AI MESSAGE ================= */}
      <div className="ai-message">
        <div className="ai-icon">✦</div>
        <div>
          <h3>Your AI Movie Guide</h3>
          {ratingsCount > 0 ? (
            <p>
              We've analyzed your ratings and calculated tailored suggestions based on your personal taste profile.
            </p>
          ) : (
            <p>
              Rate movies to help our collaborative AI model learn your unique taste.
            </p>
          )}
        </div>
      </div>

      {/* ================= TOP GENRES ================= */}
      {topGenres.length > 0 && (
        <div className="preference-box">
          <div>
            <p className="preference-label">TOP GENRES IN RECOMMENDATIONS</p>
            <div className="genre-tags">
              {topGenres.map((genre) => (
                <span key={genre}>{genre}</span>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* ================= RECOMMENDED MOVIES ================= */}
      {recommendations.length > 0 ? (
        <section className="recommendation-section">
          <div className="section-heading">
            <div>
              <p>{isPersonalized ? "PERSONALIZED FOR YOU" : "CURATED CATALOG PICKS"}</p>
              <h2>{isPersonalized ? "Recommended Movies" : "Popular Suggestions"}</h2>
            </div>
          </div>

          <div className="recommendation-grid">
            {recommendations.map((movie) => (
              <MovieCard
                key={movie.id}
                id={movie.id}
                title={movie.title}
                posterUrl={movie.posterUrl}
                releaseYear={movie.releaseYear}
                genres={movie.genres}
                tmdbRating={movie.tmdbRating}
                matchPercentage={movie.matchPercentage}
                inCatalog={true}
              />
            ))}
          </div>
        </section>
      ) : loading ? (
        <p className="loading-text" style={{ padding: "30px 50px" }}>
          Generating recommendations for you...
        </p>
      ) : (
        /* ================= EMPTY STATE ================= */
        <div className="no-recommendations">
          <div className="empty-ai-icon">✦</div>
          <h2>We Need More Data</h2>
          <p>
            Rate a few movies and our AI will start creating personalized recommendations for you.
          </p>
          <Link to="/onboarding" className="discover-button">
            Rate Movies for AI Profile
          </Link>
        </div>
      )}
    </div>
  );
}

export default Recommendations;