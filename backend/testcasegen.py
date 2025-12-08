"""
Test Case Generation System using LangGraph
Generates hierarchical test cases (L1, L2, L3) based on business requirements
"""

from typing import TypedDict, Annotated, Literal, Optional, List, Dict, Any
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
import operator
import json
from dotenv import load_dotenv
import os 

load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")


# ============================================================================
# STATE DEFINITION
# ============================================================================

class TestCaseState(TypedDict):
    """State that persists throughout the session"""
    # Initial input
    user_initial_prompt: str
    
    # L1 Level
    l1_clarification_questions: List[str]
    l1_clarification_answers: Dict[str, str]
    l1_test_cases: List[Dict[str, Any]]
    selected_l1_case: Optional[Dict[str, Any]]
    selected_l1_index: Optional[int]
    
    # L2 Level
    l2_clarification_questions: List[str]
    l2_clarification_answers: Dict[str, str]
    l2_test_cases: List[Dict[str, Any]]
    selected_l2_case: Optional[Dict[str, Any]]
    selected_l2_index: Optional[int]
    
    # L3 Level
    l3_clarification_questions: List[str]
    l3_clarification_answers: Dict[str, str]
    l3_test_cases: List[Dict[str, Any]]
    
    # Global Summary (all answered questions across all levels)
    answered_history: List[Dict[str, str]]  # List of all {question, answer, level, context} pairs
    global_summary: str  # Single summary of all answered questions
    
    # Final output
    full_tree_data: Dict[str, Any]
    
    # Control flow
    current_level: Literal["l1", "l2", "l3", "complete"]
    session_id: str


# ============================================================================
# LLM CONFIGURATION
# ============================================================================

def get_llm():
    """Initialize the LLM (adjust model and API key as needed)"""
    return ChatOpenAI(
        model="gpt-4",
        temperature=0.7,
        api_key=openai_api_key,
    )


# ============================================================================
# NODE FUNCTIONS
# ============================================================================

def ask_l1_questions(state: TestCaseState) -> TestCaseState:
    """
    Node: Generate optional questions to clarify L1 test case requirements
    Uses global summary for context
    """
    llm = get_llm()
    
    # Get global summary
    global_summary = state.get('global_summary', "")
    
    prompt = f"""
    You are a test case generation expert. A user has provided the following business description:
    
    {state['user_initial_prompt']}
    
    Context from Previous Answers:
    {global_summary if global_summary else "No previous context available."}
    
    Generate 3-5 optional clarification questions that would help you understand:
    1. The software systems they're using
    2. Key business processes
    3. Critical workflows
    4. Integration points
    
    Use the context to avoid duplicate questions and build upon existing knowledge.
    These questions should help generate comprehensive L1 (high-level) test cases.
    
    For each question, also provide 3-5 suggested answer options that users might commonly select.
    
    Return ONLY a JSON array of objects, each with:
    - "question": the question string
    - "suggested_answers": array of 3-5 suggested answer strings
    
    Example format:
    [
        {{"question": "What are the main software systems you use?", "suggested_answers": ["ERP System", "CRM Platform", "Custom Web Application", "Mobile App", "Database System"]}},
        {{"question": "What are your critical business workflows?", "suggested_answers": ["Order Processing", "Customer Onboarding", "Payment Processing", "Inventory Management", "Reporting"]}}
    ]
    """
    
    messages = [
        SystemMessage(content="You are a helpful test case generation assistant. Always return valid JSON."),
        HumanMessage(content=prompt)
    ]
    
    response = llm.invoke(messages)
    
    try:
        # Parse JSON response
        questions_data = json.loads(response.content)
        if not isinstance(questions_data, list):
            questions_data = [questions_data]
        
        # Ensure each question has the expected format
        questions = []
        for item in questions_data:
            if isinstance(item, dict) and 'question' in item:
                questions.append({
                    'question': item['question'],
                    'suggested_answers': item.get('suggested_answers', [])
                })
            elif isinstance(item, str):
                # Legacy format - just a question string
                questions.append({
                    'question': item,
                    'suggested_answers': []
                })
    except:
        # Fallback: try to extract questions from text
        content = response.content.strip()
        try:
            if content.startswith('[') and content.endswith(']'):
                questions_data = json.loads(content)
                questions = []
                for item in questions_data:
                    if isinstance(item, dict) and 'question' in item:
                        questions.append({
                            'question': item['question'],
                            'suggested_answers': item.get('suggested_answers', [])
                        })
                    elif isinstance(item, str):
                        questions.append({
                            'question': item,
                            'suggested_answers': []
                        })
            else:
                # Simple fallback - split by newlines or question marks
                question_strings = [q.strip() for q in content.split('\n') if q.strip() and '?' in q]
                if question_strings:
                    questions = [{'question': q, 'suggested_answers': []} for q in question_strings]
                else:
                    questions = [
                        {"question": "What are the main software systems you use?", "suggested_answers": ["ERP System", "CRM Platform", "Custom Web Application"]},
                        {"question": "What are your critical business workflows?", "suggested_answers": ["Order Processing", "Customer Onboarding", "Payment Processing"]},
                        {"question": "What are the key integration points between systems?", "suggested_answers": ["API Integration", "Database Sync", "File Transfer"]}
                    ]
        except:
            # Final fallback
            questions = [
                {"question": "What are the main software systems you use?", "suggested_answers": ["ERP System", "CRM Platform", "Custom Web Application"]},
                {"question": "What are your critical business workflows?", "suggested_answers": ["Order Processing", "Customer Onboarding", "Payment Processing"]},
                {"question": "What are the key integration points between systems?", "suggested_answers": ["API Integration", "Database Sync", "File Transfer"]}
            ]
    
    state['l1_clarification_questions'] = questions
    state['current_level'] = "l1"
    
    return state


