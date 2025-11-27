/**
 * Axios instance configuration and interceptors
 */

import axios, { type AxiosError, type AxiosResponse, type InternalAxiosRequestConfig } from 'axios';
import { API_CONFIG } from '@/utils/constants';

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
    // Handle common error scenarios
    if (error.response) {
      // Server responded with error status
      const status = error.response.status;

      switch (status) {
        case 401:
          // Unauthorized - redirect to login or show error
          console.error('未授权访问,请先登录');
          break;

        case 403:
          // Forbidden
          console.error('没有权限访问此资源');
          break;

        case 404:
          // Not found
          console.error('请求的资源不存在');
          break;

        case 500:
        case 502:
        case 503:
        case 504:
          // Server errors
          console.error('服务器错误,请稍后重试');
          break;

        default:
          console.error(`请求失败: ${status}`);
      }
    } else if (error.request) {
      // Request was made but no response received
      console.error('网络连接失败,请检查网络后重试');
    } else {
      // Something else happened
      console.error('请求配置错误:', error.message);
    }

    return Promise.reject(error);
  }
);

export default api;
