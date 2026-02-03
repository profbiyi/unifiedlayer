import axios from "axios";

/**
 * Axios API client with HTTPOnly cookie authentication.
 *
 * Uses withCredentials to automatically send HTTPOnly cookies with every request.
 * This is more secure than localStorage as cookies can't be accessed via JavaScript (XSS protection).
 */
const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || "/api",
  headers: {
    "Content-Type": "application/json",
  },
  withCredentials: true, // Send cookies with every request
});

// Response interceptor: Handle 401 errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Redirect to login on authentication failure
      if (typeof window !== "undefined") {
        window.location.href = "/login";
      }
    }
    return Promise.reject(error);
  }
);

export default api;