def generate_l1_cases(state: TestCaseState) -> TestCaseState:
    """
    Node: Generate L1 test cases based on initial prompt and clarification answers
    Updates global summary after generation
    """
    llm = get_llm()
    
    answers_text = ""
    if state.get('l1_clarification_answers'):
        answers_text = "\n".join([f"Q: {k}\nA: {v}" for k, v in state['l1_clarification_answers'].items()])
    
    # Get global summary
    global_summary = state.get('global_summary', "")
    
    prompt = f"""
    You are a test case generation expert. Based on the following information, generate L1 (high-level) test cases.
    
    Business Description:
    {state['user_initial_prompt']}
    
    Context from Previous Answers:
    {global_summary if global_summary else "No previous context available."}
    
    Clarification Answers:
    {answers_text if answers_text else "No additional clarifications provided."}
    
    Generate 5-10 comprehensive L1 test cases. Each test case should:
    - Be high-level and cover major business functionality
    - Have a clear title/name
    - Include a brief description
    - Be independent and testable
    
    Return ONLY a JSON array of objects, each with:
    - "id": unique identifier (e.g., "L1_001")
    - "title": test case title
    - "description": brief description
    
    Example format:
    [
        {{"id": "L1_001", "title": "User Authentication", "description": "Test user login and authentication flows"}},
        {{"id": "L1_002", "title": "Data Processing", "description": "Test core data processing workflows"}}
    ]
    """
    
    messages = [
        SystemMessage(content="You are a helpful test case generation assistant. Always return valid JSON arrays."),
        HumanMessage(content=prompt)
    ]
    
    response = llm.invoke(messages)
    
    try:
        test_cases = json.loads(response.content)
        if not isinstance(test_cases, list):
            test_cases = [test_cases]
    except:
        # Fallback: create basic structure
        test_cases = [
            {"id": "L1_001", "title": "Core Functionality Test", "description": "Test core business functionality"},
            {"id": "L1_002", "title": "Integration Test", "description": "Test system integrations"}
        ]
    
    state['l1_test_cases'] = test_cases
    
    # Update global summary after generating L1 cases
    state = update_global_summary(state)
    
    return state


def update_global_summary(state: TestCaseState) -> TestCaseState:
    """
    Node: Update global summary with ALL answered questions from L1, L2, and L3
    This single summary is used for all question generation across all levels
    """
    llm = get_llm()
    
    # Initialize global history if not exists
    if 'answered_history' not in state:
        state['answered_history'] = []
    
    # Collect all answered questions from L1
    l1_questions = state.get('l1_clarification_questions', [])
    l1_answers = state.get('l1_clarification_answers', {})
    for q in l1_questions:
        question_text = q.get('question', str(q)) if isinstance(q, dict) else str(q)
        if question_text in l1_answers and l1_answers[question_text].strip():
            qa_pair = {
                'question': question_text,
                'answer': l1_answers[question_text],
                'level': 'L1',
                'context': 'Initial business clarification'
            }
            # Only add if not already in history (avoid duplicates)
            if qa_pair not in state['answered_history']:
                state['answered_history'].append(qa_pair)
    
    # Collect all answered questions from L2
    l2_questions = state.get('l2_clarification_questions', [])
    l2_answers = state.get('l2_clarification_answers', {})
    selected_l1 = state.get('selected_l1_case') or {}
    l1_context = f"L1: {selected_l1.get('title', 'N/A')}" if selected_l1 else "L1: N/A"
    for q in l2_questions:
        question_text = q.get('question', str(q)) if isinstance(q, dict) else str(q)
        if question_text in l2_answers and l2_answers[question_text].strip():
            qa_pair = {
                'question': question_text,
                'answer': l2_answers[question_text],
                'level': 'L2',
                'context': l1_context
            }
            # Only add if not already in history (avoid duplicates)
            if qa_pair not in state['answered_history']:
                state['answered_history'].append(qa_pair)
    
    # Collect all answered questions from L3
    l3_questions = state.get('l3_clarification_questions', [])
    l3_answers = state.get('l3_clarification_answers', {})
    selected_l2 = state.get('selected_l2_case') or {}
    l2_context = f"L2: {selected_l2.get('title', 'N/A')}" if selected_l2 else "L2: N/A"
    for q in l3_questions:
        question_text = q.get('question', str(q)) if isinstance(q, dict) else str(q)
        if question_text in l3_answers and l3_answers[question_text].strip():
            qa_pair = {
                'question': question_text,
                'answer': l3_answers[question_text],
                'level': 'L3',
                'context': l2_context
            }
            # Only add if not already in history (avoid duplicates)
            if qa_pair not in state['answered_history']:
                state['answered_history'].append(qa_pair)
    
    # Get ALL answered questions from global history
    all_answered = state['answered_history']
    
    # If no answered questions, don't create summary
    if not all_answered:
        state['global_summary'] = ""
        return state
    
    # Get existing global summary
    existing_summary = state.get('global_summary', "")
    
    # Format Q&A for summarization (concise format)
    qa_text = "\n".join([f"[{item['level']}] {item['question']}: {item['answer']}" for item in all_answered])
    
    prompt = f"""
    Summarize all answered questions into a crisp, concise summary (2-3 sentences max).
    
    Business Context: {state['user_initial_prompt']}
    
    Previous Summary: {existing_summary if existing_summary else "None"}
    
    All Answered Questions:
    {qa_text}
    
    Create a brief summary focusing on key insights. Return ONLY the summary text, no labels.
    """
    
    messages = [
        SystemMessage(content="You are a concise summarization assistant. Return only the summary text, 2-3 sentences max."),
        HumanMessage(content=prompt)
    ]
    
    response = llm.invoke(messages)
    summary = response.content.strip()
    
    # Update the global summary
    state['global_summary'] = summary
    
    return state


