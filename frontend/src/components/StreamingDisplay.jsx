import { useState, useEffect, useRef } from 'react'

const StreamingDisplay = ({ streamUrl, onComplete, onError, className = '' }) => {
  const [streamingText, setStreamingText] = useState('')
  const [isStreaming, setIsStreaming] = useState(false)
  const abortControllerRef = useRef(null)

  useEffect(() => {
    if (!streamUrl) return

    setIsStreaming(true)
    setStreamingText('')
    abortControllerRef.current = new AbortController()

    const eventSource = new EventSource(streamUrl)
    
    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        
        if (data.type === 'token') {
          setStreamingText(data.full_text || '')
        } else if (data.type === 'complete') {
          setIsStreaming(false)
          eventSource.close()
          if (onComplete) {
            onComplete(data.state || data)
          }
        } else if (data.type === 'error') {
          setIsStreaming(false)
          eventSource.close()
          if (onError) {
            onError(data.error || 'An error occurred')
          }
        }
      } catch (error) {
        console.error('Error parsing SSE data:', error)
      }
    }

    eventSource.onerror = (error) => {
      console.error('SSE error:', error)
      setIsStreaming(false)
      eventSource.close()
      if (onError) {
        onError('Stream connection error')
      }
    }

    return () => {
      eventSource.close()
      if (abortControllerRef.current) {
        abortControllerRef.current.abort()
      }
    }
  }, [streamUrl, onComplete, onError])

  if (!streamUrl) return null

  return (
    <div className={`${className}`}>
      {isStreaming && (
        <div className="flex items-center gap-2 text-sm text-gray-600 mb-2">
          <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
          <span>Generating...</span>
        </div>
      )}
      {streamingText && (
        <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 max-h-64 overflow-y-auto">
          <pre className="text-sm text-gray-700 whitespace-pre-wrap font-mono">
            {streamingText}
          </pre>
        </div>
      )}
    </div>
  )
}

export default StreamingDisplay

