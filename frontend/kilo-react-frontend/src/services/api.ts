import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || '/api';

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add auth token if available
api.interceptors.request.use((config) => {
  let token = localStorage.getItem('admin_token');
  if (!token) {
    token = 'kilo-secure-admin-2024';
    localStorage.setItem('admin_token', token);
  }
  config.headers['X-Admin-Token'] = token;
  return config;
});

// Unified Agent client — hits /agent/ which nginx proxies to port 9200
export const agentApi = axios.create({
  baseURL: '/agent',
  headers: { 'Content-Type': 'application/json' },
});

export default api;
