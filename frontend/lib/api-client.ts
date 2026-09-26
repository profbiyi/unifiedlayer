import axios, { AxiosError, InternalAxiosRequestConfig } from "axios";

/**
 * Axios API client — cookie-based auth.
 *
 * The access and refresh tokens live in httpOnly cookies set by the backend, so
 * JavaScript never touches them (an XSS cannot exfiltrate the session). Requests
 * go to the same origin (`/api/v1`, proxied to the backend by the Next.js rewrite
 * in next.config.js) with `withCredentials` so the browser attaches the cookies.
 * On a 401 we transparently hit `/auth/refresh` (which reads the refresh cookie)
 * and retry once.
 */

// Same-origin API root; the Next.js rewrite proxies /api/* to the backend so the
// auth cookies are first-party.
const API_BASE = "/api/v1";

// Prevent multiple simultaneous refresh attempts.
let isRefreshing = false;
let failedQueue: Array<{
  resolve: (value?: unknown) => void;
  reject: (reason?: unknown) => void;
}> = [];

const processQueue = (error: Error | null) => {
  failedQueue.forEach((prom) => {
    if (error) {
      prom.reject(error);
    } else {
      prom.resolve();
    }
  });
  failedQueue = [];
};

const api = axios.create({
  baseURL: API_BASE,
  timeout: 30000,
  withCredentials: true, // send the httpOnly auth cookies
  headers: {
    "Content-Type": "application/json",
  },
});

// Response interceptor: on 401, try a cookie-based token refresh once, then retry.
api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & {
      _retry?: boolean;
    };

    if (error.response?.status !== 401) {
      return Promise.reject(error);
    }

    // Don't try to refresh the refresh call itself, and only retry once.
    if (originalRequest._retry || originalRequest.url?.includes("/auth/refresh")) {
      clearSessionAndRedirect();
      return Promise.reject(error);
    }

    if (typeof window === "undefined") {
      return Promise.reject(error);
    }

    // If a refresh is already in flight, queue this request behind it.
    if (isRefreshing) {
      return new Promise((resolve, reject) => {
        failedQueue.push({ resolve, reject });
      })
        .then(() => api(originalRequest))
        .catch((err) => Promise.reject(err));
    }

    originalRequest._retry = true;
    isRefreshing = true;

    try {
      // The refresh token rides in an httpOnly cookie; nothing to send in the body.
      await axios.post(`${API_BASE}/auth/refresh`, null, {
        withCredentials: true,
        timeout: 30000,
      });

      processQueue(null);
      return api(originalRequest);
    } catch (refreshError) {
      processQueue(refreshError as Error);
      clearSessionAndRedirect();
      return Promise.reject(refreshError);
    } finally {
      isRefreshing = false;
    }
  }
);

function clearSessionAndRedirect() {
  if (typeof window !== "undefined") {
    if (!window.location.pathname.includes("/login")) {
      window.location.href = "/login";
    }
  }
}

export default api;

// Token management is now handled entirely by httpOnly cookies. These helpers are
// retained as no-ops so existing callers keep working; there is no JS-readable token.
export const setToken = (_token?: string) => {};
export const setRefreshToken = (_token?: string) => {};
export const getToken = (): string | null => null;
export const getRefreshToken = (): string | null => null;
export const removeToken = () => {};
export const removeRefreshToken = () => {};
export const clearAllTokens = () => {};
