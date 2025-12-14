"""
Pydantic schemas for request/response validation
"""
from pydantic import BaseModel, EmailStr
from typing import Dict, List, Optional, Any
from datetime import datetime


# User schemas
class UserCreate(BaseModel):
    email: EmailStr
    username: str
    password: str


class UserResponse(BaseModel):
    id: int
    email: str
    username: str
    created_at: datetime
    
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


# Auth schemas
class Token(BaseModel):
    access_token: str
    token_type: str


# Session schemas
class SessionCreate(BaseModel):
    title: Optional[str] = None  # Optional, will be auto-generated from user_prompt if not provided
    user_prompt: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_prompt": "I run an e-commerce platform..."
            }
        }


class SessionUpdate(BaseModel):
    title: Optional[str] = None


class SessionResponse(BaseModel):
    id: int
    user_id: int
    title: str
    user_prompt: str
    state_data: Dict[str, Any]
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True


# Test case state schemas
class TestCaseStateResponse(BaseModel):
    user_initial_prompt: str
    l1_clarification_questions: List[Any]  # Can be List[str] or List[Dict] with question and suggested_answers
    l1_clarification_answers: Dict[str, str]
    l1_test_cases: List[Dict[str, Any]]
    selected_l1_case: Optional[Dict[str, Any]]
    selected_l1_index: Optional[int]
    l2_clarification_questions: List[Any]  # Can be List[str] or List[Dict] with question and suggested_answers
    l2_clarification_answers: Dict[str, str]
    l2_test_cases: List[Dict[str, Any]]
    selected_l2_case: Optional[Dict[str, Any]]
    selected_l2_index: Optional[int]
    l3_clarification_questions: List[Any]  # Can be List[str] or List[Dict] with question and suggested_answers
    l3_clarification_answers: Dict[str, str]
    l3_test_cases: List[Dict[str, Any]]
    full_tree_data: Dict[str, Any]
    current_level: str
    session_id: str


# Question/Answer schemas
class QuestionAnswer(BaseModel):
    answers: Dict[str, str]  # question -> answer mapping


# PlantUML schemas
class PlantUMLGenerateRequest(BaseModel):
    session_id: int
    test_case_id: str  # L1 or L2 test case ID
    diagram_type: str  # "l1" or "l2"
    test_case_title: str


class PlantUMLEditRequest(BaseModel):
    diagram_id: int
    edit_prompt: str
    diagram_type: Optional[str] = "activity"  # activity, sequence, flowchart


class PlantUMLDiagramResponse(BaseModel):
    id: int
    session_id: int
    diagram_type: str
    test_case_id: str
    test_case_title: str
    plantuml_code: str
    image_url: str  # URL to retrieve the image
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class PlantUMLImageResponse(BaseModel):
    image_data: bytes  # Base64 encoded or binary
    content_type: str = "image/png"
