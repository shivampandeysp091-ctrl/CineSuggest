import "./Login.css";
import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";

import {
  loginUser,
  isValidEmail,
} from "../auth/auth";

function Login() {

  const navigate = useNavigate();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleLogin = async (e) => {
    e.preventDefault();
    setError("");

    // Email validation
    if (!isValidEmail(email)) {
      setError("Please enter a valid email address.");
      return;
    }

    if (!password) {
      setError("Please enter your password.");
      return;
    }

    try {
      setLoading(true);
      const cleanEmail = email.toLowerCase().trim();
      const result = await loginUser(cleanEmail, password);

      if (!result.success) {
        if (result.needs_verification) {
          // Redirect to Signup OTP verification screen with email pre-filled
          navigate("/signup", {
            state: {
              email: cleanEmail,
              step: "verify",
              message: "Please enter your verification code to activate your account.",
            },
          });
          return;
        }
        setError(result.message);
        return;
      }

      navigate("/home");
    } catch (err) {
      setError("An unexpected error occurred. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-page">

      {/* LEFT SIDE */}

      <div className="login-visual">

        <div className="visual-overlay">

          <h1>CineSuggest</h1>

          <p>
            Discover movies you'll love,
            powered by AI.
          </p>

        </div>

      </div>


      {/* RIGHT SIDE */}

      <div className="login-form-section">

        <div className="login-container">

          <h2>Welcome Back</h2>

          <p className="login-subtitle">
            Sign in to continue your cinematic journey
          </p>


          {error && (
            <div className="auth-error">
              {error}
            </div>
          )}


          <form onSubmit={handleLogin}>

            <label>Email</label>

            <input
              type="email"
              placeholder="you@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />


            <label>Password</label>

            <input
              type="password"
              placeholder="Enter your password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />


            <div className="login-options">

              <label className="remember">

                <input type="checkbox" />

                Remember me

              </label>

            <Link to="/forgot-password">
  Forgot Password?
</Link>
            </div>


            <button
              type="submit"
              className="login-button"
              disabled={loading}
            >
              {loading ? "Signing In..." : "Sign In"}
            </button>

          </form>


          <p className="signup-text">

            Don't have an account?

            <Link to="/signup">
              {" "}Create Account
            </Link>

          </p>

        </div>

      </div>

    </div>
  );
}

export default Login;