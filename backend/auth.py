"""
Authentication utilities
"""
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from database import SessionLocal
from models import User

# JWT settings
SECRET_KEY = "your-secret-key-change-this-in-production"  # Change this!
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 24 * 60  # 24 hours for development (change to 30 for production)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    try:
        # Convert password to bytes
        password_bytes = plain_password.encode('utf-8')
        # Truncate to 72 bytes if necessary (bcrypt limit)
        if len(password_bytes) > 72:
            password_bytes = password_bytes[:72]
        
        # Verify password
        return bcrypt.checkpw(password_bytes, hashed_password.encode('utf-8'))
    except Exception as e:
        print(f"Password verification error: {e}")
        return False


def get_password_hash(password: str) -> str:
    """Hash a password - handles bcrypt 72-byte limit by truncating"""
    # Convert password to bytes
    password_bytes = password.encode('utf-8')
    
    # Truncate to 72 bytes if necessary (bcrypt limit)
    if len(password_bytes) > 72:
        password_bytes = password_bytes[:72]
    
    # Generate salt and hash
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password_bytes, salt)
    
    # Return as string
    return hashed.decode('utf-8')


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create a JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        # Use the configured expiration time
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(SessionLocal)):
    """Get the current authenticated user"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    if not token:
        raise credentials_exception
    
    try:
        # Remove 'Bearer ' prefix if present
        if token.startswith('Bearer '):
            token = token[7:]
        
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError as e:
        print(f"JWT decode error: {e}")
        raise credentials_exception
    except Exception as e:
        print(f"Token validation error: {e}")
        raise credentials_exception
    
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise credentials_exception
    
    return user

