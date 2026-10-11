import "./Signup.css";
import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";

import {
  registerUser,
  isValidEmail,
  isStrongPassword,
} from "../auth/auth";

function Signup() {

  const navigate = useNavigate();

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");

  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSignup = async (e) => {
    e.preventDefault();
    setError("");

    // Name validation
    if (name.trim().length < 2) {
      setError("Please enter your full name.");
      return;
    }

    // Gmail validation
    if (!isValidEmail(email)) {
      setError("Please use a valid Gmail address.");
      return;
    }

    // Password validation
    if (!isStrongPassword(password)) {
      setError(
        "Password must contain at least 8 characters, one uppercase letter, one lowercase letter, one number and one special character."
      );
      return;
    }

    // Confirm password
    if (password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }

    try {
      setLoading(true);
      // Create account via Backend API
      const result = await registerUser({
        name: name.trim(),
        email: email.toLowerCase(),
        password: password,
      });

      if (!result.success) {
        setError(result.message);
        return;
      }

      navigate("/onboarding");
    } catch (err) {
      setError("An unexpected error occurred. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="signup-page">

      <div className="signup-visual">

        <div className="signup-visual-overlay">

          <h1>CineSuggest</h1>

          <p>
            Your next favorite movie
            is waiting for you.
          </p>

        </div>

      </div>


      <div className="signup-form-section">

        <div className="signup-container">

          <h2>Create Account</h2>

          <p className="signup-subtitle">
            Join CineSuggest and discover movies made for you.
          </p>


          {error && (
            <div className="auth-error">
              {error}
            </div>
          )}


          <form onSubmit={handleSignup}>

            <label>Full Name</label>

            <input
              type="text"
              placeholder="Enter your name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
            />


            <label>Email</label>

            <input
              type="email"
              placeholder="example@gmail.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />

            <small className="password-hint">
              Use a Gmail address ending with @gmail.com
            </small>


            <label>Password</label>

            <input
              type="password"
              placeholder="Create a strong password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />

            <small className="password-hint">
              8+ characters, uppercase, lowercase, number & special character
            </small>


            <label>Confirm Password</label>

            <input
              type="password"
              placeholder="Confirm your password"
              value={confirmPassword}
              onChange={(e) =>
                setConfirmPassword(e.target.value)
              }
              required
            />


            <button
              type="submit"
              className="signup-button"
              disabled={loading}
            >
              {loading ? "Creating Account..." : "Create Account"}
            </button>

          </form>


          <p className="login-text">

            Already have an account?

            <Link to="/login">
              {" "}Sign In
            </Link>

          </p>

        </div>

      </div>

    </div>
  );
}

export default Signup;