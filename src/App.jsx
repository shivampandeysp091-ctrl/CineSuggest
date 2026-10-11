import { BrowserRouter, Routes, Route } from "react-router-dom";

import Login from "./pages/Login";
import Signup from "./pages/Signup";
import ForgotPassword from "./pages/ForgotPassword";
import Onboarding from "./pages/Onboarding";

import Home from "./pages/Home";
import Search from "./pages/Search";
import Recommendations from "./pages/Recommendations";
import MyList from "./pages/MyList";
import History from "./pages/History";
import MovieDetails from "./pages/MovieDetails";

import Profile from "./pages/Profile";
import AccountSettings from "./pages/AccountSettings";
import ChangePassword from "./pages/ChangePassword";

function App() {
  return (
    <BrowserRouter>

      <Routes>

        {/* Authentication */}

        <Route
          path="/"
          element={<Login />}
        />

        <Route
          path="/login"
          element={<Login />}
        />

        <Route
          path="/signup"
          element={<Signup />}
        />

        <Route
          path="/onboarding"
          element={<Onboarding />}
        />

        <Route
          path="/forgot-password"
          element={<ForgotPassword />}
        />


        {/* Main Pages */}

        <Route
          path="/home"
          element={<Home />}
        />

        <Route
          path="/search"
          element={<Search />}
        />

        <Route
          path="/recommendations"
          element={<Recommendations />}
        />

        <Route
          path="/my-list"
          element={<MyList />}
        />

        <Route
          path="/history"
          element={<History />}
        />


        {/* Movie Details */}

        <Route
          path="/movie-details/:id"
          element={<MovieDetails />}
        />


        {/* Profile */}

        <Route
          path="/profile"
          element={<Profile />}
        />

        <Route
          path="/account-settings"
          element={<AccountSettings />}
        />

        <Route
          path="/change-password"
          element={<ChangePassword />}
        />

      </Routes>

    </BrowserRouter>
  );
}

export default App;