import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import SessionSidebar from '../components/SessionSidebar'
import TestCaseTree from '../components/TestCaseTree'
import QuestionForm from '../components/QuestionForm'
import api from '../services/api'
import toast from 'react-hot-toast'
import { LogOut, Plus } from 'lucide-react'

const Dashboard = () => {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [sessions, setSessions] = useState([])
  const [currentSession, setCurrentSession] = useState(null)
  const [sessionState, setSessionState] = useState(null)
  const [loading, setLoading] = useState(false)
  const [loadingNode, setLoadingNode] = useState(null) // Track which node is loading: 'l1_index' or 'l2_index'
  const [showNewSessionModal, setShowNewSessionModal] = useState(false)
  const [newSessionPrompt, setNewSessionPrompt] = useState('')
  const [newSessionTitle, setNewSessionTitle] = useState('')

  useEffect(() => {
    fetchSessions()
  }, [])

  useEffect(() => {
    if (currentSession) {
      fetchSessionState(currentSession.id)
    }
  }, [currentSession])

  const fetchSessions = async () => {
    try {
      const response = await api.get('/api/sessions')
      setSessions(response.data)
    } catch (error) {
      toast.error('Failed to fetch sessions')
    }
  }

  const fetchSessionState = async (sessionId) => {
    try {
      const response = await api.get(`/api/sessions/${sessionId}/state`)
      setSessionState(response.data)
    } catch (error) {
      // Session might not have state yet
      setSessionState(null)
    }
  }

  const createNewSession = async () => {
    if (!newSessionPrompt.trim()) {
      toast.error('Please enter a business description')
      return
    }

    setLoading(true)
    try {
      const response = await api.post('/api/sessions', {
        title: newSessionTitle || 'New Session',
        user_prompt: newSessionPrompt
      })
      
      const newSession = response.data
      setSessions([newSession, ...sessions])
      setCurrentSession(newSession)
      setShowNewSessionModal(false)
      setNewSessionPrompt('')
      setNewSessionTitle('')
      
      // Start the session
      await startSession(newSession.id)
      toast.success('Session created!')
    } catch (error) {
      toast.error('Failed to create session')
    } finally {
      setLoading(false)
    }
  }

  const startSession = async (sessionId) => {
    try {
      const response = await api.post(`/api/sessions/${sessionId}/start`)
      setSessionState(response.data)
      await fetchSessions()
    } catch (error) {
      toast.error('Failed to start session')
    }
  }

  const deleteSession = async (sessionId) => {
    if (!confirm('Are you sure you want to delete this session?')) return

    try {
      await api.delete(`/api/sessions/${sessionId}`)
      setSessions(sessions.filter(s => s.id !== sessionId))
      if (currentSession?.id === sessionId) {
        setCurrentSession(null)
        setSessionState(null)
      }
      toast.success('Session deleted')
    } catch (error) {
      toast.error('Failed to delete session')
    }
  }

  const handleQuestionSubmit = async (level, answers) => {
    if (!currentSession) return

    setLoading(true)
    try {
      const response = await api.post(
        `/api/sessions/${currentSession.id}/${level}/answers`,
        { answers }
      )
      // Merge the new state with existing state to preserve expanded nodes
      setSessionState(response.data)
      await fetchSessions()
      toast.success('Answers submitted!')
    } catch (error) {
      toast.error('Failed to submit answers')
    } finally {
      setLoading(false)
    }
  }

  const handleCaseSelect = async (level, index) => {
    if (!currentSession) return

    // Set loading for specific node only
    setLoadingNode(`${level}_${index}`)
    try {
      const paramName = level === 'l1' ? 'l1_index' : 'l2_index'
      const response = await api.post(
        `/api/sessions/${currentSession.id}/${level}/select?${paramName}=${index}`
      )
      setSessionState(response.data)
      await fetchSessions()
      toast.success('Test case selected!')
    } catch (error) {
      console.error('Error selecting case:', error.response?.data || error.message)
      toast.error(error.response?.data?.detail || 'Failed to select test case')
    } finally {
      setLoadingNode(null)
    }
  }

  const getCurrentLevel = () => {
    if (!sessionState) return null
    
    // Show L1 questions if they exist and L1 test cases haven't been generated yet
    if (sessionState.l1_clarification_questions?.length > 0 && !sessionState.l1_test_cases?.length) {
      return 'l1_questions'
    }
    
    // Show L2 questions if they exist and answers haven't been submitted
    // (Once answers are submitted, L2 cases are generated immediately, so we check if answers exist)
    if (sessionState.l2_clarification_questions?.length > 0 && 
        Object.keys(sessionState.l2_clarification_answers || {}).length === 0) {
      return 'l2_questions'
    }
    
    // Show L3 questions if they exist and answers haven't been submitted
    // (Once answers are submitted, L3 cases are generated immediately, so we check if answers exist)
    if (sessionState.l3_clarification_questions?.length > 0 && 
        Object.keys(sessionState.l3_clarification_answers || {}).length === 0) {
      return 'l3_questions'
    }
    
    // Otherwise show the tree (users can select any node)
    return 'tree_view'
  }

  const currentLevel = getCurrentLevel()

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Sidebar */}
      <SessionSidebar
        sessions={sessions}
        currentSession={currentSession}
        onSelectSession={setCurrentSession}
        onDeleteSession={deleteSession}
        onCreateNew={() => setShowNewSessionModal(true)}
      />

      {/* Main Content */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <header className="bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-800">Test Case Generator</h1>
            <p className="text-sm text-gray-500">Welcome, {user?.username}</p>
          </div>
          <button
            onClick={() => {
              logout()
              navigate('/login')
            }}
            className="flex items-center gap-2 px-4 py-2 text-gray-700 hover:bg-gray-100 rounded-lg transition"
          >
            <LogOut size={20} />
            Logout
          </button>
        </header>

        {/* Content Area */}
        <div className="flex-1 overflow-auto p-6">
          {!currentSession ? (
            <div className="flex items-center justify-center h-full">
              <div className="text-center">
                <h2 className="text-2xl font-semibold text-gray-700 mb-4">
                  No session selected
                </h2>
                <p className="text-gray-500 mb-6">
                  Create a new session or select one from the sidebar
                </p>
                <button
                  onClick={() => setShowNewSessionModal(true)}
                  className="flex items-center gap-2 px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition mx-auto"
                >
                  <Plus size={20} />
                  Create New Session
                </button>
              </div>
            </div>
          ) : !sessionState ? (
            <div className="flex items-center justify-center h-full">
              <div className="text-center">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
                <p className="text-gray-500">Starting session...</p>
                <button
                  onClick={() => startSession(currentSession.id)}
                  className="mt-4 px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
                >
                  Start Session
                </button>
              </div>
            </div>
          ) : (
            <div className="space-y-6">
              {/* Session Info */}
              <div className="bg-white rounded-lg shadow p-4">
                <h2 className="text-lg font-semibold text-gray-800 mb-2">
                  {currentSession.title}
                </h2>
                <p className="text-sm text-gray-600">{currentSession.user_prompt}</p>
              </div>

              {/* Questions Form - Show when questions are available */}
              {currentLevel === 'l1_questions' && (
                <QuestionForm
                  questions={sessionState.l1_clarification_questions || []}
                  onSubmit={(answers) => handleQuestionSubmit('l1', answers)}
                  loading={loading}
                />
              )}

              {currentLevel === 'l2_questions' && (
                <QuestionForm
                  questions={sessionState.l2_clarification_questions || []}
                  onSubmit={(answers) => handleQuestionSubmit('l2', answers)}
                  loading={loading}
                />
              )}

              {currentLevel === 'l3_questions' && (
                <QuestionForm
                  questions={sessionState.l3_clarification_questions || []}
                  onSubmit={(answers) => handleQuestionSubmit('l3', answers)}
                  loading={loading}
                />
              )}

              {/* Test Case Tree - Always show when L1 cases exist */}
              {sessionState.l1_test_cases?.length > 0 && (
                <TestCaseTree
                  sessionState={sessionState}
                  onSelectCase={handleCaseSelect}
                  loading={loading}
                  loadingNode={loadingNode}
                />
              )}
            </div>
          )}
        </div>
      </div>

      {/* New Session Modal */}
      {showNewSessionModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 w-full max-w-2xl">
            <h2 className="text-2xl font-bold mb-4">Create New Session</h2>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Session Title (optional)
                </label>
                <input
                  type="text"
                  value={newSessionTitle}
                  onChange={(e) => setNewSessionTitle(e.target.value)}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  placeholder="My Test Case Session"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Business Description *
                </label>
                <textarea
                  value={newSessionPrompt}
                  onChange={(e) => setNewSessionPrompt(e.target.value)}
                  rows={6}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  placeholder="Describe your business, software systems, workflows, etc..."
                  required
                />
              </div>
            </div>
            <div className="flex gap-4 mt-6">
              <button
                onClick={createNewSession}
                disabled={loading}
                className="flex-1 bg-blue-600 text-white py-2 rounded-lg hover:bg-blue-700 transition disabled:opacity-50"
              >
                {loading ? 'Creating...' : 'Create Session'}
              </button>
              <button
                onClick={() => {
                  setShowNewSessionModal(false)
                  setNewSessionPrompt('')
                  setNewSessionTitle('')
                }}
                className="flex-1 bg-gray-200 text-gray-700 py-2 rounded-lg hover:bg-gray-300 transition"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default Dashboard