def ask_l2_questions(state: TestCaseState) -> TestCaseState:
    """
    Node: Generate optional questions for the selected L1 test case
    Uses L2 sibling summary for better context
    """
    llm = get_llm()
    
    selected_l1 = state.get('selected_l1_case')
    if not selected_l1:
        # If no L1 case selected, return state without questions
        state['l2_clarification_questions'] = []
        state['current_level'] = "l1"
        return state
    
    # Get global summary
    global_summary = state.get('global_summary', "")
    
    # Debug: Print the summary context being used
    print("\n" + "=" * 80)
    print("[DEBUG L2 Question Generator]")
    print("=" * 80)
    print(f"L1 Test Case: {selected_l1.get('id', 'N/A')} - {selected_l1.get('title', 'N/A')}")
    print(f"\nGlobal Summary Context:")
    if global_summary:
        print(f"  {global_summary}")
    else:
        print("  No previous context available.")
    print("=" * 80 + "\n")
    
    prompt = f"""
    You are a test case generation expert. A user has selected the following L1 test case to explore further:
    
    L1 Test Case:
    ID: {selected_l1.get('id', 'N/A')}
    Title: {selected_l1.get('title', 'N/A')}
    Description: {selected_l1.get('description', 'N/A')}
    
    Original Business Context:
    {state['user_initial_prompt']}
    
    Context from All Previous Answers:
    {global_summary if global_summary else "No previous context available."}
    
    Generate 3-5 optional clarification questions that would help you understand this specific L1 test case in more detail.
    These questions should help generate comprehensive L2 (mid-level) test cases.
    Use the context to avoid asking duplicate questions and to build upon existing knowledge.
    
    For each question, also provide 3-5 suggested answer options that users might commonly select.
    
    Return ONLY a JSON array of objects, each with:
    - "question": the question string
    - "suggested_answers": array of 3-5 suggested answer strings
    
    Example format:
    [
        {{"question": "What are the specific scenarios for this functionality?", "suggested_answers": ["Happy Path", "Error Handling", "Edge Cases", "Performance", "Security"]}},
        {{"question": "What are the integration points?", "suggested_answers": ["API Calls", "Database Access", "External Services", "File System", "Message Queue"]}}
    ]
    """
    
    messages = [
        SystemMessage(content="You are a helpful test case generation assistant. Always return valid JSON."),
        HumanMessage(content=prompt)
    ]
    
    response = llm.invoke(messages)
    
    try:
        questions_data = json.loads(response.content)
        if not isinstance(questions_data, list):
            questions_data = [questions_data]
        
        # Ensure each question has the expected format
        questions = []
        for item in questions_data:
            if isinstance(item, dict) and 'question' in item:
                questions.append({
                    'question': item['question'],
                    'suggested_answers': item.get('suggested_answers', [])
                })
            elif isinstance(item, str):
                questions.append({
                    'question': item,
                    'suggested_answers': []
                })
    except:
        questions = [
            {"question": f"What are the specific scenarios for {selected_l1.get('title', 'this functionality')}?", "suggested_answers": ["Happy Path", "Error Handling", "Edge Cases"]},
            {"question": "What are the edge cases to consider?", "suggested_answers": ["Invalid Input", "Boundary Conditions", "Concurrent Access"]},
            {"question": "What are the integration points?", "suggested_answers": ["API Calls", "Database Access", "External Services"]}
        ]
    
    state['l2_clarification_questions'] = questions
    state['current_level'] = "l2"
    
    return state


def generate_l2_cases(state: TestCaseState) -> TestCaseState:
    """
    Node: Generate L2 test cases for the selected L1 case
    Uses L2 sibling summary for better context
    """
    llm = get_llm()
    
    selected_l1 = state.get('selected_l1_case')
    if not selected_l1:
        # If no L1 case selected, return state without test cases
        state['l2_test_cases'] = state.get('l2_test_cases', [])
        state['selected_l1_case'] = None
        state['selected_l1_index'] = None
        state['l2_clarification_questions'] = []
        state['l2_clarification_answers'] = {}
        return state
    
    # Get only answered questions
    l2_questions = state.get('l2_clarification_questions', [])
    l2_answers = state.get('l2_clarification_answers', {})
    answered_q_and_a = []
    for q in l2_questions:
        question_text = q.get('question', str(q)) if isinstance(q, dict) else str(q)
        if question_text in l2_answers and l2_answers[question_text].strip():
            answered_q_and_a.append(f"Q: {question_text}\nA: {l2_answers[question_text]}")
    
    answers_text = "\n".join(answered_q_and_a) if answered_q_and_a else ""
    
    # Update global summary before generating test cases
    state = update_global_summary(state)
    
    # Get global summary
    global_summary = state.get('global_summary', "")
    
    prompt = f"""
    You are a test case generation expert. Generate L2 (mid-level) test cases for the selected L1 test case.
    
    Original Business Context:
    {state['user_initial_prompt']}
    
    Selected L1 Test Case:
    ID: {selected_l1.get('id', 'N/A')}
    Title: {selected_l1.get('title', 'N/A')}
    Description: {selected_l1.get('description', 'N/A')}
    
    Context from All Previous Answers:
    {global_summary if global_summary else "No previous context available."}
    
    Current Clarification Answers:
    {answers_text if answers_text else "No additional clarifications provided."}
    
    Generate 5-8 L2 test cases that break down the selected L1 test case into more specific scenarios.
    Use the context to ensure variety and avoid duplication.
    Each L2 test case should:
    - Be more specific than L1 but still cover significant functionality
    - Have a clear title/name
    - Include a brief description
    - Reference the parent L1 case
    
    Return ONLY a JSON array of objects, each with:
    - "id": unique identifier (e.g., "L2_001")
    - "title": test case title
    - "description": brief description
    - "parent_l1_id": the ID of the parent L1 case
    
    Example format:
    [
        {{"id": "L2_001", "title": "Login with Valid Credentials", "description": "Test successful login", "parent_l1_id": "L1_001"}},
        {{"id": "L2_002", "title": "Login with Invalid Credentials", "description": "Test login failure scenarios", "parent_l1_id": "L1_001"}}
    ]
    """
    
    messages = [
        SystemMessage(content="You are a helpful test case generation assistant. Always return valid JSON arrays."),
        HumanMessage(content=prompt)
    ]
    
    response = llm.invoke(messages)
    
    try:
        test_cases = json.loads(response.content)
        if not isinstance(test_cases, list):
            test_cases = [test_cases]
        # Ensure parent_l1_id is set
        for tc in test_cases:
            if 'parent_l1_id' not in tc:
                tc['parent_l1_id'] = selected_l1.get('id', 'L1_001')
    except:
        test_cases = [
            {"id": "L2_001", "title": "Basic Scenario", "description": "Test basic scenario", "parent_l1_id": selected_l1.get('id', 'L1_001')},
            {"id": "L2_002", "title": "Advanced Scenario", "description": "Test advanced scenario", "parent_l1_id": selected_l1.get('id', 'L1_001')}
        ]
    
    # Append new L2 cases to existing ones (don't replace)
    existing_l2 = state.get('l2_test_cases', [])
    # Check if L2 cases for this L1 already exist
    existing_for_l1 = [tc for tc in existing_l2 if tc.get('parent_l1_id') == selected_l1.get('id')]
    if not existing_for_l1:
        # Only append if we don't already have L2 cases for this L1
        state['l2_test_cases'] = existing_l2 + test_cases
    else:
        # If they exist, replace them (in case user wants to regenerate)
        state['l2_test_cases'] = [tc for tc in existing_l2 if tc.get('parent_l1_id') != selected_l1.get('id')] + test_cases
    
    # Clear selection after generating (allow selecting another L1)
    # Also clear any L2/L3 selection and questions to prevent automatic L3 generation
    state['selected_l1_case'] = None
    state['selected_l1_index'] = None
    state['selected_l2_case'] = None
    state['selected_l2_index'] = None
    state['l2_clarification_questions'] = []
    state['l2_clarification_answers'] = {}
    # Clear L3 state to ensure clean slate for next L2 selection
    state['l3_clarification_questions'] = []
    state['l3_clarification_answers'] = {}
    
    return state




