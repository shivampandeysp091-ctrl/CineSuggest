import "./Profile.css";
import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import {
  getCurrentUser,
  getScopedKey,
  logoutUser,
} from "../auth/auth";
import { api } from "../api/client";

function Profile() {
  const navigate = useNavigate();

  // Get currently logged-in user
  const user = getCurrentUser();

  const [ratedCount, setRatedCount] = useState(0);
  const [watchedCount, setWatchedCount] = useState(0);
  const [savedCount, setSavedCount] = useState(0);

  useEffect(() => {
    let isMounted = true;

    // Load initial values from scoped local storage
    try {
      const saved = JSON.parse(localStorage.getItem(getScopedKey("myList")) || "[]");
      const watched = JSON.parse(localStorage.getItem(getScopedKey("watchHistory")) || "[]");
      const rated = JSON.parse(localStorage.getItem(getScopedKey("movieRatings")) || "{}");
      if (isMounted) {
        setSavedCount(Array.isArray(saved) ? saved.length : 0);
        setWatchedCount(Array.isArray(watched) ? watched.length : 0);
        setRatedCount(Object.keys(rated).length);
      }
    } catch (_) {}

    // Fetch authoritative stats from backend
    async function loadStats() {
      try {
        const [ratingsRes, historyRes, favoritesRes] = await Promise.allSettled([
          api.getRatings(),
          api.getWatchHistory(),
          api.getFavorites(),
        ]);

        if (isMounted) {
          if (ratingsRes.status === "fulfilled" && Array.isArray(ratingsRes.value)) {
            setRatedCount(ratingsRes.value.length);
          }
          if (historyRes.status === "fulfilled" && Array.isArray(historyRes.value?.watch_history)) {
            setWatchedCount(historyRes.value.watch_history.length);
          }
          if (favoritesRes.status === "fulfilled" && Array.isArray(favoritesRes.value?.favorites)) {
            setSavedCount(favoritesRes.value.favorites.length);
          }
        }
      } catch (err) {
        console.warn("Failed to load user stats from backend:", err);
      }
    }

    loadStats();
    return () => { isMounted = false; };
  }, []);

  // Logout
  const handleLogout = () => {
    logoutUser();
    navigate("/login", { replace: true });
  };

  // Get user's initial
  const userInitial =
    user?.name?.trim()?.charAt(0)?.toUpperCase() || "A";

  return (
    <div className="profile-page">

      {/* =====================================================
          NAVBAR
      ===================================================== */}

      <nav className="navbar">

        <div className="logo">
          <span>🎬</span>
          CineSuggest
        </div>

        <div className="nav-links">

          <Link to="/home">
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

        {/* Profile Avatar */}
        <Link
          to="/profile"
          className="profile-circle"
          title="Profile"
        >
          {userInitial}
        </Link>

      </nav>


      {/* =====================================================
          PROFILE CONTAINER
      ===================================================== */}

      <main className="profile-container">


        {/* ===================================================
            PROFILE HEADER
        =================================================== */}

        <section className="profile-header">

          {/* Avatar */}
          <div className="profile-avatar">
            {userInitial}
          </div>


          {/* User Information */}
          <div className="profile-info">

            <div className="profile-name-row">

              <h1>
                {user?.name || "CineMatch User"}
              </h1>

            </div>

            <p>
              {user?.email || "user@gmail.com"}
            </p>

          </div>


          {/* Edit Profile */}
          <Link
            to="/account-settings"
            className="edit-profile"
          >
            Edit Profile
          </Link>

        </section>


        {/* ===================================================
            STATS
        =================================================== */}

        <section className="profile-stats">


          {/* ================= MOVIES RATED ================= */}

          <Link
            to="/recommendations"
            className="stat-card"
          >

            <span>
              Movies Rated
            </span>

            <strong>
              {ratedCount}
            </strong>

            <small>
              View recommendations →
            </small>

          </Link>


          {/* ================= MOVIES WATCHED ================= */}

          <Link
            to="/history"
            className="stat-card"
          >

            <span>
              Movies Watched
            </span>

            <strong>
              {watchedCount}
            </strong>

            <small>
              View watch history →
            </small>

          </Link>


          {/* ================= MOVIES SAVED ================= */}

          <Link
            to="/my-list"
            className="stat-card"
          >

            <span>
              Movies Saved
            </span>

            <strong>
              {savedCount}
            </strong>

            <small>
              View my list →
            </small>

          </Link>

        </section>


        {/* ===================================================
            FAVORITE GENRES
        =================================================== */}

        <section className="genres-section">

          <h2>
            Favorite Genres
          </h2>

          <div className="genre-list">

            <span>Action</span>

            <span>Drama</span>

            <span>Comedy</span>

            <span>Sci-Fi</span>

            <span>Thriller</span>

          </div>

        </section>


        {/* ===================================================
            ACCOUNT SETTINGS
        =================================================== */}

        <section className="account-section">

          <h2>
            Account Settings
          </h2>


          <div className="settings-box">


            {/* ================= ACCOUNT SETTINGS ================= */}

            <Link
              to="/account-settings"
              className="setting-item"
            >

              <div>

                <h3>
                  Account Settings
                </h3>

                <p>
                  Manage your profile and general system configurations
                </p>

              </div>

              <span>
                ›
              </span>

            </Link>


            {/* ================= CHANGE PASSWORD ================= */}

            <Link
              to="/change-password"
              className="setting-item"
            >

              <div>

                <h3>
                  Change Password
                </h3>

                <p>
                  Update your account password
                </p>

              </div>

              <span>
                ›
              </span>

            </Link>


            {/* ================= LOGOUT ================= */}

            <button
              className="logout-item"
              onClick={handleLogout}
            >

              <div>

                <h3>
                  Logout
                </h3>

                <p>
                  Safely sign out from CineSuggest
                </p>

              </div>

              <span>
                ⇥
              </span>

            </button>

          </div>

        </section>

      </main>

    </div>
  );
}

export default Profile;