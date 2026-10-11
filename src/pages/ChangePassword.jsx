import "./ChangePassword.css";
import { useState } from "react";
import { Link } from "react-router-dom";

function ChangePassword() {

  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [message, setMessage] = useState("");

  const handleChangePassword = (e) => {

    e.preventDefault();

    setMessage("");

    if (!currentPassword || !newPassword || !confirmPassword) {
      setMessage("Please fill in all fields.");
      return;
    }

    if (newPassword !== confirmPassword) {
      setMessage("New passwords do not match.");
      return;
    }

    if (newPassword.length < 6) {
      setMessage("Password must contain at least 6 characters.");
      return;
    }

    /*
      Frontend demo:
      Password change can be connected to backend authentication later.
    */

    setMessage("Password changed successfully.");

    setCurrentPassword("");
    setNewPassword("");
    setConfirmPassword("");
  };

  return (
    <div className="change-password-page">

      <div className="password-container">

        <Link to="/profile" className="back-button">
          ← Back to Profile
        </Link>

        <div className="password-card">

          <p className="password-label">
            SECURITY
          </p>

          <h1>
            Change Password
          </h1>

          <p className="password-subtitle">
            Update your password to keep your account secure.
          </p>

          <form onSubmit={handleChangePassword}>

            <div className="form-group">
              <label>
                Current Password
              </label>

              <input
                type="password"
                value={currentPassword}
                onChange={(e) =>
                  setCurrentPassword(e.target.value)
                }
                placeholder="Enter current password"
              />
            </div>


            <div className="form-group">
              <label>
                New Password
              </label>

              <input
                type="password"
                value={newPassword}
                onChange={(e) =>
                  setNewPassword(e.target.value)
                }
                placeholder="Enter new password"
              />
            </div>


            <div className="form-group">
              <label>
                Confirm New Password
              </label>

              <input
                type="password"
                value={confirmPassword}
                onChange={(e) =>
                  setConfirmPassword(e.target.value)
                }
                placeholder="Confirm new password"
              />
            </div>


            {message && (
              <p className="password-message">
                {message}
              </p>
            )}


            <button
              type="submit"
              className="change-password-button"
            >
              Change Password
            </button>

          </form>

        </div>

      </div>

    </div>
  );
}

export default ChangePassword;