def ask_l3_questions(state: TestCaseState) -> TestCaseState:
    """
    Node: Generate optional questions for the selected L2 test case
    Uses global summary for better context
    """
    llm = get_llm()
    
    selected_l2 = state.get('selected_l2_case')
    if not selected_l2:
        # If no L2 case selected, return state without questions
        state['l3_clarification_questions'] = []
        state['current_level'] = "l2"
        return state
    
    selected_l1 = state.get('selected_l1_case') or {}
    
    # Find the parent L1 case from the L2 case's parent_l1_id
    parent_l1_id = selected_l2.get('parent_l1_id')
    if parent_l1_id:
        l1_cases = state.get('l1_test_cases', [])
        parent_l1 = next((l1 for l1 in l1_cases if l1.get('id') == parent_l1_id), {})
        if parent_l1:
            selected_l1 = parent_l1
    
    # Get global summary
    global_summary = state.get('global_summary', "")
    
    # Debug: Print the summary context being used
    print("\n" + "=" * 80)
    print("[DEBUG L3 Question Generator]")
    print("=" * 80)
    print(f"L2 Test Case: {selected_l2.get('id', 'N/A')} - {selected_l2.get('title', 'N/A')}")
    print(f"Parent L1: {selected_l1.get('id', 'N/A')} - {selected_l1.get('title', 'N/A')}")
    print(f"\nGlobal Summary Context:")
    if global_summary:
        print(f"  {global_summary}")
    else:
        print("  No previous context available.")
    print("=" * 80 + "\n")
    
    prompt = f"""
    You are a test case generation expert. A user has selected the following L2 test case to explore further:
    
    Parent L1 Test Case:
    ID: {selected_l1.get('id', 'N/A')}
    Title: {selected_l1.get('title', 'N/A')}
    
    Selected L2 Test Case:
    ID: {selected_l2.get('id', 'N/A')}
    Title: {selected_l2.get('title', 'N/A')}
    Description: {selected_l2.get('description', 'N/A')}
    
    Original Business Context:
    {state['user_initial_prompt']}
    
    Context from All Previous Answers:
    {global_summary if global_summary else "No previous context available."}
    
    Generate 3-5 optional clarification questions that would help you understand this specific L2 test case in more detail.
    These questions should help generate comprehensive L3 (detailed-level) test cases.
    Use the context to avoid asking duplicate questions and to build upon existing knowledge.
    
    For each question, also provide 3-5 suggested answer options that users might commonly select.
    
    Return ONLY a JSON array of objects, each with:
    - "question": the question string
    - "suggested_answers": array of 3-5 suggested answer strings
    
    Example format:
    [
        {{"question": "What are the specific test steps?", "suggested_answers": ["Setup", "Execute", "Verify", "Cleanup", "Document"]}},
        {{"question": "What are the expected results?", "suggested_answers": ["Success", "Failure", "Partial Success", "Timeout", "Error"]}}
    ]
    """
    
    messages = [
        SystemMessage(content="You are a helpful test case generation assistant. Always return valid JSON."),
        HumanMessage(content=prompt)
    ]
    
    response = llm.invoke(messages)
    
    try:
        questions_data = json.loads(response.content)
        if not isinstance(questions_data, list):
            questions_data = [questions_data]
        
        # Ensure each question has the expected format
        questions = []
        for item in questions_data:
            if isinstance(item, dict) and 'question' in item:
                questions.append({
                    'question': item['question'],
                    'suggested_answers': item.get('suggested_answers', [])
                })
            elif isinstance(item, str):
                questions.append({
                    'question': item,
                    'suggested_answers': []
                })
    except:
        questions = [
            {"question": f"What are the specific test steps for {selected_l2.get('title', 'this scenario')}?", "suggested_answers": ["Setup", "Execute", "Verify", "Cleanup"]},
            {"question": "What are the expected results?", "suggested_answers": ["Success", "Failure", "Partial Success", "Error"]},
            {"question": "What are the test data requirements?", "suggested_answers": ["Valid Data", "Invalid Data", "Boundary Values", "Null Values"]}
        ]
    
    state['l3_clarification_questions'] = questions
    state['current_level'] = "l3"
    
    return state


