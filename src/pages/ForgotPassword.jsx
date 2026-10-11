import "./ForgotPassword.css";
import { useState } from "react";
import { Link } from "react-router-dom";

function ForgotPassword() {

  const [email, setEmail] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const handleSubmit = (e) => {

    e.preventDefault();

    setMessage("");
    setError("");

    if (!email) {
      setError("Please enter your email address.");
      return;
    }

    if (!email.toLowerCase().endsWith("@gmail.com")) {
      setError("Please enter a valid Gmail address.");
      return;
    }

    const users =
      JSON.parse(localStorage.getItem("users")) || [];

    const user = users.find(
      (u) => u.email?.toLowerCase() === email.toLowerCase()
    );

    if (!user) {
      setError("No account found with this email address.");
      return;
    }

    setMessage(
      "Account found. You can now reset your password."
    );
  };

  return (
    <div className="forgot-password-page">

      <div className="forgot-password-container">

        <Link
          to="/login"
          className="back-to-login"
        >
          ← Back to Login
        </Link>

        <div className="forgot-password-card">

          <div className="forgot-icon">
            🔐
          </div>

          <h1>
            Forgot Password?
          </h1>

          <p className="forgot-subtitle">
            Enter your registered Gmail address to reset your password.
          </p>

          {error && (
            <div className="forgot-error">
              {error}
            </div>
          )}

          {message && (
            <div className="forgot-success">
              {message}
            </div>
          )}

          <form onSubmit={handleSubmit}>

            <label>
              Email Address
            </label>

            <input
              type="email"
              placeholder="example@gmail.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />

            <button
              type="submit"
              className="reset-button"
            >
              Continue
            </button>

          </form>

          <p className="login-link-text">
            Remember your password?
            <Link to="/login">
              {" "}Sign In
            </Link>
          </p>

        </div>

      </div>

    </div>
  );
}

export default ForgotPassword;