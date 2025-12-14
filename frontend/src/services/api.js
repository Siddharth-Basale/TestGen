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

// Streaming helper function
export const streamRequest = async (url, options = {}) => {
  const token = localStorage.getItem('token')
  const headers = {
    'Content-Type': 'application/json',
    ...options.headers,
  }
  
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }
  
  const response = await fetch(`${api.defaults.baseURL}${url}`, {
    method: options.method || 'POST',
    headers,
    body: options.body ? JSON.stringify(options.body) : undefined,
  })
  
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Request failed' }))
    throw new Error(error.detail || 'Request failed')
  }
  
  return response
}

// PlantUML API functions
export const generatePlantUMLDiagram = async (sessionId, testCaseId, diagramType, testCaseTitle) => {
  return api.post(`/api/sessions/${sessionId}/plantuml/generate`, {
    session_id: sessionId,
    test_case_id: testCaseId,
    diagram_type: diagramType,
    test_case_title: testCaseTitle
  })
}

export const getSessionDiagrams = async (sessionId) => {
  return api.get(`/api/sessions/${sessionId}/plantuml`)
}

export const editPlantUMLDiagram = async (diagramId, editPrompt, diagramType = 'activity') => {
  return api.post(`/api/plantuml/${diagramId}/edit`, {
    edit_prompt: editPrompt,
    diagram_type: diagramType
  })
}

export default api

