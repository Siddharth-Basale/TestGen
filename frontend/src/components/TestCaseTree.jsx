import { useState, memo } from 'react'
import { ChevronRight, ChevronDown, Circle } from 'lucide-react'

const TestCaseTree = ({ sessionState, onSelectCase, loading, loadingNode }) => {
  const [expandedNodes, setExpandedNodes] = useState(new Set())
  const [selectedNode, setSelectedNode] = useState(null)
  
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