def generate_l3_cases(state: TestCaseState) -> TestCaseState:
    """
    Node: Generate L3 test cases for the selected L2 case
    """
    llm = get_llm()
    
    selected_l2 = state.get('selected_l2_case')
    if not selected_l2:
        # If no L2 case selected, return state without test cases
        state['l3_test_cases'] = state.get('l3_test_cases', [])
        state['selected_l2_case'] = None
        state['selected_l2_index'] = None
        state['l3_clarification_questions'] = []
        state['l3_clarification_answers'] = {}
        return state
    
    selected_l1 = state.get('selected_l1_case') or {}
    
    # Find the parent L1 case from the L2 case's parent_l1_id
    parent_l1_id = selected_l2.get('parent_l1_id')
    if parent_l1_id:
        l1_cases = state.get('l1_test_cases', [])
        parent_l1 = next((l1 for l1 in l1_cases if l1.get('id') == parent_l1_id), {})
        if parent_l1:
            selected_l1 = parent_l1
    
    # Get L2 questions and answers for context
    l2_questions = state.get('l2_clarification_questions', [])
    l2_answers = state.get('l2_clarification_answers', {})
    l3_questions = state.get('l3_clarification_questions', [])
    l3_answers = state.get('l3_clarification_answers', {})
    
    # Format L2 questions and answers - only include questions that have been answered
    l2_questions_text = ""
    l2_answers_text = ""
    if l2_answers and l2_questions:
        answered_l2_questions = []
        for q in l2_questions:
            # Get question text (handle both string and object formats)
            question_text = q.get('question', str(q)) if isinstance(q, dict) else str(q)
            # Only include if there's an answer for this question
            if question_text in l2_answers and l2_answers[question_text].strip():
                answered_l2_questions.append(question_text)
                l2_answers_text += f"Q: {question_text}\nA: {l2_answers[question_text]}\n"
        
        if answered_l2_questions:
            l2_questions_text = "\n".join([f"- {q}" for q in answered_l2_questions])
    
    # Format L3 questions and answers - only include questions that have been answered
    l3_questions_text = ""
    l3_answers_text = ""
    if l3_answers and l3_questions:
        answered_l3_questions = []
        for q in l3_questions:
            # Get question text (handle both string and object formats)
            question_text = q.get('question', str(q)) if isinstance(q, dict) else str(q)
            # Only include if there's an answer for this question
            if question_text in l3_answers and l3_answers[question_text].strip():
                answered_l3_questions.append(question_text)
                l3_answers_text += f"Q: {question_text}\nA: {l3_answers[question_text]}\n"
        
        if answered_l3_questions:
            l3_questions_text = "\n".join([f"- {q}" for q in answered_l3_questions])
    
    # Update global summary before generating test cases
    state = update_global_summary(state)
    
    # Get global summary
    global_summary = state.get('global_summary', "")
    
    prompt = f"""
    You are a test case generation expert. Generate L3 (detailed-level) test cases for the selected L2 test case.
    
    Original Business Context:
    {state['user_initial_prompt']}
    
    Parent L1 Test Case:
    ID: {selected_l1.get('id', 'N/A')}
    Title: {selected_l1.get('title', 'N/A')}
    
    Selected L2 Test Case:
    ID: {selected_l2.get('id', 'N/A')}
    Title: {selected_l2.get('title', 'N/A')}
    Description: {selected_l2.get('description', 'N/A')}
    
    Context from All Previous Answers:
    {global_summary if global_summary else "No previous context available."}
    
    Current L2 Clarification Answers:
    {l2_answers_text if l2_answers_text else "No L2 answers were provided."}
    
    Current L3 Clarification Answers:
    {l3_answers_text if l3_answers_text else "No L3 answers were provided."}
    
    Generate 5-10 detailed L3 test cases that break down the selected L2 test case into specific, executable test scenarios.
    Use all the context from previous answers and current answers to generate comprehensive and relevant test cases.
    Each L3 test case should:
    - Be very specific and detailed
    - Include test steps or scenarios
    - Have clear expected results
    - Reference the parent L2 case
    - Consider the context from all previous questions and answers
    
    Return ONLY a JSON array of objects, each with:
    - "id": unique identifier (e.g., "L3_001")
    - "title": test case title
    - "description": detailed description
    - "test_steps": array of test steps (optional)
    - "expected_result": expected result (optional)
    - "parent_l2_id": the ID of the parent L2 case
    
    Example format:
    [
        {{
            "id": "L3_001",
            "title": "Valid Email Login",
            "description": "Test login with valid email and password",
            "test_steps": ["Navigate to login page", "Enter valid email", "Enter valid password", "Click login"],
            "expected_result": "User is successfully logged in",
            "parent_l2_id": "L2_001"
        }}
    ]
    """
    
    messages = [
        SystemMessage(content="You are a helpful test case generation assistant. Always return valid JSON arrays."),
        HumanMessage(content=prompt)
    ]
    
    response = llm.invoke(messages)
    
    try:
        test_cases = json.loads(response.content)
        if not isinstance(test_cases, list):
            test_cases = [test_cases]
        # Ensure parent_l2_id is set
        for tc in test_cases:
            if 'parent_l2_id' not in tc:
                tc['parent_l2_id'] = selected_l2.get('id', 'L2_001')
    except:
        test_cases = [
            {
                "id": "L3_001",
                "title": "Detailed Test Case 1",
                "description": "Test detailed scenario 1",
                "test_steps": ["Step 1", "Step 2"],
                "expected_result": "Expected result",
                "parent_l2_id": selected_l2.get('id', 'L2_001')
            }
        ]
    
    # Append new L3 cases to existing ones (don't replace)
    existing_l3 = state.get('l3_test_cases', [])
    # Check if L3 cases for this L2 already exist
    existing_for_l2 = [tc for tc in existing_l3 if tc.get('parent_l2_id') == selected_l2.get('id')]
    if not existing_for_l2:
        # Only append if we don't already have L3 cases for this L2
        state['l3_test_cases'] = existing_l3 + test_cases
    else:
        # If they exist, replace them (in case user wants to regenerate)
        state['l3_test_cases'] = [tc for tc in existing_l3 if tc.get('parent_l2_id') != selected_l2.get('id')] + test_cases
    
    # Clear selection after generating (allow selecting another L2)
    state['selected_l2_case'] = None
    state['selected_l2_index'] = None
    state['l3_clarification_questions'] = []
    state['l3_clarification_answers'] = {}
    
    return state


def build_tree(state: TestCaseState) -> TestCaseState:
    """
    Node: Aggregate all test cases into a hierarchical tree structure
    """
    tree = {
        "l1_cases": [],
        "session_id": state.get('session_id', 'unknown'),
        "user_prompt": state.get('user_initial_prompt', '')
    }
    
    # Build L1 structure
    l1_cases = state.get('l1_test_cases', [])
    for l1_case in l1_cases:
        l1_node = {
            "id": l1_case.get('id', ''),
            "title": l1_case.get('title', ''),
            "description": l1_case.get('description', ''),
            "l2_cases": []
        }
        
        # Add L2 cases for this L1
        l2_cases = state.get('l2_test_cases', [])
        for l2_case in l2_cases:
            if l2_case.get('parent_l1_id') == l1_case.get('id'):
                l2_node = {
                    "id": l2_case.get('id', ''),
                    "title": l2_case.get('title', ''),
                    "description": l2_case.get('description', ''),
                    "l3_cases": []
                }
                
                # Add L3 cases for this L2
                l3_cases = state.get('l3_test_cases', [])
                for l3_case in l3_cases:
                    if l3_case.get('parent_l2_id') == l2_case.get('id'):
                        l3_node = {
                            "id": l3_case.get('id', ''),
                            "title": l3_case.get('title', ''),
                            "description": l3_case.get('description', ''),
                            "test_steps": l3_case.get('test_steps', []),
                            "expected_result": l3_case.get('expected_result', '')
                        }
                        l2_node["l3_cases"].append(l3_node)
                
                l1_node["l2_cases"].append(l2_node)
        
        tree["l1_cases"].append(l1_node)
    
    state['full_tree_data'] = tree
    state['current_level'] = "complete"
    
    return state


# ============================================================================
# CONDITIONAL EDGE FUNCTIONS
# ============================================================================

def should_continue_to_l2(state: TestCaseState) -> Literal["ask_l2_questions", "wait_for_l1_selection", "build_tree"]:
    """Decide whether to proceed to L2 generation or wait for user input"""
    if state.get('selected_l1_case') and state.get('selected_l1_index') is not None:
        return "ask_l2_questions"
    elif state.get('l1_test_cases'):
        return "wait_for_l1_selection"
    else:
        return "build_tree"


