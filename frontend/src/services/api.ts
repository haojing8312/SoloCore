/**
 * Axios instance configuration and interceptors
 */

import axios, { type AxiosError, type AxiosResponse, type InternalAxiosRequestConfig } from 'axios';
import { API_CONFIG } from '@/utils/constants';
import { getUserFriendlyErrorMessage } from '@/utils/errorMessages';

/**
 * Create Axios instance with default configuration
 */
const api = axios.create({
  baseURL: API_CONFIG.BASE_URL,
  timeout: API_CONFIG.TIMEOUT,
  headers: {
    'Content-Type': 'application/json',
  },
});

/**
 * Request interceptor - Add common headers
 */
api.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    // Add any common headers here (e.g., Authorization token)
    // const token = localStorage.getItem('token');
    // if (token) {
    //   config.headers.Authorization = `Bearer ${token}`;
    // }

    return config;
  },
  (error: AxiosError) => {
    return Promise.reject(error);
  }
);

/**
 * Response interceptor - Handle common errors
 */
api.interceptors.response.use(
  (response: AxiosResponse) => {
    return response;
  },
  (error: AxiosError) => {
    // Enhance error with user-friendly message
    if (error.response) {
      const status = error.response.status;
      const data = error.response.data as { code?: string; message?: string };

      // Get user-friendly message
      const friendlyMessage = getUserFriendlyErrorMessage({
        code: data?.code,
        status,
        message: data?.message,
      });

      // Create enhanced error
      const enhancedError = new Error(friendlyMessage);
      (enhancedError as unknown as { originalError: AxiosError }).originalError = error;
      (enhancedError as unknown as { status: number }).status = status;
      (enhancedError as unknown as { code?: string }).code = data?.code;

      // Handle specific status codes
      if (status === 401) {
        // Unauthorized - clear auth and redirect to login
        localStorage.removeItem('auth_token');
        // Only redirect if not already on login page
        if (!window.location.pathname.includes('/login')) {
          window.location.href = '/login';
        }
      }

      return Promise.reject(enhancedError);
    } else if (error.request) {
      // Network error
      const networkError = new Error(getUserFriendlyErrorMessage('NETWORK_ERROR'));
      (networkError as unknown as { originalError: AxiosError }).originalError = error;
      return Promise.reject(networkError);
    }

    return Promise.reject(error);
  }
);

export default api;
