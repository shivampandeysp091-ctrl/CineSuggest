import "./Signup.css";
import { useNavigate, Link } from "react-router-dom";

function Signup() {
  const navigate = useNavigate();

  const handleSignup = (e) => {
  e.preventDefault();
  navigate("/");
};

  return (
    <div className="signup-page">

      {/* Left Side - Movie Visual */}
      <div className="signup-visual">

        <div className="signup-visual-overlay">
          <h1>Cinematic AI</h1>

          <p>
            Your next favorite movie
            is waiting for you.
          </p>
        </div>

      </div>


      {/* Right Side - Signup Form */}
      <div className="signup-form-section">

        <div className="signup-container">

          <h2>Create Account</h2>

          <p className="signup-subtitle">
            Join Cinematic AI and discover movies made for you.
          </p>


          <form onSubmit={handleSignup}>

            <label>Full Name</label>

            <input
              type="text"
              placeholder="Enter your name"
              required
            />


            <label>Email</label>

            <input
              type="email"
              placeholder="Enter your email"
              required
            />


            <label>Password</label>

            <input
              type="password"
              placeholder="Create a password"
              required
            />


            <label>Confirm Password</label>

            <input
              type="password"
              placeholder="Confirm your password"
              required
            />


            <button
              type="submit"
              className="signup-button"
            >
              Create Account
            </button>

          </form>


          <p className="login-text">

            Already have an account?

            <Link to="/">
              {" "}Sign In
            </Link>

          </p>

        </div>

      </div>

    </div>
  );
}

export default Signup;