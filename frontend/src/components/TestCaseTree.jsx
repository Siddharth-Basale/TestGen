import { useState, useEffect, memo } from 'react'
import { ChevronRight, ChevronDown, Circle, Image, Loader2 } from 'lucide-react'
import { generatePlantUMLDiagram, getSessionDiagrams } from '../services/api'
import toast from 'react-hot-toast'
import PlantUMLDiagramModal from './PlantUMLDiagramModal'

const TestCaseTree = ({ sessionState, onSelectCase, loading, loadingNode, sessionId }) => {
  const [expandedNodes, setExpandedNodes] = useState(new Set())
  const [selectedNode, setSelectedNode] = useState(null)
  const [generatingDiagram, setGeneratingDiagram] = useState(null) // Track which diagram is generating: 'l1_id' or 'l2_id'
  const [diagrams, setDiagrams] = useState({}) // Store diagram IDs: { 'l1_id': diagramId, 'l2_id': diagramId }
  const [modalOpen, setModalOpen] = useState(false)
  const [currentDiagramId, setCurrentDiagramId] = useState(null)
  const [currentDiagramType, setCurrentDiagramType] = useState(null)
  const [currentTestCaseId, setCurrentTestCaseId] = useState(null)
  
  // Preserve expanded state across re-renders by using a ref-like approach
  // The Set in useState already preserves state, so we're good there

  const toggleNode = (nodeId) => {
    const newExpanded = new Set(expandedNodes)
    if (newExpanded.has(nodeId)) {
      newExpanded.delete(nodeId)
    } else {
      newExpanded.add(nodeId)
    }
    setExpandedNodes(newExpanded)
  }

  // Load diagrams when session changes
  useEffect(() => {
    if (sessionId) {
      loadDiagrams()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId, sessionState?.l3_test_cases])

  const loadDiagrams = async () => {
    if (!sessionId) return
    try {
      const response = await getSessionDiagrams(sessionId)
      const diagramsMap = {}
      response.data.forEach(diagram => {
        diagramsMap[diagram.test_case_id] = diagram.id
      })
      setDiagrams(diagramsMap)
    } catch (error) {
      console.error('Error loading diagrams:', error)
    }
  }

  // Check if L1 case has all L2 cases with L3 cases
  const l1HasAllL2WithL3 = (l1Case) => {
    const l2Cases = sessionState.l2_test_cases?.filter(l2 => l2.parent_l1_id === l1Case.id) || []
    if (l2Cases.length === 0) return false
    
    // Check if all L2 cases have at least one L3 case
    return l2Cases.every(l2 => {
      const l3Count = sessionState.l3_test_cases?.filter(l3 => l3.parent_l2_id === l2.id).length || 0
      return l3Count > 0
    })
  }

  // Check if L2 case has L3 cases
  const l2HasL3 = (l2Case) => {
    const l3Count = sessionState.l3_test_cases?.filter(l3 => l3.parent_l2_id === l2Case.id).length || 0
    return l3Count > 0
  }

  const handleGenerateDiagram = async (testCaseId, testCaseTitle, diagramType) => {
    if (!sessionId) {
      toast.error('Session not found')
      return
    }

    setGeneratingDiagram(testCaseId)
    try {
      const response = await generatePlantUMLDiagram(
        sessionId,
        testCaseId,
        diagramType,
        testCaseTitle
      )
      
      const diagramId = response.data.id
      setDiagrams(prev => ({ ...prev, [testCaseId]: diagramId }))
      toast.success('Diagram generated successfully!')
      
      // Open modal to show the diagram
      setCurrentDiagramId(diagramId)
      setCurrentDiagramType(diagramType)
      setCurrentTestCaseId(testCaseId)
      setModalOpen(true)
    } catch (error) {
      console.error('Error generating diagram:', error)
      toast.error(error.response?.data?.detail || 'Failed to generate diagram')
    } finally {
      setGeneratingDiagram(null)
    }
  }

  const handleViewDiagram = (testCaseId) => {
    const diagramId = diagrams[testCaseId]
    if (diagramId) {
      setCurrentDiagramId(diagramId)
      setCurrentDiagramType(sessionState.l1_test_cases?.some(l1 => l1.id === testCaseId) ? 'l1' : 'l2')
      setCurrentTestCaseId(testCaseId)
      setModalOpen(true)
    }
  }

  if (!sessionState) {
    return null
  }

  const l1Cases = sessionState.l1_test_cases || []
  const treeData = sessionState.full_tree_data

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h3 className="text-lg font-semibold text-gray-800 mb-4">Test Case Tree</h3>
      
      {/* Never show global loading when a specific node is loading */}
      {loading && !loadingNode && l1Cases.length === 0 && (
        <div className="flex items-center justify-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        </div>
      )}

      {!loading && !loadingNode && l1Cases.length === 0 && (
        <div className="text-center text-gray-500 py-8">
          No test cases generated yet. Answer the questions above to generate test cases.
        </div>
      )}

      {/* Always show tree when L1 cases exist, even if loading (we show loading on specific nodes) */}
      {l1Cases.length > 0 && (
        <div className="space-y-2">
          {/* Root Node - User Prompt */}
          <div className="mb-4 p-4 bg-indigo-50 rounded-lg border-2 border-indigo-200">
            <div className="flex items-center gap-2">
              <Circle size={14} className="text-indigo-600" fill="currentColor" />
              <div>
                <div className="font-semibold text-indigo-900">Root: Business Description</div>
                <div className="text-sm text-indigo-700 mt-1">{sessionState.user_initial_prompt}</div>
              </div>
            </div>
          </div>

          {/* L1 Nodes */}
          <div className="space-y-2">
            {l1Cases.map((l1Case, index) => {
              const nodeId = `l1_${index}`
              const isExpanded = expandedNodes.has(nodeId)
              const isSelected = selectedNode === nodeId
              const isLoading = loadingNode === `l1_${index}`
              const hasL2 = sessionState.l2_test_cases?.some(
                l2 => l2.parent_l1_id === l1Case.id
              )

              return (
                <div key={l1Case.id} className="mb-2">
                  <div
                    className={`flex items-center gap-2 p-3 rounded-lg cursor-pointer transition relative ${
                      isSelected
                        ? 'bg-blue-100 border-2 border-blue-500'
                        : 'bg-gray-50 hover:bg-gray-100 border-2 border-transparent'
                    } ${!hasL2 ? 'hover:shadow-md' : ''} ${isLoading ? 'opacity-75' : ''}`}
                    onClick={() => {
                      if (!hasL2 && !isLoading) {
                        setSelectedNode(`l1_${index}`)
                        onSelectCase('l1', index)
                      } else if (!isLoading) {
                        toggleNode(nodeId)
                      }
                    }}
                  >
                    {hasL2 && !isLoading && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          toggleNode(nodeId)
                        }}
                        className="p-1 hover:bg-gray-200 rounded"
                      >
                        {isExpanded ? (
                          <ChevronDown size={16} className="text-gray-600" />
                        ) : (
                          <ChevronRight size={16} className="text-gray-600" />
                        )}
                      </button>
                    )}
                    {isLoading && (
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
                    )}
                    {!isLoading && <Circle size={12} className="text-blue-600" fill="currentColor" />}
                    <div className="flex-1">
                      <div className="font-semibold text-gray-800">{l1Case.title}</div>
                      <div className="text-xs text-gray-500">{l1Case.description}</div>
                    </div>
                    {!hasL2 && !isLoading && (
                      <span className="text-xs bg-blue-100 text-blue-700 px-2 py-1 rounded">
                        Click to explore
                      </span>
                    )}
                    {hasL2 && !isLoading && (
                      <span className="text-xs bg-green-100 text-green-700 px-2 py-1 rounded">
                        {sessionState.l2_test_cases?.filter(l2 => l2.parent_l1_id === l1Case.id).length || 0} L2 cases
                      </span>
                    )}
                    {isLoading && (
                      <span className="text-xs bg-blue-100 text-blue-700 px-2 py-1 rounded">
                        Generating...
                      </span>
                    )}
                    {/* Generate Diagram Button for L1 */}
                    {!isLoading && l1HasAllL2WithL3(l1Case) && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          if (diagrams[l1Case.id]) {
                            handleViewDiagram(l1Case.id)
                          } else {
                            handleGenerateDiagram(l1Case.id, l1Case.title, 'l1')
                          }
                        }}
                        disabled={generatingDiagram === l1Case.id}
                        className="ml-2 px-3 py-1.5 text-xs bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1.5 transition"
                        title={diagrams[l1Case.id] ? 'View Diagram' : 'Generate Diagram'}
                      >
                        {generatingDiagram === l1Case.id ? (
                          <>
                            <Loader2 size={14} className="animate-spin" />
                            <span>Generating...</span>
                          </>
                        ) : diagrams[l1Case.id] ? (
                          <>
                            <Image size={14} />
                            <span>View Diagram</span>
                          </>
                        ) : (
                          <>
                            <Image size={14} />
                            <span>Generate Diagram</span>
                          </>
                        )}
                      </button>
                    )}
                  </div>

                  {/* L2 Children */}
                  {isExpanded && hasL2 && (
                    <div className="ml-6 mt-2 space-y-2">
                      {sessionState.l2_test_cases
                        ?.filter(l2 => l2.parent_l1_id === l1Case.id)
                        .map((l2Case) => {
                          const actualIndex = sessionState.l2_test_cases.findIndex(l2 => l2.id === l2Case.id)
                          const l2NodeId = `l2_${actualIndex}_${l1Case.id}`
                          const isL2Expanded = expandedNodes.has(l2NodeId)
                          const isL2Selected = selectedNode === l2NodeId
                          const isL2Loading = loadingNode === `l2_${actualIndex}`
                          const hasL3 = sessionState.l3_test_cases?.some(
                            l3 => l3.parent_l2_id === l2Case.id
                          )

                          return (
                            <div key={l2Case.id} className="mb-2">
                              <div
                                className={`flex items-center gap-2 p-3 rounded-lg cursor-pointer transition relative ${
                                  isL2Selected
                                    ? 'bg-green-100 border-2 border-green-500'
                                    : 'bg-gray-50 hover:bg-gray-100 border-2 border-transparent'
                                } ${!hasL3 ? 'hover:shadow-md' : ''} ${isL2Loading ? 'opacity-75' : ''}`}
                                onClick={() => {
                                  if (!hasL3 && !isL2Loading) {
                                    setSelectedNode(l2NodeId)
                                    onSelectCase('l2', actualIndex)
                                  } else if (!isL2Loading) {
                                    toggleNode(l2NodeId)
                                  }
                                }}
                              >
                                {hasL3 && !isL2Loading && (
                                  <button
                                    onClick={(e) => {
                                      e.stopPropagation()
                                      toggleNode(l2NodeId)
                                    }}
                                    className="p-1 hover:bg-gray-200 rounded"
                                  >
                                    {isL2Expanded ? (
                                      <ChevronDown size={16} className="text-gray-600" />
                                    ) : (
                                      <ChevronRight size={16} className="text-gray-600" />
                                    )}
                                  </button>
                                )}
                                {isL2Loading && (
                                  <div className="animate-spin rounded-full h-3 w-3 border-b-2 border-green-600"></div>
                                )}
                                {!isL2Loading && <Circle size={10} className="text-green-600" fill="currentColor" />}
                                <div className="flex-1">
                                  <div className="font-medium text-gray-800">{l2Case.title}</div>
                                  <div className="text-xs text-gray-500">{l2Case.description}</div>
                                </div>
                                {!hasL3 && !isL2Loading && (
                                  <span className="text-xs bg-green-100 text-green-700 px-2 py-1 rounded">
                                    Click to explore
                                  </span>
                                )}
                                {hasL3 && !isL2Loading && (
                                  <span className="text-xs bg-purple-100 text-purple-700 px-2 py-1 rounded">
                                    {sessionState.l3_test_cases?.filter(l3 => l3.parent_l2_id === l2Case.id).length || 0} L3 cases
                                  </span>
                                )}
                                {isL2Loading && (
                                  <span className="text-xs bg-green-100 text-green-700 px-2 py-1 rounded">
                                    Generating...
                                  </span>
                                )}
                                {/* Generate Diagram Button for L2 */}
                                {!isL2Loading && l2HasL3(l2Case) && (
                                  <button
                                    onClick={(e) => {
                                      e.stopPropagation()
                                      if (diagrams[l2Case.id]) {
                                        handleViewDiagram(l2Case.id)
                                      } else {
                                        handleGenerateDiagram(l2Case.id, l2Case.title, 'l2')
                                      }
                                    }}
                                    disabled={generatingDiagram === l2Case.id}
                                    className="ml-2 px-3 py-1.5 text-xs bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1.5 transition"
                                    title={diagrams[l2Case.id] ? 'View Diagram' : 'Generate Diagram'}
                                  >
                                    {generatingDiagram === l2Case.id ? (
                                      <>
                                        <Loader2 size={14} className="animate-spin" />
                                        <span>Generating...</span>
                                      </>
                                    ) : diagrams[l2Case.id] ? (
                                      <>
                                        <Image size={14} />
                                        <span>View</span>
                                      </>
                                    ) : (
                                      <>
                                        <Image size={14} />
                                        <span>Generate</span>
                                      </>
                                    )}
                                  </button>
                                )}
                              </div>

                              {/* L3 Children */}
                              {isL2Expanded && hasL3 && (
                                <div className="ml-6 mt-2 space-y-2">
                                  {sessionState.l3_test_cases
                                    ?.filter(l3 => l3.parent_l2_id === l2Case.id)
                                    .map((l3Case, l3Index) => (
                                      <div
                                        key={l3Case.id}
                                        className="p-3 bg-purple-50 rounded-lg border border-purple-200"
                                      >
                                        <div className="flex items-start gap-2">
                                          <Circle size={8} className="text-purple-600 mt-1" fill="currentColor" />
                                          <div className="flex-1">
                                            <div className="font-medium text-gray-800">{l3Case.title}</div>
                                            <div className="text-xs text-gray-600 mt-1">{l3Case.description}</div>
                                            {l3Case.test_steps && l3Case.test_steps.length > 0 && (
                                              <div className="mt-2">
                                                <div className="text-xs font-semibold text-gray-700">Test Steps:</div>
                                                <ol className="text-xs text-gray-600 list-decimal list-inside mt-1">
                                                  {l3Case.test_steps.map((step, i) => (
                                                    <li key={i}>{step}</li>
                                                  ))}
                                                </ol>
                                              </div>
                                            )}
                                            {l3Case.expected_result && (
                                              <div className="mt-2">
                                                <div className="text-xs font-semibold text-gray-700">Expected Result:</div>
                                                <div className="text-xs text-gray-600 mt-1">{l3Case.expected_result}</div>
                                              </div>
                                            )}
                                          </div>
                                        </div>
                                      </div>
                                    ))}
                                </div>
                              )}
                            </div>
                          )
                        })}
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* PlantUML Diagram Modal */}
      <PlantUMLDiagramModal
        isOpen={modalOpen}
        onClose={() => {
          setModalOpen(false)
          setCurrentDiagramId(null)
          setCurrentDiagramType(null)
          setCurrentTestCaseId(null)
        }}
        diagramId={currentDiagramId}
        sessionId={sessionId}
        testCaseId={currentTestCaseId}
        diagramType={currentDiagramType}
        onEdit={() => {
          // Reload diagrams after edit
          loadDiagrams()
        }}
      />
    </div>
  )
}

// Memoize component to prevent unnecessary re-renders
// Only re-render when loadingNode changes or when test cases/questions actually change
export default memo(TestCaseTree, (prevProps, nextProps) => {
  // Always re-render if loadingNode changes (to show/hide loading spinner on specific node)
  if (prevProps.loadingNode !== nextProps.loadingNode) return false
  
  // Always re-render if global loading changes
  if (prevProps.loading !== nextProps.loading) return false
  
  // Re-render if test cases count changed (new cases added)
  const prevL1Count = prevProps.sessionState?.l1_test_cases?.length || 0
  const nextL1Count = nextProps.sessionState?.l1_test_cases?.length || 0
  if (prevL1Count !== nextL1Count) return false
  
  const prevL2Count = prevProps.sessionState?.l2_test_cases?.length || 0
  const nextL2Count = nextProps.sessionState?.l2_test_cases?.length || 0
  if (prevL2Count !== nextL2Count) return false
  
  const prevL3Count = prevProps.sessionState?.l3_test_cases?.length || 0
  const nextL3Count = nextProps.sessionState?.l3_test_cases?.length || 0
  if (prevL3Count !== nextL3Count) return false
  
  // Re-render if questions changed (to show question form)
  const prevL2QCount = prevProps.sessionState?.l2_clarification_questions?.length || 0
  const nextL2QCount = nextProps.sessionState?.l2_clarification_questions?.length || 0
  if (prevL2QCount !== nextL2QCount) return false
  
  const prevL3QCount = prevProps.sessionState?.l3_clarification_questions?.length || 0
  const nextL3QCount = nextProps.sessionState?.l3_clarification_questions?.length || 0
  if (prevL3QCount !== nextL3QCount) return false
  
  // If counts are the same, don't re-render (data hasn't meaningfully changed)
  // This prevents re-renders when sessionState object reference changes but data is identical
  return true
})

