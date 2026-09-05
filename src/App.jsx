import { BrowserRouter, Routes, Route } from "react-router-dom";

import Login from "./pages/Login";
import Signup from "./pages/Signup";
import Home from "./pages/Home";
import Search from "./pages/Search";
import Recommendations from "./pages/Recommendations";
import MyList from "./pages/MyList";
import History from "./pages/History";
import MovieDetails from "./pages/MovieDetails";

function App() {
  return (
    <BrowserRouter>
      <Routes>

        <Route path="/" element={<Login />} />
        <Route path="/login" element={<Login />} />
        <Route path="/signup" element={<Signup />} />

        <Route path="/home" element={<Home />} />

        <Route path="/search" element={<Search />} />

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

        <Route
          path="/movie-details/:id"
          element={<MovieDetails />}
        />

      </Routes>
    </BrowserRouter>
  );
}

export default App;