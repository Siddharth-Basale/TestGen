import { useState, useEffect } from 'react'
import { X, Download, Edit2, Loader2 } from 'lucide-react'
import api from '../services/api'
import toast from 'react-hot-toast'

const PlantUMLDiagramModal = ({ isOpen, onClose, diagramId, sessionId, testCaseId, diagramType, onEdit }) => {
  const [imageUrl, setImageUrl] = useState(null)
  const [loading, setLoading] = useState(false)
  const [editMode, setEditMode] = useState(false)
  const [editPrompt, setEditPrompt] = useState('')
  const [editing, setEditing] = useState(false)

  useEffect(() => {
    if (isOpen && diagramId) {
      loadImage()
    } else {
      setImageUrl(null)
      setEditMode(false)
      setEditPrompt('')
    }
    
    // Cleanup function - revoke object URL when component unmounts or diagramId changes
    return () => {
      if (imageUrl) {
        URL.revokeObjectURL(imageUrl)
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen, diagramId])

  const loadImage = async () => {
    if (!diagramId) return
    
    setLoading(true)
    try {
      const token = localStorage.getItem('token')
      const response = await fetch(`http://localhost:8000/api/plantuml/${diagramId}/image`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })
      
      if (response.ok) {
        const blob = await response.blob()
        const url = URL.createObjectURL(blob)
        setImageUrl(url)
      } else {
        toast.error('Failed to load diagram image')
      }
    } catch (error) {
      console.error('Error loading image:', error)
      toast.error('Failed to load diagram image')
    } finally {
      setLoading(false)
    }
  }

  const handleEdit = async () => {
    if (!editPrompt.trim()) {
      toast.error('Please enter edit instructions')
      return
    }

    setEditing(true)
    try {
      const response = await api.post(`/api/plantuml/${diagramId}/edit`, {
        edit_prompt: editPrompt,
        diagram_type: 'activity'
      })

      toast.success('Diagram updated successfully!')
      setEditMode(false)
      setEditPrompt('')
      // Reload image
      loadImage()
      if (onEdit) onEdit(response.data)
    } catch (error) {
      console.error('Error editing diagram:', error)
      toast.error(error.response?.data?.detail || 'Failed to edit diagram')
    } finally {
      setEditing(false)
    }
  }

  const handleDownload = () => {
    if (imageUrl) {
      const link = document.createElement('a')
      link.href = imageUrl
      link.download = `diagram_${diagramId}.png`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      toast.success('Diagram downloaded')
    }
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-6xl w-full max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b">
          <h2 className="text-xl font-semibold text-gray-800">
            {editMode ? 'Edit PlantUML Diagram' : 'PlantUML Diagram'}
          </h2>
          <div className="flex items-center gap-2">
            {!editMode && imageUrl && (
              <>
                <button
                  onClick={handleDownload}
                  className="p-2 hover:bg-gray-100 rounded-lg transition"
                  title="Download"
                >
                  <Download size={20} className="text-gray-600" />
                </button>
                <button
                  onClick={() => setEditMode(true)}
                  className="p-2 hover:bg-gray-100 rounded-lg transition"
                  title="Edit"
                >
                  <Edit2 size={20} className="text-gray-600" />
                </button>
              </>
            )}
            <button
              onClick={onClose}
              className="p-2 hover:bg-gray-100 rounded-lg transition"
            >
              <X size={20} className="text-gray-600" />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-auto p-4">
          {editMode ? (
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Edit Instructions
                </label>
                <textarea
                  value={editPrompt}
                  onChange={(e) => setEditPrompt(e.target.value)}
                  placeholder="Describe how you want to modify the diagram (e.g., 'Add a new step after step 3', 'Change the color of the start node to blue', 'Add a decision point for error handling')"
                  className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  rows={6}
                />
              </div>
              <div className="flex gap-2">
                <button
                  onClick={handleEdit}
                  disabled={editing || !editPrompt.trim()}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                >
                  {editing && <Loader2 size={16} className="animate-spin" />}
                  Apply Changes
                </button>
                <button
                  onClick={() => {
                    setEditMode(false)
                    setEditPrompt('')
                  }}
                  className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300"
                >
                  Cancel
                </button>
              </div>
            </div>
          ) : (
            <div className="flex items-center justify-center min-h-[400px]">
              {loading ? (
                <div className="flex flex-col items-center gap-2">
                  <Loader2 size={32} className="animate-spin text-blue-600" />
                  <p className="text-gray-600">Loading diagram...</p>
                </div>
              ) : imageUrl ? (
                <img
                  src={imageUrl}
                  alt="PlantUML Diagram"
                  className="max-w-full max-h-full object-contain"
                />
              ) : (
                <p className="text-gray-500">No diagram available</p>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default PlantUMLDiagramModal