def should_continue_to_l3(state: TestCaseState) -> Literal["ask_l3_questions", "wait_for_l2_selection", "build_tree"]:
    """Decide whether to proceed to L3 generation or wait for user input"""
    if state.get('selected_l2_case') and state.get('selected_l2_index') is not None:
        return "ask_l3_questions"
    elif state.get('l2_test_cases'):
        return "wait_for_l2_selection"
    else:
        return "build_tree"


def should_build_tree(state: TestCaseState) -> Literal["build_tree", "wait_for_l3_completion"]:
    """Decide whether to build the final tree"""
    if state.get('l3_test_cases'):
        return "build_tree"
    else:
        return "wait_for_l3_completion"


# ============================================================================
# GRAPH CONSTRUCTION
# ============================================================================

def create_test_case_graph():
    """Create and configure the LangGraph workflow"""
    
    # Initialize memory for checkpointing
    memory = MemorySaver()
    
    # Create the graph
    workflow = StateGraph(TestCaseState)
    
    # Add nodes
    workflow.add_node("ask_l1_questions", ask_l1_questions)
    workflow.add_node("generate_l1_cases", generate_l1_cases)
    workflow.add_node("ask_l2_questions", ask_l2_questions)
    workflow.add_node("generate_l2_cases", generate_l2_cases)
    workflow.add_node("ask_l3_questions", ask_l3_questions)
    workflow.add_node("generate_l3_cases", generate_l3_cases)
    workflow.add_node("build_tree", build_tree)
    
    # Set entry point
    workflow.set_entry_point("ask_l1_questions")
    
    # Add edges
    workflow.add_edge("ask_l1_questions", "generate_l1_cases")
    
    # Conditional edge after L1 generation
    workflow.add_conditional_edges(
        "generate_l1_cases",
        should_continue_to_l2,
        {
            "ask_l2_questions": "ask_l2_questions",
            "wait_for_l1_selection": END,  # Wait for user to select L1
            "build_tree": "build_tree"
        }
    )
    
    # Conditional edge after L2 questions - check if answers exist
    workflow.add_conditional_edges(
        "ask_l2_questions",
        lambda state: "generate_l2_cases" if state.get("l2_clarification_answers") else "wait_for_l2_answers",
        {
            "generate_l2_cases": "generate_l2_cases",
            "wait_for_l2_answers": END  # Wait for user to submit answers
        }
    )
    
    # Conditional edge after L2 generation
    workflow.add_conditional_edges(
        "generate_l2_cases",
        should_continue_to_l3,
        {
            "ask_l3_questions": "ask_l3_questions",
            "wait_for_l2_selection": END,  # Wait for user to select L2
            "build_tree": "build_tree"
        }
    )
    
    # Conditional edge after L3 questions - check if answers exist
    workflow.add_conditional_edges(
        "ask_l3_questions",
        lambda state: "generate_l3_cases" if state.get("l3_clarification_answers") else "wait_for_l3_answers",
        {
            "generate_l3_cases": "generate_l3_cases",
            "wait_for_l3_answers": END  # Wait for user to submit answers
        }
    )
    
    # Conditional edge after L3 generation
    workflow.add_conditional_edges(
        "generate_l3_cases",
        should_build_tree,
        {
            "build_tree": "build_tree",
            "wait_for_l3_completion": END
        }
    )
    
    workflow.add_edge("build_tree", END)
    
    # Compile with memory
    app = workflow.compile(checkpointer=memory)
    
    return app


# ============================================================================
# API FUNCTIONS FOR INTERACTION
# ============================================================================

