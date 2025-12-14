"""
Database models
"""
from sqlalchemy import Column, Integer, String, DateTime, Text, JSON, LargeBinary, ForeignKey
from sqlalchemy.sql import func
from database import Base


class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Session(Base):
    __tablename__ = "sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    title = Column(String, nullable=False)
    user_prompt = Column(Text, nullable=False)
    state_data = Column(JSON, default={})  # Stores the full TestCaseState
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class PlantUMLDiagram(Base):
    __tablename__ = "plantuml_diagrams"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Diagram metadata
    diagram_type = Column(String, nullable=False)  # "l1" or "l2"
    test_case_id = Column(String, nullable=False)  # L1 or L2 test case ID
    test_case_title = Column(String, nullable=False)
    
    # PlantUML code and rendered image
    plantuml_code = Column(Text, nullable=False)  # Original PlantUML code
    image_data = Column(LargeBinary, nullable=False)  # PNG image as binary
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

