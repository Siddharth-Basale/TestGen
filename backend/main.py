"""
FastAPI Backend for Test Case Generation System
"""
from fastapi import FastAPI, Depends, HTTPException, status, Query, Header, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Optional
import uvicorn
import json
import asyncio

from database import SessionLocal, engine, Base
from models import User, Session as SessionModel
from schemas import (
    UserCreate, UserResponse, Token, 
    SessionCreate, SessionResponse, SessionUpdate,
    TestCaseStateResponse, QuestionAnswer
)
from auth import (
    get_password_hash, verify_password, 
    create_access_token, get_current_user
)
import sys
import os

from testcasegen import TestCaseGenerator, generate_session_title

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Test Case Generation API", version="1.0.0")

# Debugging middleware to log all requests (headers removed)
@app.middleware("http")
async def debug_middleware(request: Request, call_next):
    response = await call_next(request)
    return response

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],  # React dev servers
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ============================================================================
# AUTHENTICATION ENDPOINTS
# ============================================================================

@app.post("/api/auth/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def signup(user_data: UserCreate, db: Session = Depends(get_db)):
    """Register a new user"""
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user
    hashed_password = get_password_hash(user_data.password)
    db_user = User(
        email=user_data.email,
        username=user_data.username,
        hashed_password=hashed_password
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    return db_user


@app.post("/api/auth/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Login and get access token"""
    user = db.query(User).filter(User.email == form_data.username).first()
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    from auth import ACCESS_TOKEN_EXPIRE_MINUTES
    from datetime import timedelta
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email, "user_id": user.id},
        expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/api/auth/me")
def get_current_user_info(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """Get current user information"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    try:
        token = authorization[7:]  # Remove 'Bearer ' prefix
        from jose import jwt, JWTError
        from auth import SECRET_KEY, ALGORITHM
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        
        if not email:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        user = db.query(User).filter(User.email == email).first()
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        
        return {
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "created_at": user.created_at.isoformat() if user.created_at else None
        }
    except JWTError as e:
        print(f"JWT Error: {e}")
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        print(f"Error in get_current_user_info: {e}")
        raise HTTPException(status_code=401, detail="Authentication failed")


# ============================================================================
# SESSION ENDPOINTS
# ============================================================================

@app.post("/api/sessions", status_code=status.HTTP_201_CREATED)
def create_session(
    session_data: SessionCreate,
    request: Request,
    db: Session = Depends(get_db)
):
    """Create a new test case generation session"""
    authorization = request.headers.get("Authorization")
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    try:
        token = authorization[7:]
        from jose import jwt, JWTError
        from auth import SECRET_KEY, ALGORITHM
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        
        user = db.query(User).filter(User.email == email).first()
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        
        # Validate session_data
        if not session_data.user_prompt or not session_data.user_prompt.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="user_prompt is required"
            )
        
        # Generate title automatically from business description
        generated_title = generate_session_title(session_data.user_prompt.strip())
        
        db_session = SessionModel(
            user_id=user.id,
            title=generated_title,
            user_prompt=session_data.user_prompt.strip(),
            state_data={}
        )
        db.add(db_session)
        db.commit()
        db.refresh(db_session)
        
        return {
            "id": db_session.id,
            "user_id": db_session.user_id,
            "title": db_session.title,
            "user_prompt": db_session.user_prompt,
            "state_data": db_session.state_data or {},
            "created_at": db_session.created_at.isoformat() if db_session.created_at else None,
            "updated_at": db_session.updated_at.isoformat() if db_session.updated_at else None
        }
    except HTTPException:
        raise
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        print(f"Error in create_session: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to create session: {str(e)}")


@app.get("/api/sessions")
def get_sessions(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """Get all sessions for current user"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    try:
        token = authorization[7:]
        from jose import jwt, JWTError
        from auth import SECRET_KEY, ALGORITHM
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        
        user = db.query(User).filter(User.email == email).first()
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        
        sessions = db.query(SessionModel).filter(
            SessionModel.user_id == user.id
        ).order_by(SessionModel.created_at.desc()).all()
        
        return [
            {
                "id": s.id,
                "user_id": s.user_id,
                "title": s.title,
                "user_prompt": s.user_prompt,
                "state_data": s.state_data or {},
                "created_at": s.created_at.isoformat() if s.created_at else None,
                "updated_at": s.updated_at.isoformat() if s.updated_at else None
            }
            for s in sessions
        ]
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        print(f"Error in get_sessions: {e}")
        raise HTTPException(status_code=401, detail="Authentication failed")


@app.get("/api/sessions/{session_id}", response_model=SessionResponse)
def get_session(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific session"""
    db_session = db.query(SessionModel).filter(
        SessionModel.id == session_id,
        SessionModel.user_id == current_user.id
    ).first()
    
    if not db_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    return db_session


@app.delete("/api/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session(
    session_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """Delete a session"""
    print(f"\n=== DEBUG: delete_session called ===")
    print(f"Session ID: {session_id}")
    
    # Get authorization
    authorization = request.headers.get("Authorization")
    print(f"Authorization header: {authorization[:20] if authorization else 'None'}...")
    
    if not authorization or not authorization.startswith("Bearer "):
        print("ERROR: No valid authorization header")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    try:
        token = authorization[7:]
        from jose import jwt, JWTError
        from auth import SECRET_KEY, ALGORITHM
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        print(f"Decoded email: {email}")
        
        user = db.query(User).filter(User.email == email).first()
        if not user:
            print(f"ERROR: User not found for email: {email}")
            raise HTTPException(status_code=401, detail="User not found")
        
        print(f"User found: {user.id} - {user.email}")
        
        db_session = db.query(SessionModel).filter(
            SessionModel.id == session_id,
            SessionModel.user_id == user.id
        ).first()
        
        if not db_session:
            print(f"ERROR: Session {session_id} not found for user {user.id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )
        
        print(f"Session found: {db_session.id} - {db_session.title}")
        print("Deleting session...")
        
        db.delete(db_session)
        db.commit()
        print("Session deleted successfully")
        
        return None
    except HTTPException:
        raise
    except JWTError as e:
        print(f"JWT Error: {e}")
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        print(f"ERROR in delete_session: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to delete session: {str(e)}")


# ============================================================================
# TEST CASE GENERATION ENDPOINTS
# ============================================================================

@app.post("/api/sessions/{session_id}/start")
def start_session(
    session_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """Start test case generation for a session"""
    print(f"\n=== DEBUG: start_session called ===")
    print(f"Session ID: {session_id}")
    
    # Get authorization
    authorization = request.headers.get("Authorization")
    print(f"Authorization header: {authorization[:20] if authorization else 'None'}...")
    
    if not authorization or not authorization.startswith("Bearer "):
        print("ERROR: No valid authorization header")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    try:
        token = authorization[7:]
        from jose import jwt, JWTError
        from auth import SECRET_KEY, ALGORITHM
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        print(f"Decoded email: {email}")
        
        user = db.query(User).filter(User.email == email).first()
        if not user:
            print(f"ERROR: User not found for email: {email}")
            raise HTTPException(status_code=401, detail="User not found")
        
        print(f"User found: {user.id} - {user.email}")
        
        db_session = db.query(SessionModel).filter(
            SessionModel.id == session_id,
            SessionModel.user_id == user.id
        ).first()
        
        if not db_session:
            print(f"ERROR: Session {session_id} not found for user {user.id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )
        
        print(f"Session found: {db_session.id} - {db_session.title}")
        print(f"User prompt: {db_session.user_prompt[:50]}...")
        
        # Initialize generator
        print("Initializing TestCaseGenerator...")
        generator = TestCaseGenerator()
        
        # Start session
        print(f"Starting session with ID: user_{user.id}_session_{session_id}")
        state = generator.start_session(
            user_prompt=db_session.user_prompt,
            session_id=f"user_{user.id}_session_{session_id}"
        )
        
        print(f"State generated. Keys: {list(state.keys())}")
        print(f"L1 questions count: {len(state.get('l1_clarification_questions', []))}")
        
        # Save state to database
        db_session.state_data = state
        db.commit()
        print("State saved to database")
        
        return state
    except HTTPException:
        raise
    except JWTError as e:
        print(f"JWT Error: {e}")
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        print(f"ERROR in start_session: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to start session: {str(e)}")


@app.post("/api/sessions/{session_id}/start/stream")
async def start_session_stream(
    session_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """Start test case generation for a session with streaming"""
    authorization = request.headers.get("Authorization")
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    try:
        token = authorization[7:]
        from jose import jwt, JWTError
        from auth import SECRET_KEY, ALGORITHM
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        
        user = db.query(User).filter(User.email == email).first()
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        
        db_session = db.query(SessionModel).filter(
            SessionModel.id == session_id,
            SessionModel.user_id == user.id
        ).first()
        
        if not db_session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )
        
        generator = TestCaseGenerator()
        generator.current_thread_id = f"user_{user.id}_session_{session_id}"
        
        initial_state = {
            "user_initial_prompt": db_session.user_prompt,
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
            "session_id": generator.current_thread_id
        }
        
        # Update checkpoint and save initial state immediately before streaming starts
        config = {"configurable": {"thread_id": generator.current_thread_id}}
        generator.app.update_state(config, initial_state)
        db_session.state_data = initial_state
        db.commit()
        
        async def generate():
            try:
                # Stream L1 questions generation
                import asyncio
                token_count = 0
                stream_iter = generator.stream_ask_l1_questions(initial_state)
                for chunk in stream_iter:
                    if chunk.get("type") == "token":
                        token = chunk.get("token", "")
                        full_text = chunk.get("full_text", "")
                        yield f"data: {json.dumps({'type': 'token', 'token': token, 'full_text': full_text})}\n\n"
                        # Flush immediately for real-time streaming
                        await asyncio.sleep(0)
                        # Save state periodically (every 10 tokens) to prevent data loss
                        token_count += 1
                        if token_count % 10 == 0:
                            try:
                                db_session.state_data = initial_state
                                db.commit()
                            except Exception as e:
                                print(f"Error saving state during streaming: {e}")
                    elif chunk.get("type") == "complete":
                        questions = chunk.get("questions", [])
                        initial_state["l1_clarification_questions"] = questions
                        initial_state["current_level"] = "l1"
                        
                        # Update checkpoint
                        config = {"configurable": {"thread_id": generator.current_thread_id}}
                        generator.app.update_state(config, initial_state)
                        
                        # Save to database
                        db_session.state_data = initial_state
                        db.commit()
                        
                        yield f"data: {json.dumps({'type': 'complete', 'state': initial_state})}\n\n"
            except Exception as e:
                import traceback
                error_msg = str(e)
                traceback.print_exc()
                # Save state even on error to prevent data loss
                try:
                    db_session.state_data = initial_state
                    db.commit()
                except Exception as save_error:
                    print(f"Error saving state on error: {save_error}")
                yield f"data: {json.dumps({'type': 'error', 'error': error_msg})}\n\n"
        
        return StreamingResponse(generate(), media_type="text/event-stream", headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable nginx buffering
        })
    except HTTPException:
        raise
    except JWTError as e:
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start session: {str(e)}")


@app.post("/api/sessions/{session_id}/l1/answers/stream")
async def submit_l1_answers_stream(
    session_id: int,
    answers: QuestionAnswer,
    request: Request,
    db: Session = Depends(get_db)
):
    """Submit L1 clarification answers with streaming"""
    authorization = request.headers.get("Authorization")
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    try:
        token = authorization[7:]
        from jose import jwt, JWTError
        from auth import SECRET_KEY, ALGORITHM
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        
        user = db.query(User).filter(User.email == email).first()
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        
        db_session = db.query(SessionModel).filter(
            SessionModel.id == session_id,
            SessionModel.user_id == user.id
        ).first()
        
        if not db_session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )
        
        generator = TestCaseGenerator()
        generator.current_thread_id = f"user_{user.id}_session_{session_id}"
        
        state = db_session.state_data or {}
        if not state.get("user_initial_prompt"):
            state["user_initial_prompt"] = db_session.user_prompt
        if "session_id" not in state:
            state["session_id"] = generator.current_thread_id
        
        state["l1_clarification_answers"] = answers.answers
        
        config = {"configurable": {"thread_id": generator.current_thread_id}}
        generator.app.update_state(config, state)
        
        # Save state immediately before streaming starts
        db_session.state_data = state
        db.commit()
        
        async def generate():
            nonlocal state
            try:
                import asyncio
                token_count = 0
                # Stream L1 test cases generation
                stream_iter = generator.stream_generate_l1_cases(state)
                for chunk in stream_iter:
                    if chunk.get("type") == "token":
                        token = chunk.get("token", "")
                        full_text = chunk.get("full_text", "")
                        yield f"data: {json.dumps({'type': 'token', 'token': token, 'full_text': full_text})}\n\n"
                        # Flush immediately for real-time streaming
                        await asyncio.sleep(0)
                        # Save state periodically (every 10 tokens) to prevent data loss
                        token_count += 1
                        if token_count % 10 == 0:
                            try:
                                db_session.state_data = state
                                db.commit()
                            except Exception as e:
                                print(f"Error saving state during streaming: {e}")
                    elif chunk.get("type") == "complete":
                        test_cases = chunk.get("test_cases", [])
                        state["l1_test_cases"] = test_cases
                        
                        # Update global summary
                        from testcasegen import update_global_summary
                        state = update_global_summary(state)
                        
                        # Update checkpoint
                        generator.app.update_state(config, state)
                        
                        # Save to database
                        db_session.state_data = state
                        db.commit()
                        
                        yield f"data: {json.dumps({'type': 'complete', 'state': state})}\n\n"
            except Exception as e:
                import traceback
                error_msg = str(e)
                traceback.print_exc()
                # Save state even on error to prevent data loss
                try:
                    db_session.state_data = state
                    db.commit()
                except Exception as save_error:
                    print(f"Error saving state on error: {save_error}")
                yield f"data: {json.dumps({'type': 'error', 'error': error_msg})}\n\n"
        
        return StreamingResponse(generate(), media_type="text/event-stream", headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable nginx buffering
        })
    except HTTPException:
        raise
    except JWTError as e:
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to submit L1 answers: {str(e)}")


@app.post("/api/sessions/{session_id}/l1/answers", response_model=TestCaseStateResponse)
def submit_l1_answers(
    session_id: int,
    answers: QuestionAnswer,
    request: Request,
    db: Session = Depends(get_db)
):
    """Submit L1 clarification answers"""
    print(f"\n=== DEBUG: submit_l1_answers called ===")
    print(f"Session ID: {session_id}")
    print(f"Answers: {answers.answers}")
    
    # Get authorization
    authorization = request.headers.get("Authorization")
    print(f"Authorization header: {authorization[:20] if authorization else 'None'}...")
    
    if not authorization or not authorization.startswith("Bearer "):
        print("ERROR: No valid authorization header")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    try:
        token = authorization[7:]
        from jose import jwt, JWTError
        from auth import SECRET_KEY, ALGORITHM
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        print(f"Decoded email: {email}")
        
        user = db.query(User).filter(User.email == email).first()
        if not user:
            print(f"ERROR: User not found for email: {email}")
            raise HTTPException(status_code=401, detail="User not found")
        
        print(f"User found: {user.id} - {user.email}")
        
        db_session = db.query(SessionModel).filter(
            SessionModel.id == session_id,
            SessionModel.user_id == user.id
        ).first()
        
        if not db_session:
            print(f"ERROR: Session {session_id} not found for user {user.id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )
        
        print(f"Session found: {db_session.id} - {db_session.title}")
        
        generator = TestCaseGenerator()
        generator.current_thread_id = f"user_{user.id}_session_{session_id}"
        
        # Get current state
        state = db_session.state_data or {}
        
        # Ensure state has all required fields
        if not state.get("user_initial_prompt"):
            state["user_initial_prompt"] = db_session.user_prompt
        if "session_id" not in state:
            state["session_id"] = generator.current_thread_id
        
        # Update state with answers
        state["l1_clarification_answers"] = answers.answers
        
        # Update checkpoint
        config = {"configurable": {"thread_id": generator.current_thread_id}}
        generator.app.update_state(config, state)
        
        # Submit answers
        print("Calling generator.submit_l1_answers...")
        new_state = generator.submit_l1_answers(
            answers.answers,
            session_id=generator.current_thread_id
        )
        
        print(f"New state generated. Keys: {list(new_state.keys())}")
        print(f"L1 test cases count: {len(new_state.get('l1_test_cases', []))}")
        
        # Update database
        db_session.state_data = new_state
        db.commit()
        print("State updated in database")
        
        return new_state
    except HTTPException:
        raise
    except JWTError as e:
        print(f"JWT Error: {e}")
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        print(f"ERROR in submit_l1_answers: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to submit L1 answers: {str(e)}")


@app.post("/api/sessions/{session_id}/l1/select/stream")
async def select_l1_case_stream(
    session_id: int,
    request: Request,
    l1_index: Optional[int] = Query(None, alias="l1_index"),
    db: Session = Depends(get_db)
):
    """Select an L1 test case to explore with streaming"""
    if l1_index is None:
        query_params = dict(request.query_params)
        if "l1_index" in query_params:
            try:
                l1_index = int(query_params["l1_index"])
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="l1_index must be an integer"
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="l1_index is required"
            )
    
    authorization = request.headers.get("Authorization")
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    try:
        token = authorization[7:]
        from jose import jwt, JWTError
        from auth import SECRET_KEY, ALGORITHM
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        
        user = db.query(User).filter(User.email == email).first()
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        
        db_session = db.query(SessionModel).filter(
            SessionModel.id == session_id,
            SessionModel.user_id == user.id
        ).first()
        
        if not db_session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )
        
        state = db_session.state_data or {}
        if not state.get("user_initial_prompt"):
            state["user_initial_prompt"] = db_session.user_prompt
        
        l1_cases = state.get("l1_test_cases", [])
        if l1_index >= len(l1_cases) or l1_index < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid l1_index. Must be between 0 and {len(l1_cases)-1}"
            )
        
        generator = TestCaseGenerator()
        generator.current_thread_id = f"user_{user.id}_session_{session_id}"
        
        if "session_id" not in state:
            state["session_id"] = generator.current_thread_id
        
        state["selected_l1_case"] = l1_cases[l1_index]
        state["selected_l1_index"] = l1_index
        state["l2_clarification_questions"] = []
        state["l2_clarification_answers"] = {}
        state["selected_l2_case"] = None
        state["selected_l2_index"] = None
        state["l3_clarification_questions"] = []
        state["l3_clarification_answers"] = {}
        
        config = {"configurable": {"thread_id": generator.current_thread_id}}
        generator.app.update_state(config, state)
        
        # Save state immediately before streaming starts
        db_session.state_data = state
        db.commit()
        
        async def generate():
            try:
                import asyncio
                token_count = 0
                # Stream L2 questions generation
                stream_iter = generator.stream_ask_l2_questions(state)
                for chunk in stream_iter:
                    if chunk.get("type") == "token":
                        token = chunk.get("token", "")
                        full_text = chunk.get("full_text", "")
                        yield f"data: {json.dumps({'type': 'token', 'token': token, 'full_text': full_text})}\n\n"
                        # Flush immediately for real-time streaming
                        await asyncio.sleep(0)
                        # Save state periodically (every 10 tokens) to prevent data loss
                        token_count += 1
                        if token_count % 10 == 0:
                            try:
                                db_session.state_data = state
                                db.commit()
                            except Exception as e:
                                print(f"Error saving state during streaming: {e}")
                    elif chunk.get("type") == "complete":
                        questions = chunk.get("questions", [])
                        state["l2_clarification_questions"] = questions
                        state["current_level"] = "l2"
                        
                        # Update checkpoint
                        generator.app.update_state(config, state)
                        
                        # Save to database
                        db_session.state_data = state
                        db.commit()
                        
                        yield f"data: {json.dumps({'type': 'complete', 'state': state})}\n\n"
            except Exception as e:
                import traceback
                error_msg = str(e)
                traceback.print_exc()
                # Save state even on error to prevent data loss
                try:
                    db_session.state_data = state
                    db.commit()
                except Exception as save_error:
                    print(f"Error saving state on error: {save_error}")
                yield f"data: {json.dumps({'type': 'error', 'error': error_msg})}\n\n"
        
        return StreamingResponse(generate(), media_type="text/event-stream", headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable nginx buffering
        })
    except HTTPException:
        raise
    except JWTError as e:
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to select L1 case: {str(e)}")


@app.post("/api/sessions/{session_id}/l1/select")
def select_l1_case(
    session_id: int,
    request: Request,
    l1_index: Optional[int] = Query(None, alias="l1_index"),
    db: Session = Depends(get_db)
):
    """Select an L1 test case to explore"""
    print(f"\n=== DEBUG: select_l1_case called ===")
    print(f"Session ID: {session_id}")
    print(f"L1 Index from query: {l1_index}")
    
    # Try to get from query params if not provided
    if l1_index is None:
        query_params = dict(request.query_params)
        print(f"Query params: {query_params}")
        if "l1_index" in query_params:
            try:
                l1_index = int(query_params["l1_index"])
                print(f"Parsed l1_index from query: {l1_index}")
            except ValueError:
                print(f"ERROR: Could not parse l1_index: {query_params['l1_index']}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="l1_index must be an integer"
                )
        else:
            print("ERROR: l1_index not found in query params")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="l1_index is required"
            )
    
    # Get authorization
    authorization = request.headers.get("Authorization")
    print(f"Authorization header: {authorization[:20] if authorization else 'None'}...")
    
    if not authorization or not authorization.startswith("Bearer "):
        print("ERROR: No valid authorization header")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    try:
        token = authorization[7:]
        from jose import jwt, JWTError
        from auth import SECRET_KEY, ALGORITHM
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        print(f"Decoded email: {email}")
        
        user = db.query(User).filter(User.email == email).first()
        if not user:
            print(f"ERROR: User not found for email: {email}")
            raise HTTPException(status_code=401, detail="User not found")
        
        print(f"User found: {user.id} - {user.email}")
        
        db_session = db.query(SessionModel).filter(
            SessionModel.id == session_id,
            SessionModel.user_id == user.id
        ).first()
        
        if not db_session:
            print(f"ERROR: Session {session_id} not found for user {user.id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )
        
        print(f"Session found: {db_session.id} - {db_session.title}")
        
        # Get current state
        state = db_session.state_data or {}
        
        # Ensure state has all required fields
        if not state.get("user_initial_prompt"):
            state["user_initial_prompt"] = db_session.user_prompt
        
        l1_cases = state.get("l1_test_cases", [])
        print(f"L1 cases count: {len(l1_cases)}")
        
        if l1_index >= len(l1_cases) or l1_index < 0:
            print(f"ERROR: Invalid l1_index {l1_index}, valid range: 0-{len(l1_cases)-1}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid l1_index. Must be between 0 and {len(l1_cases)-1}"
            )
        
        print(f"Selecting L1 case at index {l1_index}: {l1_cases[l1_index].get('title', 'N/A')}")
        
        generator = TestCaseGenerator()
        generator.current_thread_id = f"user_{user.id}_session_{session_id}"
        
        # Ensure state has session_id
        if "session_id" not in state:
            state["session_id"] = generator.current_thread_id
        
        # Update the graph's checkpoint with the complete state from database
        config = {"configurable": {"thread_id": generator.current_thread_id}}
        print("Updating graph state with database state...")
        generator.app.update_state(config, state)
        
        # Now select L1 case - this will use the updated state
        print("Calling generator.select_l1_case...")
        new_state = generator.select_l1_case(
            l1_index,
            session_id=generator.current_thread_id
        )
        
        print(f"New state generated. Keys: {list(new_state.keys())}")
        print(f"L2 questions count: {len(new_state.get('l2_clarification_questions', []))}")
        
        # Update database
        db_session.state_data = new_state
        db.commit()
        print("State updated in database")
        
        return new_state
    except HTTPException:
        raise
    except JWTError as e:
        print(f"JWT Error: {e}")
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        print(f"ERROR in select_l1_case: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to select L1 case: {str(e)}")


@app.post("/api/sessions/{session_id}/l2/answers/stream")
async def submit_l2_answers_stream(
    session_id: int,
    answers: QuestionAnswer,
    request: Request,
    db: Session = Depends(get_db)
):
    """Submit L2 clarification answers with streaming"""
    authorization = request.headers.get("Authorization")
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    try:
        token = authorization[7:]
        from jose import jwt, JWTError
        from auth import SECRET_KEY, ALGORITHM
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        
        user = db.query(User).filter(User.email == email).first()
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        
        db_session = db.query(SessionModel).filter(
            SessionModel.id == session_id,
            SessionModel.user_id == user.id
        ).first()
        
        if not db_session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )
        
        generator = TestCaseGenerator()
        generator.current_thread_id = f"user_{user.id}_session_{session_id}"
        
        state = db_session.state_data or {}
        if not state.get("user_initial_prompt"):
            state["user_initial_prompt"] = db_session.user_prompt
        if "session_id" not in state:
            state["session_id"] = generator.current_thread_id
        
        state["l2_clarification_answers"] = answers.answers
        
        config = {"configurable": {"thread_id": generator.current_thread_id}}
        generator.app.update_state(config, state)
        
        # Save state immediately before streaming starts
        db_session.state_data = state
        db.commit()
        
        async def generate():
            nonlocal state
            try:
                import asyncio
                token_count = 0
                # Stream L2 test cases generation
                stream_iter = generator.stream_generate_l2_cases(state)
                for chunk in stream_iter:
                    if chunk.get("type") == "token":
                        token = chunk.get("token", "")
                        full_text = chunk.get("full_text", "")
                        yield f"data: {json.dumps({'type': 'token', 'token': token, 'full_text': full_text})}\n\n"
                        # Flush immediately for real-time streaming
                        await asyncio.sleep(0)
                        # Save state periodically (every 10 tokens) to prevent data loss
                        token_count += 1
                        if token_count % 10 == 0:
                            try:
                                db_session.state_data = state
                                db.commit()
                            except Exception as e:
                                print(f"Error saving state during streaming: {e}")
                    elif chunk.get("type") == "complete":
                        test_cases = chunk.get("test_cases", [])
                        existing_l2 = state.get('l2_test_cases', [])
                        selected_l1 = state.get('selected_l1_case', {})
                        existing_for_l1 = [tc for tc in existing_l2 if tc.get('parent_l1_id') == selected_l1.get('id')]
                        if not existing_for_l1:
                            state['l2_test_cases'] = existing_l2 + test_cases
                        else:
                            state['l2_test_cases'] = [tc for tc in existing_l2 if tc.get('parent_l1_id') != selected_l1.get('id')] + test_cases
                        
                        # Update global summary
                        from testcasegen import update_global_summary
                        state = update_global_summary(state)
                        
                        # Clear selection
                        state['selected_l1_case'] = None
                        state['selected_l1_index'] = None
                        state['selected_l2_case'] = None
                        state['selected_l2_index'] = None
                        state['l2_clarification_questions'] = []
                        state['l2_clarification_answers'] = {}
                        state['l3_clarification_questions'] = []
                        state['l3_clarification_answers'] = {}
                        
                        # Update checkpoint
                        generator.app.update_state(config, state)
                        
                        # Save to database
                        db_session.state_data = state
                        db.commit()
                        
                        yield f"data: {json.dumps({'type': 'complete', 'state': state})}\n\n"
            except Exception as e:
                import traceback
                error_msg = str(e)
                traceback.print_exc()
                # Save state even on error to prevent data loss
                try:
                    db_session.state_data = state
                    db.commit()
                except Exception as save_error:
                    print(f"Error saving state on error: {save_error}")
                yield f"data: {json.dumps({'type': 'error', 'error': error_msg})}\n\n"
        
        return StreamingResponse(generate(), media_type="text/event-stream", headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable nginx buffering
        })
    except HTTPException:
        raise
    except JWTError as e:
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to submit L2 answers: {str(e)}")


@app.post("/api/sessions/{session_id}/l2/answers", response_model=TestCaseStateResponse)
def submit_l2_answers(
    session_id: int,
    answers: QuestionAnswer,
    request: Request,
    db: Session = Depends(get_db)
):
    """Submit L2 clarification answers"""
    print(f"\n=== DEBUG: submit_l2_answers called ===")
    print(f"Session ID: {session_id}")
    print(f"Answers: {answers.answers}")
    
    # Get authorization
    authorization = request.headers.get("Authorization")
    print(f"Authorization header: {authorization[:20] if authorization else 'None'}...")
    
    if not authorization or not authorization.startswith("Bearer "):
        print("ERROR: No valid authorization header")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    try:
        token = authorization[7:]
        from jose import jwt, JWTError
        from auth import SECRET_KEY, ALGORITHM
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        print(f"Decoded email: {email}")
        
        user = db.query(User).filter(User.email == email).first()
        if not user:
            print(f"ERROR: User not found for email: {email}")
            raise HTTPException(status_code=401, detail="User not found")
        
        print(f"User found: {user.id} - {user.email}")
        
        db_session = db.query(SessionModel).filter(
            SessionModel.id == session_id,
            SessionModel.user_id == user.id
        ).first()
        
        if not db_session:
            print(f"ERROR: Session {session_id} not found for user {user.id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )
        
        print(f"Session found: {db_session.id} - {db_session.title}")
        
        generator = TestCaseGenerator()
        generator.current_thread_id = f"user_{user.id}_session_{session_id}"
        
        # Get current state
        state = db_session.state_data or {}
        
        # Ensure state has all required fields
        if not state.get("user_initial_prompt"):
            state["user_initial_prompt"] = db_session.user_prompt
        if "session_id" not in state:
            state["session_id"] = generator.current_thread_id
        
        # Update state with answers
        state["l2_clarification_answers"] = answers.answers
        
        # Update checkpoint
        config = {"configurable": {"thread_id": generator.current_thread_id}}
        generator.app.update_state(config, state)
        
        # Submit answers
        print("Calling generator.submit_l2_answers...")
        new_state = generator.submit_l2_answers(
            answers.answers,
            session_id=generator.current_thread_id
        )
        
        print(f"New state generated. Keys: {list(new_state.keys())}")
        print(f"L2 test cases count: {len(new_state.get('l2_test_cases', []))}")
        
        # Update database
        db_session.state_data = new_state
        db.commit()
        print("State updated in database")
        
        return new_state
    except HTTPException:
        raise
    except JWTError as e:
        print(f"JWT Error: {e}")
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        print(f"ERROR in submit_l2_answers: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to submit L2 answers: {str(e)}")


@app.post("/api/sessions/{session_id}/l2/select/stream")
async def select_l2_case_stream(
    session_id: int,
    request: Request,
    l2_index: Optional[int] = Query(None, alias="l2_index"),
    db: Session = Depends(get_db)
):
    """Select an L2 test case to explore with streaming"""
    if l2_index is None:
        query_params = dict(request.query_params)
        if "l2_index" in query_params:
            try:
                l2_index = int(query_params["l2_index"])
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="l2_index must be an integer"
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="l2_index is required"
            )
    
    authorization = request.headers.get("Authorization")
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    try:
        token = authorization[7:]
        from jose import jwt, JWTError
        from auth import SECRET_KEY, ALGORITHM
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        
        user = db.query(User).filter(User.email == email).first()
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        
        db_session = db.query(SessionModel).filter(
            SessionModel.id == session_id,
            SessionModel.user_id == user.id
        ).first()
        
        if not db_session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )
        
        state = db_session.state_data or {}
        if not state.get("user_initial_prompt"):
            state["user_initial_prompt"] = db_session.user_prompt
        
        l2_cases = state.get("l2_test_cases", [])
        if l2_index >= len(l2_cases) or l2_index < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid l2_index. Must be between 0 and {len(l2_cases)-1}"
            )
        
        generator = TestCaseGenerator()
        generator.current_thread_id = f"user_{user.id}_session_{session_id}"
        
        if "session_id" not in state:
            state["session_id"] = generator.current_thread_id
        
        state["selected_l2_case"] = l2_cases[l2_index]
        state["selected_l2_index"] = l2_index
        state["l3_clarification_questions"] = []
        state["l3_clarification_answers"] = {}
        
        config = {"configurable": {"thread_id": generator.current_thread_id}}
        generator.app.update_state(config, state)
        
        # Save state immediately before streaming starts
        db_session.state_data = state
        db.commit()
        
        async def generate():
            try:
                import asyncio
                token_count = 0
                # Stream L3 questions generation
                stream_iter = generator.stream_ask_l3_questions(state)
                for chunk in stream_iter:
                    if chunk.get("type") == "token":
                        token = chunk.get("token", "")
                        full_text = chunk.get("full_text", "")
                        yield f"data: {json.dumps({'type': 'token', 'token': token, 'full_text': full_text})}\n\n"
                        # Flush immediately for real-time streaming
                        await asyncio.sleep(0)
                        # Save state periodically (every 10 tokens) to prevent data loss
                        token_count += 1
                        if token_count % 10 == 0:
                            try:
                                db_session.state_data = state
                                db.commit()
                            except Exception as e:
                                print(f"Error saving state during streaming: {e}")
                    elif chunk.get("type") == "complete":
                        questions = chunk.get("questions", [])
                        state["l3_clarification_questions"] = questions
                        state["current_level"] = "l3"
                        
                        # Update checkpoint
                        generator.app.update_state(config, state)
                        
                        # Save to database
                        db_session.state_data = state
                        db.commit()
                        
                        yield f"data: {json.dumps({'type': 'complete', 'state': state})}\n\n"
            except Exception as e:
                import traceback
                error_msg = str(e)
                traceback.print_exc()
                # Save state even on error to prevent data loss
                try:
                    db_session.state_data = state
                    db.commit()
                except Exception as save_error:
                    print(f"Error saving state on error: {save_error}")
                yield f"data: {json.dumps({'type': 'error', 'error': error_msg})}\n\n"
        
        return StreamingResponse(generate(), media_type="text/event-stream", headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable nginx buffering
        })
    except HTTPException:
        raise
    except JWTError as e:
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to select L2 case: {str(e)}")


@app.post("/api/sessions/{session_id}/l2/select")
def select_l2_case(
    session_id: int,
    request: Request,
    l2_index: Optional[int] = Query(None, alias="l2_index"),
    db: Session = Depends(get_db)
):
    """Select an L2 test case to explore"""
    print(f"\n=== DEBUG: select_l2_case called ===")
    print(f"Session ID: {session_id}")
    print(f"L2 Index from query: {l2_index}")
    
    # Try to get from query params if not provided
    if l2_index is None:
        query_params = dict(request.query_params)
        print(f"Query params: {query_params}")
        if "l2_index" in query_params:
            try:
                l2_index = int(query_params["l2_index"])
                print(f"Parsed l2_index from query: {l2_index}")
            except ValueError:
                print(f"ERROR: Could not parse l2_index: {query_params['l2_index']}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="l2_index must be an integer"
                )
        else:
            print("ERROR: l2_index not found in query params")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="l2_index is required"
            )
    
    # Get authorization
    authorization = request.headers.get("Authorization")
    print(f"Authorization header: {authorization[:20] if authorization else 'None'}...")
    
    if not authorization or not authorization.startswith("Bearer "):
        print("ERROR: No valid authorization header")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    try:
        token = authorization[7:]
        from jose import jwt, JWTError
        from auth import SECRET_KEY, ALGORITHM
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        print(f"Decoded email: {email}")
        
        user = db.query(User).filter(User.email == email).first()
        if not user:
            print(f"ERROR: User not found for email: {email}")
            raise HTTPException(status_code=401, detail="User not found")
        
        print(f"User found: {user.id} - {user.email}")
        
        db_session = db.query(SessionModel).filter(
            SessionModel.id == session_id,
            SessionModel.user_id == user.id
        ).first()
        
        if not db_session:
            print(f"ERROR: Session {session_id} not found for user {user.id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )
        
        print(f"Session found: {db_session.id} - {db_session.title}")
        
        # Get current state
        state = db_session.state_data or {}
        l2_cases = state.get("l2_test_cases", [])
        print(f"L2 cases count: {len(l2_cases)}")
        
        if l2_index >= len(l2_cases) or l2_index < 0:
            print(f"ERROR: Invalid l2_index {l2_index}, valid range: 0-{len(l2_cases)-1}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid l2_index. Must be between 0 and {len(l2_cases)-1}"
            )
        
        print(f"Selecting L2 case at index {l2_index}: {l2_cases[l2_index].get('title', 'N/A')}")
        
        generator = TestCaseGenerator()
        generator.current_thread_id = f"user_{user.id}_session_{session_id}"
        
        # Ensure state has all required fields
        if not state.get("user_initial_prompt"):
            state["user_initial_prompt"] = db_session.user_prompt
        if "session_id" not in state:
            state["session_id"] = generator.current_thread_id
        
        # Update the graph's checkpoint with the complete state
        config = {"configurable": {"thread_id": generator.current_thread_id}}
        print("Updating graph state with database state...")
        generator.app.update_state(config, state)
        
        # Now select L2 case
        print("Calling generator.select_l2_case...")
        new_state = generator.select_l2_case(
            l2_index,
            session_id=generator.current_thread_id
        )
        
        print(f"New state generated. Keys: {list(new_state.keys())}")
        print(f"L3 questions count: {len(new_state.get('l3_clarification_questions', []))}")
        
        # Update database
        db_session.state_data = new_state
        db.commit()
        print("State updated in database")
        
        return new_state
    except HTTPException:
        raise
    except JWTError as e:
        print(f"JWT Error: {e}")
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        print(f"ERROR in select_l2_case: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to select L2 case: {str(e)}")


@app.post("/api/sessions/{session_id}/l3/answers/stream")
async def submit_l3_answers_stream(
    session_id: int,
    answers: QuestionAnswer,
    request: Request,
    db: Session = Depends(get_db)
):
    """Submit L3 clarification answers with streaming"""
    authorization = request.headers.get("Authorization")
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    try:
        token = authorization[7:]
        from jose import jwt, JWTError
        from auth import SECRET_KEY, ALGORITHM
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        
        user = db.query(User).filter(User.email == email).first()
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        
        db_session = db.query(SessionModel).filter(
            SessionModel.id == session_id,
            SessionModel.user_id == user.id
        ).first()
        
        if not db_session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )
        
        generator = TestCaseGenerator()
        generator.current_thread_id = f"user_{user.id}_session_{session_id}"
        
        state = db_session.state_data or {}
        if not state.get("user_initial_prompt"):
            state["user_initial_prompt"] = db_session.user_prompt
        if "session_id" not in state:
            state["session_id"] = generator.current_thread_id
        
        state["l3_clarification_answers"] = answers.answers
        
        config = {"configurable": {"thread_id": generator.current_thread_id}}
        generator.app.update_state(config, state)
        
        # Save state immediately before streaming starts
        db_session.state_data = state
        db.commit()
        
        async def generate():
            nonlocal state
            try:
                import asyncio
                token_count = 0
                # Stream L3 test cases generation
                stream_iter = generator.stream_generate_l3_cases(state)
                for chunk in stream_iter:
                    if chunk.get("type") == "token":
                        token = chunk.get("token", "")
                        full_text = chunk.get("full_text", "")
                        yield f"data: {json.dumps({'type': 'token', 'token': token, 'full_text': full_text})}\n\n"
                        # Flush immediately for real-time streaming
                        await asyncio.sleep(0)
                        # Save state periodically (every 10 tokens) to prevent data loss
                        token_count += 1
                        if token_count % 10 == 0:
                            try:
                                db_session.state_data = state
                                db.commit()
                            except Exception as e:
                                print(f"Error saving state during streaming: {e}")
                    elif chunk.get("type") == "complete":
                        test_cases = chunk.get("test_cases", [])
                        existing_l3 = state.get('l3_test_cases', [])
                        selected_l2 = state.get('selected_l2_case', {})
                        existing_for_l2 = [tc for tc in existing_l3 if tc.get('parent_l2_id') == selected_l2.get('id')]
                        if not existing_for_l2:
                            state['l3_test_cases'] = existing_l3 + test_cases
                        else:
                            state['l3_test_cases'] = [tc for tc in existing_l3 if tc.get('parent_l2_id') != selected_l2.get('id')] + test_cases
                        
                        # Update global summary
                        from testcasegen import update_global_summary
                        state = update_global_summary(state)
                        
                        # Build tree
                        from testcasegen import build_tree
                        state = build_tree(state)
                        
                        # Clear selection
                        state['selected_l2_case'] = None
                        state['selected_l2_index'] = None
                        state['l3_clarification_questions'] = []
                        state['l3_clarification_answers'] = {}
                        
                        # Update checkpoint
                        generator.app.update_state(config, state)
                        
                        # Save to database
                        db_session.state_data = state
                        db.commit()
                        
                        yield f"data: {json.dumps({'type': 'complete', 'state': state})}\n\n"
            except Exception as e:
                import traceback
                error_msg = str(e)
                traceback.print_exc()
                yield f"data: {json.dumps({'type': 'error', 'error': error_msg})}\n\n"
        
        return StreamingResponse(generate(), media_type="text/event-stream", headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable nginx buffering
        })
    except HTTPException:
        raise
    except JWTError as e:
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to submit L3 answers: {str(e)}")


@app.post("/api/sessions/{session_id}/l3/answers", response_model=TestCaseStateResponse)
def submit_l3_answers(
    session_id: int,
    answers: QuestionAnswer,
    request: Request,
    db: Session = Depends(get_db)
):
    """Submit L3 clarification answers"""
    print(f"\n=== DEBUG: submit_l3_answers called ===")
    print(f"Session ID: {session_id}")
    print(f"Answers: {answers.answers}")
    
    # Get authorization
    authorization = request.headers.get("Authorization")
    print(f"Authorization header: {authorization[:20] if authorization else 'None'}...")
    
    if not authorization or not authorization.startswith("Bearer "):
        print("ERROR: No valid authorization header")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    try:
        token = authorization[7:]
        from jose import jwt, JWTError
        from auth import SECRET_KEY, ALGORITHM
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        print(f"Decoded email: {email}")
        
        user = db.query(User).filter(User.email == email).first()
        if not user:
            print(f"ERROR: User not found for email: {email}")
            raise HTTPException(status_code=401, detail="User not found")
        
        print(f"User found: {user.id} - {user.email}")
        
        db_session = db.query(SessionModel).filter(
            SessionModel.id == session_id,
            SessionModel.user_id == user.id
        ).first()
        
        if not db_session:
            print(f"ERROR: Session {session_id} not found for user {user.id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )
        
        print(f"Session found: {db_session.id} - {db_session.title}")
        
        generator = TestCaseGenerator()
        generator.current_thread_id = f"user_{user.id}_session_{session_id}"
        
        # Get current state
        state = db_session.state_data or {}
        
        # Ensure state has all required fields
        if not state.get("user_initial_prompt"):
            state["user_initial_prompt"] = db_session.user_prompt
        if "session_id" not in state:
            state["session_id"] = generator.current_thread_id
        
        # Update state with answers
        state["l3_clarification_answers"] = answers.answers
        
        # Update checkpoint
        config = {"configurable": {"thread_id": generator.current_thread_id}}
        generator.app.update_state(config, state)
        
        # Submit answers
        print("Calling generator.submit_l3_answers...")
        new_state = generator.submit_l3_answers(
            answers.answers,
            session_id=generator.current_thread_id
        )
        
        print(f"New state generated. Keys: {list(new_state.keys())}")
        print(f"L3 test cases count: {len(new_state.get('l3_test_cases', []))}")
        
        # Update database
        db_session.state_data = new_state
        db.commit()
        print("State updated in database")
        
        return new_state
    except HTTPException:
        raise
    except JWTError as e:
        print(f"JWT Error: {e}")
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        print(f"ERROR in submit_l3_answers: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to submit L3 answers: {str(e)}")


@app.get("/api/sessions/{session_id}/state")
def get_session_state(
    session_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """Get current state of a session"""
    print(f"\n=== DEBUG: get_session_state called ===")
    print(f"Session ID: {session_id}")
    
    # Get authorization
    authorization = request.headers.get("Authorization")
    print(f"Authorization header: {authorization[:20] if authorization else 'None'}...")
    
    if not authorization or not authorization.startswith("Bearer "):
        print("ERROR: No valid authorization header")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    try:
        token = authorization[7:]
        from jose import jwt, JWTError
        from auth import SECRET_KEY, ALGORITHM
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        print(f"Decoded email: {email}")
        
        user = db.query(User).filter(User.email == email).first()
        if not user:
            print(f"ERROR: User not found for email: {email}")
            raise HTTPException(status_code=401, detail="User not found")
        
        print(f"User found: {user.id} - {user.email}")
        
        db_session = db.query(SessionModel).filter(
            SessionModel.id == session_id,
            SessionModel.user_id == user.id
        ).first()
        
        if not db_session:
            print(f"ERROR: Session {session_id} not found for user {user.id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )
        
        print(f"Session found: {db_session.id} - {db_session.title}")
        state_data = db_session.state_data or {}
        print(f"State data keys: {list(state_data.keys()) if state_data else 'Empty'}")
        print(f"State data type: {type(state_data)}")
        
        if state_data:
            print(f"Has l1_questions: {bool(state_data.get('l1_clarification_questions'))}")
            print(f"Has l1_cases: {bool(state_data.get('l1_test_cases'))}")
        
        return state_data
    except HTTPException:
        raise
    except JWTError as e:
        print(f"JWT Error: {e}")
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        print(f"ERROR in get_session_state: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to get session state: {str(e)}")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

