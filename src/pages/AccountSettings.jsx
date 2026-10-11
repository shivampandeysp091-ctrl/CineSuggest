import "./AccountSettings.css";
import { Link } from "react-router-dom";
import { getCurrentUser } from "../auth/auth";

function AccountSettings() {
  const user = getCurrentUser();

  return (
    <div className="account-settings-page">

      <div className="settings-container">

        <Link to="/profile" className="back-button">
          ← Back to Profile
        </Link>

        <div className="settings-card">

          <p className="settings-label">
            ACCOUNT
          </p>

          <h1>
            Account Settings
          </h1>

          <p className="settings-subtitle">
            Manage your profile information.
          </p>

          <div className="form-group">
            <label>Name</label>

            <input
              type="text"
              value={user?.name || ""}
              readOnly
            />
          </div>

          <div className="form-group">
            <label>Email</label>

            <input
              type="email"
              value={user?.email || ""}
              readOnly
            />
          </div>

          <div className="account-info">
            <span>Account Status</span>
            <strong>Active</strong>
          </div>

        </div>

      </div>

    </div>
  );
}

export default AccountSettings;