class TestCaseGenerator:
    """Main class for interacting with the test case generation system"""
    
    def __init__(self):
        self.app = create_test_case_graph()
        self.current_thread_id = None
    
    def start_session(self, user_prompt: str, session_id: str = None) -> Dict[str, Any]:
        """
        Start a new session with user's initial prompt
        
        Args:
            user_prompt: The initial business description
            session_id: Optional session ID, will generate one if not provided
        
        Returns:
            State after L1 questions are generated
        """
        if session_id is None:
            import uuid
            session_id = f"session_{uuid.uuid4().hex[:8]}"
        
        self.current_thread_id = session_id
        
        initial_state = {
            "user_initial_prompt": user_prompt,
            "l1_clarification_questions": [],
            "l1_clarification_answers": {},
            "l1_test_cases": [],
            "selected_l1_case": None,
            "selected_l1_index": None,
            "l2_clarification_questions": [],
            "l2_clarification_answers": {},
            "l2_test_cases": [],
            "selected_l2_case": None,
            "selected_l2_index": None,
            "l3_clarification_questions": [],
            "l3_clarification_answers": {},
            "l3_test_cases": [],
            "answered_history": [],
            "global_summary": "",
            "full_tree_data": {},
            "current_level": "l1",
            "session_id": session_id
        }
        
        config = {"configurable": {"thread_id": session_id}}
        
        # Run until we need user input (after L1 questions or L1 cases)
        result = self.app.invoke(initial_state, config)
        
        return result
    
    def submit_l1_answers(self, answers: Dict[str, str], session_id: str = None) -> Dict[str, Any]:
        """
        Submit answers to L1 clarification questions and generate L1 test cases
        
        Args:
            answers: Dictionary mapping question to answer
            session_id: Session ID (uses current if not provided)
        
        Returns:
            State after L1 test cases are generated
        """
        if session_id is None:
            session_id = self.current_thread_id
        
        config = {"configurable": {"thread_id": session_id}}
        
        # Get current state
        state = self.app.get_state(config)
        current_state = state.values
        
        # Update with answers
        current_state["l1_clarification_answers"] = answers
        
        # Continue from generate_l1_cases
        result = self.app.invoke(current_state, config)
        
        return result
    
    def select_l1_case(self, l1_index: int, session_id: str = None) -> Dict[str, Any]:
        """
        Select an L1 test case to explore further
        
        Args:
            l1_index: Index of the L1 test case to select
            session_id: Session ID (uses current if not provided)
        
        Returns:
            State after L2 questions are generated (stops and waits for answers)
        """
        if session_id is None:
            session_id = self.current_thread_id
        
        config = {"configurable": {"thread_id": session_id}}
        
        # Get current state
        state = self.app.get_state(config)
        current_state = state.values
        
        # Ensure global summary and history are initialized if missing
        if 'answered_history' not in current_state:
            current_state['answered_history'] = []
        if 'global_summary' not in current_state:
            current_state['global_summary'] = ""
        
        # Select L1 case
        l1_cases = current_state.get("l1_test_cases", [])
        if 0 <= l1_index < len(l1_cases):
            current_state["selected_l1_case"] = l1_cases[l1_index]
            current_state["selected_l1_index"] = l1_index
        
        # Clear any previous L2/L3 state to start fresh (but preserve global summary and history)
        current_state["l2_clarification_questions"] = []
        current_state["l2_clarification_answers"] = {}  # Clear answers so graph stops after questions
        current_state["selected_l2_case"] = None
        current_state["selected_l2_index"] = None
        current_state["l3_clarification_questions"] = []
        current_state["l3_clarification_answers"] = {}
        # DO NOT clear answered_history, global_summary
        
        # Directly call ask_l2_questions function to generate questions
        current_state = ask_l2_questions(current_state)
        
        # Update state in checkpoint
        self.app.update_state(config, current_state)
        
        return current_state
    
    def submit_l2_answers(self, answers: Dict[str, str], session_id: str = None) -> Dict[str, Any]:
        """
        Submit answers to L2 clarification questions and generate L2 test cases
        
        Args:
            answers: Dictionary mapping question to answer
            session_id: Session ID (uses current if not provided)
        
        Returns:
            State after L2 test cases are generated
        """
        if session_id is None:
            session_id = self.current_thread_id
        
        config = {"configurable": {"thread_id": session_id}}
        
        # Get current state
        state = self.app.get_state(config)
        current_state = state.values
        
        # Update with answers
        current_state["l2_clarification_answers"] = answers
        
        # Update checkpoint
        self.app.update_state(config, current_state)
        
        # Directly call generate_l2_cases function to generate test cases
        current_state = generate_l2_cases(current_state)
        
        # Update checkpoint again
        self.app.update_state(config, current_state)
        
        return current_state
    
    def select_l2_case(self, l2_index: int, session_id: str = None) -> Dict[str, Any]:
        """
        Select an L2 test case to explore further
        
        Args:
            l2_index: Index of the L2 test case to select
            session_id: Session ID (uses current if not provided)
        
        Returns:
            State after L3 questions are generated (stops and waits for answers)
        """
        if session_id is None:
            session_id = self.current_thread_id
        
        config = {"configurable": {"thread_id": session_id}}
        
        # Get current state
        state = self.app.get_state(config)
        current_state = state.values
        
        # Ensure global summary and history are initialized if missing
        if 'answered_history' not in current_state:
            current_state['answered_history'] = []
        if 'global_summary' not in current_state:
            current_state['global_summary'] = ""
        
        # Select L2 case
        l2_cases = current_state.get("l2_test_cases", [])
        if 0 <= l2_index < len(l2_cases):
            current_state["selected_l2_case"] = l2_cases[l2_index]
            current_state["selected_l2_index"] = l2_index
        
        # Clear any previous L3 state to start fresh (but preserve global summary and history)
        current_state["l3_clarification_questions"] = []
        current_state["l3_clarification_answers"] = {}  # Clear answers so graph stops after questions
        # DO NOT clear answered_history, global_summary
        
        # Directly call ask_l3_questions function to generate questions
        current_state = ask_l3_questions(current_state)
        
        # Update state in checkpoint
        self.app.update_state(config, current_state)
        
        return current_state
    
    def submit_l3_answers(self, answers: Dict[str, str], session_id: str = None) -> Dict[str, Any]:
        """
        Submit answers to L3 clarification questions and generate L3 test cases
        
        Args:
            answers: Dictionary mapping question to answer
            session_id: Session ID (uses current if not provided)
        
        Returns:
            State after L3 test cases are generated and tree is built
        """
        if session_id is None:
            session_id = self.current_thread_id
        
        config = {"configurable": {"thread_id": session_id}}
        
        # Get current state
        state = self.app.get_state(config)
        current_state = state.values
        
        # Update with answers
        current_state["l3_clarification_answers"] = answers
        
        # Update checkpoint
        self.app.update_state(config, current_state)
        
        # Directly call generate_l3_cases function to generate test cases
        current_state = generate_l3_cases(current_state)
        
        # Build tree
        current_state = build_tree(current_state)
        
        # Update checkpoint again
        self.app.update_state(config, current_state)
        
        return current_state
    
    def get_current_state(self, session_id: str = None) -> Dict[str, Any]:
        """
        Get the current state of the session
        
        Args:
            session_id: Session ID (uses current if not provided)
        
        Returns:
            Current state dictionary
        """
        if session_id is None:
            session_id = self.current_thread_id
        
        config = {"configurable": {"thread_id": session_id}}
        state = self.app.get_state(config)
        
        return state.values
    
    def get_tree(self, session_id: str = None) -> Dict[str, Any]:
        """
        Get the final tree structure
        
        Args:
            session_id: Session ID (uses current if not provided)
        
        Returns:
            Tree structure dictionary
        """
        state = self.get_current_state(session_id)
        return state.get("full_tree_data", {})


# ============================================================================
# INTERACTIVE TERMINAL INTERFACE
# ============================================================================

def get_user_input(prompt: str, allow_empty: bool = False) -> str:
    """Get input from user with optional empty check"""
    while True:
        user_input = input(prompt).strip()
        if user_input or allow_empty:
            return user_input
        print("Input cannot be empty. Please try again.")


def get_user_choice(prompt: str, max_choice: int) -> int:
    """Get a valid choice from user"""
    while True:
        try:
            choice = int(input(prompt))
            if 0 <= choice < max_choice:
                return choice
            print(f"Please enter a number between 0 and {max_choice - 1}")
        except ValueError:
            print("Please enter a valid number")


