import { useState } from 'react'
import { Send, X } from 'lucide-react'

const QuestionForm = ({ questions, onSubmit, loading }) => {
  const [answers, setAnswers] = useState({})
  const [otherInputs, setOtherInputs] = useState({})

  // Helper to get question text (handles both old string format and new object format)
  const getQuestionText = (question) => {
    if (typeof question === 'string') return question
    return question.question || question
  }

  // Helper to get suggested answers
  const getSuggestedAnswers = (question) => {
    if (typeof question === 'string') return []
    return question.suggested_answers || []
  }

  // Handle selecting/deselecting a suggested answer
  const handleAnswerToggle = (questionText, answer) => {
    const currentAnswers = answers[questionText] || []
    const isSelected = Array.isArray(currentAnswers)
      ? currentAnswers.includes(answer)
      : currentAnswers === answer

    if (isSelected) {
      // Remove answer
      const newAnswers = Array.isArray(currentAnswers)
        ? currentAnswers.filter(a => a !== answer)
        : []
      setAnswers({ ...answers, [questionText]: newAnswers })
    } else {
      // Add answer (support multiple selection)
      const newAnswers = Array.isArray(currentAnswers)
        ? [...currentAnswers, answer]
        : [answer]
      setAnswers({ ...answers, [questionText]: newAnswers })
    }
  }

  // Handle "Other:" input change
  const handleOtherChange = (questionText, value) => {
    setOtherInputs({ ...otherInputs, [questionText]: value })
    // Update answers with "Other: {value}" format
    const currentAnswers = answers[questionText] || []
    const otherAnswers = Array.isArray(currentAnswers)
      ? currentAnswers.filter(a => typeof a === 'string' && !a.startsWith('Other:'))
      : (typeof currentAnswers === 'string' && currentAnswers.startsWith('Other:')) ? [] : []

    if (value.trim()) {
      const newAnswers = Array.isArray(currentAnswers)
        ? [...otherAnswers, `Other: ${value.trim()}`]
        : [`Other: ${value.trim()}`]
      setAnswers({ ...answers, [questionText]: newAnswers })
    } else {
      setAnswers({ ...answers, [questionText]: Array.isArray(currentAnswers) ? otherAnswers : [] })
    }
  }

  // Handle manual text input (for custom answers)
  const handleManualInput = (questionText, value) => {
    // Only update if it's not a suggested answer selection
    const suggestedAnswers = getSuggestedAnswers(questions.find(q => getQuestionText(q) === questionText))
    if (!suggestedAnswers.some(sa => sa === value)) {
      setAnswers({ ...answers, [questionText]: value })
    }
  }

  // Check if an answer is selected
  const isAnswerSelected = (questionText, answer) => {
    const currentAnswers = answers[questionText]
    if (!currentAnswers) return false
    if (Array.isArray(currentAnswers)) {
      return currentAnswers.includes(answer) || (typeof answer === 'string' && answer.startsWith('Other:') && currentAnswers.some(a => typeof a === 'string' && a.startsWith('Other:')))
    }
    return currentAnswers === answer
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    // Format answers: convert arrays to comma-separated strings for backend compatibility
    const formattedAnswers = {}
    Object.keys(answers).forEach(question => {
      const answer = answers[question]
      if (Array.isArray(answer)) {
        formattedAnswers[question] = answer.join(', ')
      } else {
        formattedAnswers[question] = answer || ''
      }
    })
    onSubmit(formattedAnswers)
    setAnswers({})
    setOtherInputs({})
  }

  if (!questions || questions.length === 0) {
    return null
  }

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h3 className="text-lg font-semibold text-gray-800 mb-4">
        Clarification Questions
      </h3>
      <p className="text-sm text-gray-600 mb-4">
        Please answer the following questions to help generate better test cases.
        You can select multiple options or provide your own answer. You can skip any question by leaving it blank.
      </p>
      <form onSubmit={handleSubmit} className="space-y-6">
        {questions.map((question, index) => {
          const questionText = getQuestionText(question)
          const suggestedAnswers = getSuggestedAnswers(question)
          const currentAnswers = answers[questionText] || []
          const hasOther = Array.isArray(currentAnswers)
            ? currentAnswers.some(a => typeof a === 'string' && a.startsWith('Other:'))
            : (typeof currentAnswers === 'string' && currentAnswers.startsWith('Other:'))
          const otherValue = otherInputs[questionText] || (hasOther && Array.isArray(currentAnswers)
            ? (currentAnswers.find(a => typeof a === 'string' && a.startsWith('Other:'))?.replace('Other: ', '') || '')
            : (typeof currentAnswers === 'string' && currentAnswers.startsWith('Other:') ? currentAnswers.replace('Other: ', '') : ''))

          return (
            <div key={index} className="border-b border-gray-200 pb-4 last:border-b-0">
              <label className="block text-sm font-medium text-gray-700 mb-3">
                {index + 1}. {questionText}
              </label>

              {/* Suggested Answer Chips */}
              {suggestedAnswers.length > 0 && (
                <div className="mb-3">
                  <div className="flex flex-wrap gap-2">
                    {suggestedAnswers.map((answer, answerIndex) => {
                      const isSelected = isAnswerSelected(questionText, answer)
                      return (
                        <button
                          key={answerIndex}
                          type="button"
                          onClick={() => handleAnswerToggle(questionText, answer)}
                          className={`px-3 py-1.5 text-sm rounded-full border transition-all ${isSelected
                              ? 'bg-blue-100 border-blue-500 text-blue-700 font-medium'
                              : 'bg-gray-50 border-gray-300 text-gray-700 hover:bg-gray-100'
                            }`}
                        >
                          {answer}
                          {isSelected && <X size={14} className="inline-block ml-1.5" />}
                        </button>
                      )
                    })}
                  </div>
                </div>
              )}

              {/* Other: Input */}
              <div className="mb-3">
                <div className="flex items-center gap-2">
                  <span className="text-sm text-gray-600 font-medium">Other:</span>
                  <input
                    type="text"
                    value={otherValue || ''}
                    onChange={(e) => handleOtherChange(questionText, e.target.value)}
                    placeholder="Enter your own answer..."
                    className="flex-1 px-3 py-1.5 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  />
                </div>
              </div>

              {/* Manual Text Input (fallback for questions without suggested answers) */}
              {suggestedAnswers.length === 0 && (
                <textarea
                  value={typeof currentAnswers === 'string' ? currentAnswers : ''}
                  onChange={(e) => handleManualInput(questionText, e.target.value)}
                  rows={2}
                  className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="Your answer (optional)..."
                />
              )}

              {/* Show selected answers summary */}
              {Array.isArray(currentAnswers) && currentAnswers.length > 0 && (
                <div className="mt-2 text-xs text-gray-500">
                  Selected: {currentAnswers.join(', ')}
                </div>
              )}
            </div>
          )
        })}

        <button
          type="submit"
          disabled={loading}
          className="flex items-center gap-2 px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <Send size={18} />
          {loading ? 'Submitting...' : 'Submit Answers'}
        </button>
      </form>
    </div>
  )
}

export default QuestionForm
