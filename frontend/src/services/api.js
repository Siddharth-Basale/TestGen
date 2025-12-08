import axios from 'axios'

const api = axios.create({
  baseURL: 'http://localhost:8000',
  headers: {
    'Content-Type': 'application/json',
  },
})

// Add token to requests if available
const token = localStorage.getItem('token')
if (token) {
  api.defaults.headers.common['Authorization'] = `Bearer ${token}`
}

// Add response interceptor to handle token expiration
api.interceptors.response.use(
  (response) => response,
  (error) => {
    // If token expired (401), clear it and redirect to login
    if (error.response?.status === 401) {
      const errorMessage = error.response?.data?.detail || error.message
      if (errorMessage.includes('expired') || errorMessage.includes('Invalid token')) {
        localStorage.removeItem('token')
        delete api.defaults.headers.common['Authorization']
        // Only redirect if we're not already on the login page
        if (window.location.pathname !== '/login' && window.location.pathname !== '/signup') {
          window.location.href = '/login'
        }
      }
    }
    return Promise.reject(error)
  }
)

export default api

