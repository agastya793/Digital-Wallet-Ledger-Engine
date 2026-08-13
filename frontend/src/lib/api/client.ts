import axios from 'axios';
import { useAuthStore } from '../../stores/authStore';

export const apiClient = axios.create({
  baseURL: 'http://localhost:8000/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true, // IMPORTANT: Allows sending HttpOnly cookies
});

// Intercept requests and add the JWT token if available
apiClient.interceptors.request.use(
  (config) => {
    const token = useAuthStore.getState().token;
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Flag to prevent infinite retry loops
let isRefreshing = false;
let failedQueue: Array<{ resolve: (token: string) => void; reject: (error: any) => void }> = [];

const processQueue = (error: any, token: string | null = null) => {
  failedQueue.forEach((prom) => {
    if (error) {
      prom.reject(error);
    } else {
      prom.resolve(token as string);
    }
  });
  failedQueue = [];
};

apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    // Check if the error is 401, not from login/refresh endpoints, and hasn't been retried yet
    if (
      error.response?.status === 401 &&
      originalRequest.url !== '/auth/login' &&
      originalRequest.url !== '/auth/refresh' &&
      !originalRequest._retry
    ) {
      if (isRefreshing) {
        // If already refreshing, queue the request until refresh finishes
        return new Promise(function (resolve, reject) {
          failedQueue.push({ resolve, reject });
        })
          .then((token) => {
            originalRequest.headers.Authorization = `Bearer ${token}`;
            return apiClient(originalRequest);
          })
          .catch((err) => {
            return Promise.reject(err);
          });
      }

      originalRequest._retry = true;
      isRefreshing = true;

      try {
        // Attempt to get a new access token using the HttpOnly refresh token cookie
        const response = await axios.post(
          'http://localhost:8000/api/v1/auth/refresh',
          {},
          { withCredentials: true }
        );

        const { access_token } = response.data;
        
        // After a successful refresh, we should also fetch the user profile 
        // to restore the email in the store if it's missing (e.g. after a hard reload)
        const meResponse = await axios.get('http://localhost:8000/api/v1/auth/me', {
          headers: { Authorization: `Bearer ${access_token}` },
        });

        useAuthStore.getState().setAuth(access_token, meResponse.data.email);

        processQueue(null, access_token);
        
        originalRequest.headers.Authorization = `Bearer ${access_token}`;
        return apiClient(originalRequest);
      } catch (refreshError) {
        processQueue(refreshError, null);
        useAuthStore.getState().logout();
        window.location.href = '/login';
        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
      }
    }

    // Direct 401s on login or failed refresh should clear state
    if (error.response?.status === 401) {
       useAuthStore.getState().logout();
    }
    
    return Promise.reject(error);
  }
);
