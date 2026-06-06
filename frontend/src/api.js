// src/api.js
const BASE_URL = "/api"; // Proxy handles the http://localhost:5000 part

export const apiFetch = async (url, options = {}) => {
  const token = localStorage.getItem("token");
  
  const defaultOptions = {
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    ...options,
  };

  const response = await fetch(BASE_URL + url, defaultOptions);
  
  if (response.status === 401) {
    localStorage.removeItem("token");
    window.location.href = "/login";
  }

  return response.json();
};
