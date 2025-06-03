"""Authentication API endpoints"""

from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from loguru import logger
from pydantic import BaseModel

from ..config import settings
from ..security.auth import AuthenticationManager

router = APIRouter()
security = HTTPBearer()


class LoginRequest(BaseModel):
    """Login request model"""
    username: str
    password: str


class TokenResponse(BaseModel):
    """Token response model"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    refresh_token: Optional[str] = None


class UserInfo(BaseModel):
    """User information model"""
    id: str
    username: str
    email: str
    roles: list[str]
    permissions: list[str]


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> UserInfo:
    """Get current authenticated user"""
    token = credentials.credentials
    
    try:
        # Decode JWT token
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm]
        )
        
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials"
            )
            
        # Get user info (mock for now)
        user = UserInfo(
            id=user_id,
            username=payload.get("username", "unknown"),
            email=payload.get("email", ""),
            roles=payload.get("roles", ["user"]),
            permissions=payload.get("permissions", [])
        )
        
        return user
        
    except JWTError as e:
        logger.error(f"JWT validation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest) -> TokenResponse:
    """User login endpoint"""
    # TODO: Implement actual authentication
    # This is a mock implementation
    
    if request.username == "demo" and request.password == "demo123":
        # Create access token
        access_token_expires = timedelta(hours=settings.jwt_expiration_hours)
        access_token = create_access_token(
            data={
                "sub": "demo_user_id",
                "username": request.username,
                "email": "demo@example.com",
                "roles": ["user"],
                "permissions": ["documents:read", "search:execute"]
            },
            expires_delta=access_token_expires
        )
        
        return TokenResponse(
            access_token=access_token,
            expires_in=settings.jwt_expiration_hours * 3600
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    current_user: UserInfo = Depends(get_current_user)
) -> TokenResponse:
    """Refresh access token"""
    # Create new access token
    access_token_expires = timedelta(hours=settings.jwt_expiration_hours)
    access_token = create_access_token(
        data={
            "sub": current_user.id,
            "username": current_user.username,
            "email": current_user.email,
            "roles": current_user.roles,
            "permissions": current_user.permissions
        },
        expires_delta=access_token_expires
    )
    
    return TokenResponse(
        access_token=access_token,
        expires_in=settings.jwt_expiration_hours * 3600
    )


@router.get("/me", response_model=UserInfo)
async def get_me(
    current_user: UserInfo = Depends(get_current_user)
) -> UserInfo:
    """Get current user information"""
    return current_user


@router.post("/logout")
async def logout(
    current_user: UserInfo = Depends(get_current_user)
) -> Dict[str, str]:
    """User logout endpoint"""
    # TODO: Implement token blacklisting
    logger.info(f"User {current_user.username} logged out")
    
    return {
        "message": "Successfully logged out",
        "timestamp": datetime.utcnow().isoformat()
    }


def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None
) -> str:
    """Create JWT access token"""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=24)
        
    to_encode.update({"exp": expire})
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm
    )
    
    return encoded_jwt