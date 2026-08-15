import axios from "axios";

// In production the frontend and API can share the same origin. For a separate
// backend deployment, set REACT_APP_BACKEND_URL in the frontend deployment env.
const configuredBackend = (process.env.REACT_APP_BACKEND_URL || "").trim();
const BACKEND_URL = configuredBackend || window.location.origin;
export const API = `${BACKEND_URL.replace(/\/$/, "")}/api`;

export const api = axios.create({
  baseURL: API,
  withCredentials: true,
});

api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem("token");
    if (token && token !== "undefined" && token !== "null") {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

export function formatApiErrorDetail(detail) {
  if (detail == null) return "Something went wrong. Please try again.";
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((e) => (e && typeof e.msg === "string" ? e.msg : JSON.stringify(e)))
      .filter(Boolean)
      .join(" ");
  }
  if (detail && typeof detail.msg === "string") return detail.msg;
  return String(detail);
}
