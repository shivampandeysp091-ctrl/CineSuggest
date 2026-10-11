/**
 * CineSuggest API Client
 * Centralized service to connect React frontend with FastAPI backend.
 */

const API_BASE_URL = (import.meta.env.VITE_API_URL || "http://127.0.0.1:8000").replace(/\/+$/, "");

export function getToken() {
  return localStorage.getItem("token") || "";
}

export function setToken(token) {
  if (token) {
    localStorage.setItem("token", token);
  } else {
    localStorage.removeItem("token");
  }
}

async function request(endpoint, options = {}) {
  const url = `${API_BASE_URL}${endpoint}`;
  const token = getToken();

  const headers = {
    ...options.headers,
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  // Handle JSON body
  if (options.body && typeof options.body === "object" && !(options.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
    options.body = JSON.stringify(options.body);
  }

  try {
    const response = await fetch(url, {
      ...options,
      headers,
    });

    const isJson = response.headers.get("content-type")?.includes("application/json");
    const data = isJson ? await response.json() : await response.text();

    if (!response.ok) {
      const errorMsg = data?.detail || data?.message || `HTTP ${response.status}: Request failed`;
      const err = new Error(errorMsg);
      err.status = response.status;
      err.data = data;
      throw err;
    }

    return data;
  } catch (error) {
    console.error(`API Error on [${options.method || "GET"} ${endpoint}]:`, error);
    throw error;
  }
}

export const api = {
  // ── Authentication ──────────────────────────────────────────────────────────
  async login(email, password) {
    return request("/auth/login", {
      method: "POST",
      body: { email, password },
    });
  },

  async register(username, email, password) {
    return request("/auth/register", {
      method: "POST",
      body: { username, email, password },
    });
  },

  // ── Movies ──────────────────────────────────────────────────────────────────
  async getMovies() {
    return request("/movies/");
  },

  async getMovie(movieId) {
    return request(`/movies/${movieId}`);
  },

  async searchMovies(title) {
    return request(`/movies/search?title=${encodeURIComponent(title)}`);
  },

  async getTopRated(limit = 20) {
    return request(`/movies/top-rated?limit=${limit}`);
  },

  async getTrending() {
    return request("/movies/trending");
  },

  async getNowPlaying() {
    return request("/movies/now-playing");
  },

  async getUpcoming() {
    return request("/movies/upcoming");
  },

  async getNewReleases() {
    return request("/movies/new-releases");
  },

  async getTmdbMovie(tmdbId) {
    return request(`/movies/tmdb/${tmdbId}`);
  },

  async getOnboardingMovies(n = 12) {
    return request(`/movies/onboarding?n=${n}`);
  },

  // ── Recommendations ─────────────────────────────────────────────────────────
  async getRecommendations(n = 10) {
    return request(`/recommendations/me?n=${n}`);
  },

  // ── Favorites ───────────────────────────────────────────────────────────────
  async getFavorites() {
    return request("/favorites/me");
  },

  async addFavorite(movieId) {
    return request("/favorites/", {
      method: "POST",
      body: { movie_id: parseInt(movieId, 10) },
    });
  },

  async removeFavorite(movieId) {
    return request(`/favorites/${movieId}`, {
      method: "DELETE",
    });
  },

  async checkFavorite(movieId) {
    return request(`/favorites/check/${movieId}`);
  },

  // ── Watch History ───────────────────────────────────────────────────────────
  async getWatchHistory() {
    return request("/watch-history/me");
  },

  async addWatchHistory(movieId) {
    return request("/watch-history/", {
      method: "POST",
      body: { movie_id: parseInt(movieId, 10) },
    });
  },

  async removeWatchHistory(movieId) {
    return request(`/watch-history/${movieId}`, {
      method: "DELETE",
    });
  },

  // ── Ratings ─────────────────────────────────────────────────────────────────
  async getRatings() {
    return request("/ratings/me");
  },

  async rateMovie(movieId, rating) {
    return request("/ratings/", {
      method: "POST",
      body: { movie_id: parseInt(movieId, 10), rating: parseFloat(rating) },
    });
  },

  async deleteRating(movieId) {
    return request(`/ratings/${movieId}`, {
      method: "DELETE",
    });
  },
};

export default api;
