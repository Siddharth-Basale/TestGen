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
    title: Optional[str] = None
    user_prompt: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "title": "My Test Session",
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

