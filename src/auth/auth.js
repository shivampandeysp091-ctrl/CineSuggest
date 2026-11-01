import { api, setToken } from "../api/client";

// ── localStorage key constants ────────────────────────────────────────────────
const AUTH_KEY         = "cinematchAuth";
const CURRENT_USER_KEY = "currentUser";

/** All user-scoped storage keys (keyed by userId) */
const _scopedKeys = (userId) => [
  `movieRatings_${userId}`,
  `watchHistory_${userId}`,
  `myList_${userId}`,
];

/** Legacy shared keys that must be cleared on logout to prevent cross-user leaks */
const _legacySharedKeys = [
  "movieRatings",
  "watchHistory",
  "myList",
];

// ── email validation ──────────────────────────────────────────────────────────

/**
 * Validates any properly formatted email address.
 * No longer restricted to @gmail.com — verification requires actual mailbox access.
 */
export const isValidEmail = (email) => {
  const emailRegex = /^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$/;
  return emailRegex.test((email || "").trim());
};

// ── password validation ───────────────────────────────────────────────────────

export const isStrongPassword = (password) => {
  const passwordRegex =
    /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$/;
  return passwordRegex.test(password);
};

// ── register ──────────────────────────────────────────────────────────────────

/**
 * Step 1 of registration: create unverified account and send OTP.
 * Does NOT log the user in. Returns { success, email, needs_verification }.
 */
export const registerUser = async (userData) => {
  try {
    const username = (userData.name || userData.username || "").trim();
    const email    = (userData.email || "").toLowerCase().trim();
    const password = userData.password;

    const data = await api.register(username, email, password);

    return {
      success:          true,
      message:          data.message || "Check your email for the verification code.",
      email:            data.email || email,
      needs_verification: true,
    };
  } catch (error) {
    return {
      success: false,
      message: error.message || "Registration failed. Please try again.",
    };
  }
};

// ── verify OTP ────────────────────────────────────────────────────────────────

/**
 * Step 2 of registration: verify 6-digit OTP.
 * On success: saves token, logs user in, returns { success, user }.
 */
export const verifyOtp = async (email, otp) => {
  try {
    const data = await api.verifyOtp(email, otp);

    if (data.access_token) {
      setToken(data.access_token);
      localStorage.setItem(AUTH_KEY, "true");
      const userObj = {
        id:         data.user_id,
        name:       data.username,
        username:   data.username,
        email:      data.email,
        ml_user_id: data.ml_user_id,
      };
      localStorage.setItem(CURRENT_USER_KEY, JSON.stringify(userObj));
      return { success: true, user: userObj };
    }

    return { success: false, message: "Verification succeeded but no token returned." };
  } catch (error) {
    return {
      success: false,
      message: error.message || "OTP verification failed. Please try again.",
    };
  }
};

// ── resend OTP ────────────────────────────────────────────────────────────────

export const resendOtp = async (email) => {
  try {
    const data = await api.resendOtp(email);
    return { success: true, message: data.message || "OTP resent." };
  } catch (error) {
    return {
      success: false,
      message: error.message || "Could not resend OTP. Please try again later.",
    };
  }
};

// ── login ─────────────────────────────────────────────────────────────────────

export const loginUser = async (email, password) => {
  try {
    const cleanEmail = (email || "").toLowerCase().trim();
    const data = await api.login(cleanEmail, password);

    if (data.access_token) {
      setToken(data.access_token);
      localStorage.setItem(AUTH_KEY, "true");
      const userObj = {
        id:         data.user_id,
        name:       data.username,
        username:   data.username,
        email:      data.email,
        ml_user_id: data.ml_user_id,
      };
      localStorage.setItem(CURRENT_USER_KEY, JSON.stringify(userObj));
      return { success: true, user: userObj, token: data.access_token };
    }

    return { success: false, message: "No token returned from server." };
  } catch (error) {
    // 403 = email not verified
    if (error.status === 403 && error.message === "email_not_verified") {
      return {
        success:          false,
        needs_verification: true,
        email:            email.toLowerCase().trim(),
        message:          "Please verify your email before logging in.",
      };
    }
    return {
      success: false,
      message: error.message || "Invalid credentials. Please check your email and password.",
    };
  }
};

// ── logout ────────────────────────────────────────────────────────────────────

/**
 * Clears ALL user-specific state from localStorage to prevent cross-user leaks.
 * Removes both legacy shared keys and any scoped keys for the current user.
 */
export const logoutUser = () => {
  // Identify the current user before wiping identity keys
  const raw = localStorage.getItem(CURRENT_USER_KEY);
  let userId = null;
  try {
    userId = raw ? JSON.parse(raw)?.id : null;
  } catch (_) {}

  // Clear scoped keys (new format)
  if (userId) {
    _scopedKeys(userId).forEach((k) => localStorage.removeItem(k));
  }

  // Clear legacy shared keys (old format — may contain previous user's data)
  _legacySharedKeys.forEach((k) => localStorage.removeItem(k));

  // Clear individual movie-rating-* keys (legacy pattern used in MovieDetails)
  Object.keys(localStorage)
    .filter((k) => k.startsWith("movie-rating-"))
    .forEach((k) => localStorage.removeItem(k));

  // Clear auth identity
  localStorage.removeItem(AUTH_KEY);
  localStorage.removeItem(CURRENT_USER_KEY);
  setToken(null);
};

// ── session helpers ───────────────────────────────────────────────────────────

export const isLoggedIn = () =>
  localStorage.getItem(AUTH_KEY) === "true" && !!localStorage.getItem("token");

export const getCurrentUser = () => {
  const raw = localStorage.getItem(CURRENT_USER_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw);
  } catch (_) {
    return null;
  }
};

// ── scoped localStorage helpers (for components) ──────────────────────────────

/**
 * Returns a userId-scoped localStorage key to prevent cross-user data leaks.
 * Falls back to the legacy shared key if no user is logged in.
 */
export const getScopedKey = (baseKey) => {
  const user = getCurrentUser();
  return user?.id ? `${baseKey}_${user.id}` : baseKey;
};