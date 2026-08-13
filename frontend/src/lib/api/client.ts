import axios from 'axios';
import { useAuthStore } from '../../stores/authStore';

export const apiClient = axios.create({
  baseURL: 'http://localhost:8000/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
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

// Optional: Intercept responses to handle global 401 Unauthorized errors
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    // Only redirect to login if the 401 isn't from the login endpoint itself
    const originalRequest = error.config;
    if (error.response?.status === 401 && originalRequest.url !== '/auth/login') {
      useAuthStore.getState().logout();
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);