def print_section(title: str):
    """Print a formatted section header"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def print_test_cases(test_cases: List[Dict[str, Any]], level: str):
    """Print test cases in a formatted way"""
    if not test_cases:
        print(f"No {level} test cases generated.")
        return
    
    print(f"\n{level.upper()} Test Cases Generated ({len(test_cases)}):")
    for i, case in enumerate(test_cases):
        print(f"\n  [{i}] {case.get('id', 'N/A')} - {case.get('title', 'N/A')}")
        desc = case.get('description', '')
        if desc:
            print(f"      Description: {desc}")


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("  TEST CASE GENERATION SYSTEM - INTERACTIVE MODE")
    print("=" * 70)
    
    try:
        generator = TestCaseGenerator()
        
        # Step 1: Get user's business prompt
        print_section("STEP 1: Business Description")
        print("Please describe your business, including:")
        print("  - Software systems you use")
        print("  - Key business processes")
        print("  - Critical workflows")
        print("\nEnter your business description (press Enter twice when done):")
        
        lines = []
        while True:
            line = input()
            if line == "" and lines:  # Empty line after content means done
                break
            if line:
                lines.append(line)
        
        user_prompt = "\n".join(lines)
        if not user_prompt.strip():
            print("Error: Business description cannot be empty!")
            exit(1)
        
        print("\n✓ Processing your business description...")
        initial_state = generator.start_session(user_prompt=user_prompt)
        
        # Step 2: Show L1 questions and get answers
        print_section("STEP 2: L1 Clarification Questions")
        l1_questions = initial_state.get('l1_clarification_questions', [])
        
        if l1_questions:
            print("The system has generated the following optional questions:")
            print("(You can skip any question by pressing Enter without typing)")
            print()
            
            l1_answers = {}
            for i, question in enumerate(l1_questions, 1):
                answer = get_user_input(f"Q{i}: {question}\nYour answer (or press Enter to skip): ", allow_empty=True)
                if answer:
                    l1_answers[question] = answer
        else:
            print("No clarification questions generated.")
            l1_answers = {}
        
        print("\n✓ Generating L1 test cases...")
        l1_state = generator.submit_l1_answers(l1_answers)
        
        # Step 3: Show L1 test cases and let user select
        print_section("STEP 3: L1 Test Cases")
        l1_test_cases = l1_state.get('l1_test_cases', [])
        print_test_cases(l1_test_cases, "L1")
        
        if not l1_test_cases:
            print("\nNo L1 test cases were generated. Exiting.")
            exit(1)
        
        print(f"\nSelect an L1 test case to explore further (0-{len(l1_test_cases) - 1}):")
        l1_choice = get_user_choice("Enter your choice: ", len(l1_test_cases))
        
        print(f"\n✓ Exploring L1 case: {l1_test_cases[l1_choice].get('title')}")
        l2_state = generator.select_l1_case(l1_choice)
        
        # Step 4: Show L2 questions and get answers
        print_section("STEP 4: L2 Clarification Questions")
        l2_questions = l2_state.get('l2_clarification_questions', [])
        
        if l2_questions:
            print("The system has generated the following optional questions:")
            print("(You can skip any question by pressing Enter without typing)")
            print()
            
            l2_answers = {}
            for i, question in enumerate(l2_questions, 1):
                answer = get_user_input(f"Q{i}: {question}\nYour answer (or press Enter to skip): ", allow_empty=True)
                if answer:
                    l2_answers[question] = answer
        else:
            print("No clarification questions generated.")
            l2_answers = {}
        
        print("\n✓ Generating L2 test cases...")
        l2_cases_state = generator.submit_l2_answers(l2_answers)
        
        # Step 5: Show L2 test cases and let user select
        print_section("STEP 5: L2 Test Cases")
        l2_test_cases = l2_cases_state.get('l2_test_cases', [])
        print_test_cases(l2_test_cases, "L2")
        
        if not l2_test_cases:
            print("\nNo L2 test cases were generated. Exiting.")
            exit(1)
        
        print(f"\nSelect an L2 test case to explore further (0-{len(l2_test_cases) - 1}):")
        l2_choice = get_user_choice("Enter your choice: ", len(l2_test_cases))
        
        print(f"\n✓ Exploring L2 case: {l2_test_cases[l2_choice].get('title')}")
        l3_state = generator.select_l2_case(l2_choice)
        
        # Step 6: Show L3 questions and get answers
        print_section("STEP 6: L3 Clarification Questions")
        l3_questions = l3_state.get('l3_clarification_questions', [])
        
        if l3_questions:
            print("The system has generated the following optional questions:")
            print("(You can skip any question by pressing Enter without typing)")
            print()
            
            l3_answers = {}
            for i, question in enumerate(l3_questions, 1):
                answer = get_user_input(f"Q{i}: {question}\nYour answer (or press Enter to skip): ", allow_empty=True)
                if answer:
                    l3_answers[question] = answer
        else:
            print("No clarification questions generated.")
            l3_answers = {}
        
        print("\n✓ Generating L3 test cases and building final tree...")
        final_state = generator.submit_l3_answers(l3_answers)
        
        # Step 7: Show final tree
        print_section("STEP 7: Final Test Case Tree")
        tree = generator.get_tree()
        
        print("\nComplete Test Case Hierarchy:")
        print(json.dumps(tree, indent=2))
        
        # Also print a more readable format
        print("\n" + "=" * 70)
        print("  READABLE TREE STRUCTURE")
        print("=" * 70)
        
        l1_cases = tree.get('l1_cases', [])
        for l1_idx, l1_case in enumerate(l1_cases, 1):
            print(f"\nL1-{l1_idx}: [{l1_case.get('id')}] {l1_case.get('title')}")
            print(f"     {l1_case.get('description', '')}")
            
            l2_cases = l1_case.get('l2_cases', [])
            for l2_idx, l2_case in enumerate(l2_cases, 1):
                print(f"  └─ L2-{l2_idx}: [{l2_case.get('id')}] {l2_case.get('title')}")
                print(f"       {l2_case.get('description', '')}")
                
                l3_cases = l2_case.get('l3_cases', [])
                for l3_idx, l3_case in enumerate(l3_cases, 1):
                    print(f"      └─ L3-{l3_idx}: [{l3_case.get('id')}] {l3_case.get('title')}")
                    print(f"           {l3_case.get('description', '')}")
                    if l3_case.get('test_steps'):
                        print(f"           Steps: {', '.join(l3_case.get('test_steps', []))}")
                    if l3_case.get('expected_result'):
                        print(f"           Expected: {l3_case.get('expected_result')}")
        
        print("\n" + "=" * 70)
        print("  ✓ TEST CASE GENERATION COMPLETE!")
        print("=" * 70)
        print(f"\nSession ID: {tree.get('session_id', 'N/A')}")
        print(f"Total L1 Cases: {len(l1_cases)}")
        print(f"Total L2 Cases: {sum(len(l1.get('l2_cases', [])) for l1 in l1_cases)}")
        print(f"Total L3 Cases: {sum(len(l2.get('l3_cases', [])) for l1 in l1_cases for l2 in l1.get('l2_cases', []))}")
        
    except KeyboardInterrupt:
        print("\n\n⚠ Process interrupted by user.")
        exit(0)
    except Exception as e:
        print(f"\n\n✗ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        exit(1)

