import React from "react";
import { Link } from "react-router-dom";
import "./MovieCard.css";

export default function MovieCard({
  id,
  title,
  posterUrl,
  releaseYear,
  genres,
  tmdbRating,
  userRating,
  matchPercentage,
  inCatalog = true,
  showCatalogBadge = false,
  subtitle,
}) {
  const [imgFailed, setImgFailed] = React.useState(!posterUrl);

  const displayRating = tmdbRating != null && !isNaN(Number(tmdbRating)) && Number(tmdbRating) > 0
    ? Number(tmdbRating).toFixed(1)
    : null;

  const displayGenres = Array.isArray(genres)
    ? genres.filter(Boolean).slice(0, 2).join(" • ")
    : (typeof genres === "string" ? genres.split("|").filter(Boolean).slice(0, 2).join(" • ") : "");

  const infoText = subtitle || [releaseYear, displayGenres].filter(Boolean).join(" • ");

  return (
    <Link to={`/movie-details/${id}`} className="movie-card-component">
      <div className="movie-card-poster-wrap">
        {!imgFailed && posterUrl ? (
          <img
            src={posterUrl}
            alt={title}
            className="movie-card-img"
            onError={() => setImgFailed(true)}
            loading="lazy"
          />
        ) : (
          <div className="movie-card-placeholder">
            <span className="placeholder-clapper">🎬</span>
            <span className="placeholder-text">{title}</span>
            {releaseYear && <span className="placeholder-year">({releaseYear})</span>}
          </div>
        )}

        {/* TOP BADGES */}
        <div className="movie-card-badges-top">
          {displayRating && (
            <span className="badge-item badge-tmdb" title={`TMDB Rating: ${displayRating}/10`}>
              ★ TMDB {displayRating}
            </span>
          )}

          {userRating && Number(userRating) > 0 && (
            <span className="badge-item badge-user" title={`Your Rating: ${userRating}/5`}>
              ★ {userRating}/5
            </span>
          )}

          {matchPercentage && Number(matchPercentage) > 0 && (
            <span className="badge-item badge-match" title={`AI Match: ${Math.round(matchPercentage)}%`}>
              ✦ {Math.round(matchPercentage)}% Match
            </span>
          )}
        </div>

        {/* CATALOG STATUS BADGE */}
        {showCatalogBadge && (
          <div className="movie-card-badges-bottom">
            {inCatalog ? (
              <span className="badge-status badge-in-catalog">In Catalog</span>
            ) : (
              <span className="badge-status badge-tmdb-only">TMDB Only</span>
            )}
          </div>
        )}
      </div>

      <h3 className="movie-card-title" title={title}>{title}</h3>
      {infoText && <p className="movie-card-info">{infoText}</p>}
    </Link>
  );
}
