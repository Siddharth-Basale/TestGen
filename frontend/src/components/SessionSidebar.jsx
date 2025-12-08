import { Plus, Trash2, Clock } from 'lucide-react'

const SessionSidebar = ({ sessions, currentSession, onSelectSession, onDeleteSession, onCreateNew }) => {
  const formatDate = (dateString) => {
    const date = new Date(dateString)
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
  }

  return (
    <div className="w-64 bg-white border-r border-gray-200 flex flex-col">
      {/* Header */}
      <div className="p-4 border-b border-gray-200">
        <button
          onClick={onCreateNew}
          className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
        >
          <Plus size={20} />
          New Session
        </button>
      </div>

      {/* Sessions List */}
      <div className="flex-1 overflow-y-auto">
        <div className="p-2">
          <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide px-2 py-2">
            Recent Sessions
          </h3>
          {sessions.length === 0 ? (
            <div className="text-center text-gray-500 text-sm py-8">
              No sessions yet
            </div>
          ) : (
            <div className="space-y-1">
              {sessions.map((session) => (
                <div
                  key={session.id}
                  className={`group relative p-3 rounded-lg cursor-pointer transition ${
                    currentSession?.id === session.id
                      ? 'bg-blue-50 border border-blue-200'
                      : 'hover:bg-gray-50'
                  }`}
                  onClick={() => onSelectSession(session)}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1 min-w-0">
                      <h4 className="text-sm font-medium text-gray-800 truncate">
                        {session.title}
                      </h4>
                      <div className="flex items-center gap-2 mt-1">
                        <Clock size={12} className="text-gray-400" />
                        <span className="text-xs text-gray-500">
                          {formatDate(session.created_at)}
                        </span>
                      </div>
                    </div>
                    <button
                      onClick={(e) => {
                        e.stopPropagation()
                        onDeleteSession(session.id)
                      }}
                      className="opacity-0 group-hover:opacity-100 p-1 hover:bg-red-100 rounded transition"
                    >
                      <Trash2 size={14} className="text-red-500" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default SessionSidebar

