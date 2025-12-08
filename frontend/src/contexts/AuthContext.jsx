import { createContext, useContext, useState, useEffect } from 'react'
import api from '../services/api'
import toast from 'react-hot-toast'

const AuthContext = createContext()

export const useAuth = () => {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider')
  }
  return context
}

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const token = localStorage.getItem('token')
    if (token) {
      api.defaults.headers.common['Authorization'] = `Bearer ${token}`
      fetchUser()
    } else {
      setLoading(false)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const fetchUser = async () => {
    try {
      const response = await api.get('/api/auth/me')
      setUser(response.data)
    } catch (error) {
      console.error('Error fetching user:', error.response?.data || error.message)
      // If token expired, clear it and redirect to login
      if (error.response?.status === 401) {
        localStorage.removeItem('token')
        delete api.defaults.headers.common['Authorization']
        setUser(null)
        toast.error('Session expired. Please login again.')
      }
    } finally {
      setLoading(false)
    }
  }

  const login = async (email, password) => {
    try {
      const formData = new FormData()
      formData.append('username', email)
      formData.append('password', password)

      const response = await api.post('/api/auth/login', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })

      const { access_token } = response.data
      if (!access_token) {
        throw new Error('No access token received')
      }

      localStorage.setItem('token', access_token)
      api.defaults.headers.common['Authorization'] = `Bearer ${access_token}`

      // Fetch user info immediately after login
      try {
        const userResponse = await api.get('/api/auth/me')
        setUser(userResponse.data)
        toast.success('Login successful!')
        return true
      } catch (userError) {
        console.error('Error fetching user after login:', userError.response?.data || userError.message)
        // If user fetch fails, still allow login but show warning
        toast.error('Login successful but could not fetch user info')
        // Set a minimal user object so navigation can proceed
        setUser({ email, username: email.split('@')[0] })
        return true
      }
    } catch (error) {
      console.error('Login error:', error.response?.data || error.message)
      toast.error(error.response?.data?.detail || 'Login failed')
      throw error
    }
  }

  const signup = async (email, username, password) => {
    try {
      await api.post('/api/auth/signup', { email, username, password })
      toast.success('Account created! Please login.')
      return true
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Signup failed')
      throw error
    }
  }

  const logout = () => {
    localStorage.removeItem('token')
    delete api.defaults.headers.common['Authorization']
    setUser(null)
    toast.success('Logged out successfully')
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, signup, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

