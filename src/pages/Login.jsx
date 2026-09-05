import "./Login.css";
import { useNavigate, Link } from "react-router-dom";

function Login() {
  const navigate = useNavigate();

  const handleLogin = (e) => {
    e.preventDefault();
    navigate("/home");
  };

  return (
    <div className="login-page">

      {/* Left Side - Movie Visual */}
      <div className="login-visual">

        <div className="visual-overlay">
          <h1>Cinematic AI</h1>

          <p>
            Discover movies you'll love,
            powered by AI.
          </p>
        </div>

      </div>


      {/* Right Side - Login Form */}
      <div className="login-form-section">

        <div className="login-container">

          <h2>Welcome Back</h2>

          <p className="login-subtitle">
            Sign in to continue your cinematic journey
          </p>


          <form onSubmit={handleLogin}>

            <label>Email</label>

            <input
              type="email"
              placeholder="Enter your email"
              required
            />


            <label>Password</label>

            <input
              type="password"
              placeholder="Enter your password"
              required
            />


            <div className="login-options">

              <label className="remember">
                <input type="checkbox" />
                Remember me
              </label>

              <a href="#">
                Forgot Password?
              </a>

            </div>


            <button
              type="submit"
              className="login-button"
            >
              Sign In
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