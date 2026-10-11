import "./Profile.css";
import { Link, useNavigate } from "react-router-dom";

import {
  getCurrentUser,
  logoutUser,
} from "../auth/auth";

function Profile() {
  const navigate = useNavigate();

  // Get currently logged-in user
  const user = getCurrentUser();

  // Get saved movies
  const savedMovies =
    JSON.parse(localStorage.getItem("myList")) || [];

  // Get watch history
  const watchHistory =
    JSON.parse(localStorage.getItem("watchHistory")) || [];

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
              0
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
              {watchHistory.length}
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
              {savedMovies.length}
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