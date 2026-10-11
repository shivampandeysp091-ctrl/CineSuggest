import "./Search.css";
import { useState, useEffect } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { getCurrentUser } from "../auth/auth";
import { api } from "../api/client";
import MovieCard from "../components/MovieCard";

function Search() {
  const [searchParams, setSearchParams] = useSearchParams();
  const initialQuery = searchParams.get("query") || "";
  const [query, setQuery] = useState(initialQuery);
  const [searchResults, setSearchResults] = useState([]);
  const [isSearching, setIsSearching] = useState(false);
  const [catalogPopular, setCatalogPopular] = useState([]);

  // ================= USER =================
  const user = getCurrentUser();
  const userName =
    user?.name ||
    user?.username ||
    user?.fullName ||
    "User";

  const userInitial =
    userName.trim().charAt(0).toUpperCase();

  // Load initial popular movies from catalog if no query
  useEffect(() => {
    let isMounted = true;
    api.getTopRated(12)
      .then((data) => {
        if (isMounted && Array.isArray(data)) {
          setCatalogPopular(data);
        }
      })
      .catch(() => {});
    return () => { isMounted = false; };
  }, []);

  // ================= SEARCH EFFECT =================
  useEffect(() => {
    const urlQuery = (searchParams.get("query") || "").trim();
    setQuery(urlQuery);

    if (!urlQuery) {
      setSearchResults([]);
      setIsSearching(false);
      return;
    }

    let isMounted = true;
    setIsSearching(true);

    api.searchMovies(urlQuery)
      .then((data) => {
        if (!isMounted) return;
        const list = Array.isArray(data) ? data : (data?.results || []);
        setSearchResults(list);
      })
      .catch((err) => {
        console.warn("Search API failed:", err);
        if (isMounted) setSearchResults([]);
      })
      .finally(() => {
        if (isMounted) setIsSearching(false);
      });

    return () => { isMounted = false; };
  }, [searchParams]);

  const handleSearch = (e) => {
    e.preventDefault();
    const trimmed = query.trim();
    if (!trimmed) {
      setSearchParams({});
      return;
    }
    setSearchParams({ query: trimmed });
  };

  const isQueryActive = Boolean(searchParams.get("query")?.trim());
  const displayList = isQueryActive ? searchResults : catalogPopular;

  return (
    <div className="search-page">
      {/* ================= NAVBAR ================= */}
      <nav className="navbar">
        <div className="logo">
          <span>🎬</span> CineSuggest
        </div>

        <div className="nav-links">
          <Link to="/home">Discover</Link>
          <Link to="/recommendations">My Recommendations</Link>
          <Link to="/my-list">My List</Link>
          <Link to="/history">History</Link>
        </div>

        <Link to="/profile" className="profile-circle" title={userName}>
          {userInitial}
        </Link>
      </nav>

      {/* ================= HEADER ================= */}
      <section className="search-header">
        <p>SEARCH MOVIES</p>
        <h1>Find Your Next Movie</h1>
        <span>
          Search our AI catalog and live TMDB database for movies, actors, and genres.
        </span>

        {/* SEARCH BOX */}
        <form className="search-large" onSubmit={handleSearch}>
          <span>🔍</span>
          <input
            type="text"
            placeholder="Search for movies, e.g. Inception, Avatar, Dark Knight..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            autoComplete="off"
          />
          <button type="submit" className="search-submit-button">
            Search
          </button>
        </form>
      </section>

      {/* ================= SEARCH RESULTS ================= */}
      <section className="search-results">
        <div className="results-heading">
          <h2>
            {isQueryActive
              ? `Results for "${searchParams.get("query")}"`
              : "Popular in Catalog"}
          </h2>
          <span>
            {isSearching
              ? "Searching..."
              : `${displayList.length} ${displayList.length === 1 ? "movie" : "movies"} found`}
          </span>
        </div>

        {displayList.length > 0 ? (
          <div className="search-grid">
            {displayList.map((m) => {
              const inCatalog = m.in_catalog !== false;
              const targetId = inCatalog ? (m.movie_id || m.id) : `tmdb-${m.tmdb_id}`;
              const year = m.release_year || (m.release_date ? m.release_date.slice(0, 4) : "");

              return (
                <MovieCard
                  key={m.movie_id || m.tmdb_id || m.id}
                  id={targetId}
                  title={m.title}
                  posterUrl={m.poster_url}
                  releaseYear={year}
                  genres={m.genres}
                  tmdbRating={m.tmdb_rating}
                  inCatalog={inCatalog}
                  showCatalogBadge={true}
                />
              );
            })}
          </div>
        ) : isSearching ? (
          <p className="loading-text">Searching database and TMDB...</p>
        ) : (
          <div className="no-results">
            <div>🔍</div>
            <h2>No Movies Found</h2>
            <p>
              We couldn't find any catalog or TMDB matches for "{searchParams.get("query")}".
              Try a different keyword or movie title.
            </p>
          </div>
        )}
      </section>
    </div>
  );
}

export default Search;