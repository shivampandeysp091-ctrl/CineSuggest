import { api, setToken } from "../api/client";

const AUTH_KEY = "cinematchAuth";
const CURRENT_USER_KEY = "currentUser";

// ===============================
// EMAIL VALIDATION
// ===============================

export const isValidEmail = (email) => {
  const gmailRegex = /^[a-zA-Z0-9._%+-]+@gmail\.com$/;
  return gmailRegex.test(email);
};

// ===============================
// PASSWORD VALIDATION
// ===============================

export const isStrongPassword = (password) => {
  const passwordRegex =
    /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$/;

  return passwordRegex.test(password);
};

// ===============================
// REGISTER USER (Backend API)
// ===============================

export const registerUser = async (userData) => {
  try {
    const username = (userData.name || userData.username || "").trim();
    const email = (userData.email || "").toLowerCase().trim();
    const password = userData.password;

    const data = await api.register(username, email, password);

    // Save auth state & token
    if (data.access_token) {
      setToken(data.access_token);
      localStorage.setItem(AUTH_KEY, "true");
      const userObj = {
        id: data.user_id,
        name: data.username,
        username: data.username,
        email: data.email,
        ml_user_id: data.ml_user_id,
      };
      localStorage.setItem(CURRENT_USER_KEY, JSON.stringify(userObj));
    }

    return {
      success: true,
      message: data.message || "Account created successfully.",
      user: data,
    };
  } catch (error) {
    return {
      success: false,
      message: error.message || "Registration failed. Please try again.",
    };
  }
};

// ===============================
// LOGIN USER (Backend API)
// ===============================

export const loginUser = async (email, password) => {
  try {
    const cleanEmail = (email || "").toLowerCase().trim();
    const data = await api.login(cleanEmail, password);

    if (data.access_token) {
      setToken(data.access_token);
      localStorage.setItem(AUTH_KEY, "true");
      const userObj = {
        id: data.user_id,
        name: data.username,
        username: data.username,
        email: data.email,
        ml_user_id: data.ml_user_id,
      };
      localStorage.setItem(CURRENT_USER_KEY, JSON.stringify(userObj));

      return {
        success: true,
        user: userObj,
        token: data.access_token,
      };
    }

    return {
      success: false,
      message: "No token returned from server.",
    };
  } catch (error) {
    return {
      success: false,
      message: error.message || "Invalid credentials. Please check your email and password.",
    };
  }
};

// ===============================
// LOGOUT
// ===============================

export const logoutUser = () => {
  localStorage.removeItem(AUTH_KEY);
  localStorage.removeItem(CURRENT_USER_KEY);
  setToken(null);
};

// ===============================
// CHECK LOGIN
// ===============================

export const isLoggedIn = () => {
  return localStorage.getItem(AUTH_KEY) === "true" && !!localStorage.getItem("token");
};

// ===============================
// GET CURRENT USER
// ===============================

export const getCurrentUser = () => {
  const user = localStorage.getItem(CURRENT_USER_KEY);

  if (!user) {
    return null;
  }

  try {
    return JSON.parse(user);
  } catch (error) {
    return null;
  }
};