import "./Signup.css";
import { useState, useEffect } from "react";
import { useNavigate, useLocation, Link } from "react-router-dom";

import {
  registerUser,
  verifyOtp,
  resendOtp,
  isValidEmail,
  isStrongPassword,
} from "../auth/auth";

function Signup() {
  const navigate = useNavigate();
  const location = useLocation();

  const [step, setStep] = useState(location.state?.step || "register"); // "register" | "verify"
  const [name, setName] = useState("");
  const [email, setEmail] = useState(location.state?.email || "");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [otp, setOtp] = useState("");

  const [error, setError] = useState("");
  const [successMsg, setSuccessMsg] = useState(
    location.state?.message || ""
  );
  const [loading, setLoading] = useState(false);
  const [cooldown, setCooldown] = useState(0);

  // Handle resend cooldown countdown
  useEffect(() => {
    if (cooldown <= 0) return;
    const interval = setInterval(() => {
      setCooldown((prev) => Math.max(0, prev - 1));
    }, 1000);
    return () => clearInterval(interval);
  }, [cooldown]);

  const handleSignup = async (e) => {
    e.preventDefault();
    setError("");
    setSuccessMsg("");

    // Name validation
    if (name.trim().length < 2) {
      setError("Please enter your full name.");
      return;
    }

    // Email validation
    if (!isValidEmail(email)) {
      setError("Please enter a valid email address.");
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
      const cleanEmail = email.toLowerCase().trim();
      const result = await registerUser({
        name: name.trim(),
        email: cleanEmail,
        password: password,
      });

      if (!result.success) {
        setError(result.message);
        return;
      }

      if (result.needs_verification) {
        setStep("verify");
        setEmail(cleanEmail);
        setSuccessMsg(result.message || "Verification code sent to your email.");
        setCooldown(60);
      } else {
        navigate("/onboarding");
      }
    } catch (err) {
      setError("An unexpected error occurred. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyOtp = async (e) => {
    e.preventDefault();
    setError("");
    setSuccessMsg("");

    const cleanOtp = otp.trim();
    if (cleanOtp.length !== 6 || !/^\d{6}$/.test(cleanOtp)) {
      setError("Please enter the 6-digit numeric verification code.");
      return;
    }

    try {
      setLoading(true);
      const result = await verifyOtp(email.toLowerCase().trim(), cleanOtp);

      if (!result.success) {
        setError(result.message);
        return;
      }

      // Verified! User session is saved in auth.js
      navigate("/onboarding");
    } catch (err) {
      setError("Verification failed. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const handleResendOtp = async () => {
    if (cooldown > 0 || loading) return;
    setError("");
    setSuccessMsg("");

    try {
      setLoading(true);
      const result = await resendOtp(email.toLowerCase().trim());
      if (result.success) {
        setSuccessMsg(result.message || "A new code has been sent.");
        setCooldown(60);
      } else {
        setError(result.message);
      }
    } catch (err) {
      setError("Failed to resend code. Please try again.");
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
          {step === "register" ? (
            <>
              <h2>Create Account</h2>
              <p className="signup-subtitle">
                Join CineSuggest and discover movies made for you.
              </p>

              {error && <div className="auth-error">{error}</div>}
              {successMsg && <div className="auth-success">{successMsg}</div>}

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
                  placeholder="you@example.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                />
                <small className="password-hint">
                  Enter a valid email address to receive your verification code
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
                  onChange={(e) => setConfirmPassword(e.target.value)}
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
                Already have an account?{" "}
                <Link to="/login">Sign In</Link>
              </p>
            </>
          ) : (
            <>
              <h2>Verify Your Email</h2>
              <p className="signup-subtitle">
                Enter the 6-digit code sent to{" "}
                <strong style={{ color: "white" }}>{email}</strong>.
                This code expires in 15 minutes.
              </p>

              {error && <div className="auth-error">{error}</div>}
              {successMsg && <div className="auth-success">{successMsg}</div>}

              <form onSubmit={handleVerifyOtp}>
                <label>Verification Code</label>
                <input
                  type="text"
                  maxLength={6}
                  placeholder="123456"
                  className="otp-input"
                  value={otp}
                  onChange={(e) => setOtp(e.target.value.replace(/\D/g, ""))}
                  autoFocus
                  required
                />

                <button
                  type="submit"
                  className="signup-button"
                  disabled={loading || otp.length !== 6}
                >
                  {loading ? "Verifying..." : "Verify & Activate Account"}
                </button>
              </form>

              <div className="otp-actions">
                <button
                  type="button"
                  className="resend-button"
                  onClick={handleResendOtp}
                  disabled={cooldown > 0 || loading}
                >
                  {cooldown > 0 ? `Resend Code (${cooldown}s)` : "Resend Verification Code"}
                </button>

                <button
                  type="button"
                  className="back-to-signup"
                  onClick={() => {
                    setStep("register");
                    setError("");
                    setSuccessMsg("");
                  }}
                >
                  ← Back to change email
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

export default Signup;