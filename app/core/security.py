"""
Queska Backend - Security Module
JWT authentication, password hashing, and security utilities
"""

from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Union

from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from loguru import logger

from app.core.config import settings


# Password hashing context
pwd_context = CryptContext(
    schemes=["bcrypt", "argon2"],
    deprecated="auto",
    bcrypt__rounds=12
)


class TokenPayload(BaseModel):
    """JWT token payload structure"""
    sub: str  # Subject (user ID)
    type: str  # Token type (access, refresh, verification, reset)
    user_type: str  # User type (user, admin, vendor, agent, consultant)
    exp: datetime  # Expiration time
    iat: datetime  # Issued at time
    jti: Optional[str] = None  # JWT ID for token revocation


class TokenData(BaseModel):
    """Decoded token data"""
    user_id: str
    user_type: str
    token_type: str


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against a hashed password
    
    Args:
        plain_password: The plain text password
        hashed_password: The hashed password to compare against
        
    Returns:
        True if password matches, False otherwise
    """
    return pwd_context.verify(plain_password, hashed_password)


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt
    
    Args:
        password: Plain text password to hash
        
    Returns:
        Hashed password string
    """
    return pwd_context.hash(password)


def create_access_token(
    subject: Union[str, Any],
    user_type: str,
    expires_delta: Optional[timedelta] = None,
    additional_claims: Optional[Dict[str, Any]] = None
) -> str:
    """
    Create a JWT access token
    
    Args:
        subject: The subject of the token (usually user ID)
        user_type: Type of user (user, admin, vendor, agent, consultant)
        expires_delta: Optional custom expiration time
        additional_claims: Optional additional claims to include
        
    Returns:
        Encoded JWT token string
    """
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode = {
        "sub": str(subject),
        "type": "access",
        "user_type": user_type,
        "exp": expire,
        "iat": datetime.utcnow()
    }
    
    if additional_claims:
        to_encode.update(additional_claims)
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )
    
    return encoded_jwt


def create_refresh_token(
    subject: Union[str, Any],
    user_type: str,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT refresh token
    
    Args:
        subject: The subject of the token (usually user ID)
        user_type: Type of user
        expires_delta: Optional custom expiration time
        
    Returns:
        Encoded JWT refresh token string
    """
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    
    to_encode = {
        "sub": str(subject),
        "type": "refresh",
        "user_type": user_type,
        "exp": expire,
        "iat": datetime.utcnow()
    }
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )
    
    return encoded_jwt


def create_verification_token(
    subject: Union[str, Any],
    user_type: str,
    purpose: str = "email_verification"
) -> str:
    """
    Create a verification token (email verification, password reset, etc.)
    
    Args:
        subject: The subject of the token
        user_type: Type of user
        purpose: Purpose of the token
        
    Returns:
        Encoded JWT token string
    """
    expire = datetime.utcnow() + timedelta(hours=settings.VERIFICATION_TOKEN_EXPIRE_HOURS)
    
    to_encode = {
        "sub": str(subject),
        "type": "verification",
        "user_type": user_type,
        "purpose": purpose,
        "exp": expire,
        "iat": datetime.utcnow()
    }
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )
    
    return encoded_jwt


def create_password_reset_token(
    subject: Union[str, Any],
    user_type: str
) -> str:
    """
    Create a password reset token
    
    Args:
        subject: The subject of the token (user email or ID)
        user_type: Type of user
        
    Returns:
        Encoded JWT token string
    """
    expire = datetime.utcnow() + timedelta(hours=settings.PASSWORD_RESET_TOKEN_EXPIRE_HOURS)
    
    to_encode = {
        "sub": str(subject),
        "type": "password_reset",
        "user_type": user_type,
        "exp": expire,
        "iat": datetime.utcnow()
    }
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )
    
    return encoded_jwt


def decode_token(token: str) -> Optional[TokenPayload]:
    """
    Decode and validate a JWT token
    
    Args:
        token: The JWT token string
        
    Returns:
        TokenPayload if valid, None otherwise
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        
        return TokenPayload(
            sub=payload.get("sub"),
            type=payload.get("type"),
            user_type=payload.get("user_type"),
            exp=datetime.fromtimestamp(payload.get("exp")),
            iat=datetime.fromtimestamp(payload.get("iat")),
            jti=payload.get("jti")
        )
        
    except JWTError as e:
        logger.warning(f"JWT decode error: {e}")
        return None


def verify_token(token: str, expected_type: str = "access") -> Optional[TokenData]:
    """
    Verify a JWT token and return token data
    
    Args:
        token: The JWT token string
        expected_type: Expected token type (access, refresh, verification)
        
    Returns:
        TokenData if valid, None otherwise
    """
    payload = decode_token(token)
    
    if not payload:
        return None
    
    if payload.type != expected_type:
        logger.warning(f"Token type mismatch: expected {expected_type}, got {payload.type}")
        return None
    
    if payload.exp < datetime.utcnow():
        logger.warning("Token has expired")
        return None
    
    return TokenData(
        user_id=payload.sub,
        user_type=payload.user_type,
        token_type=payload.type
    )


def generate_api_key() -> str:
    """
    Generate a secure API key
    
    Returns:
        Random API key string
    """
    import secrets
    return f"qsk_{secrets.token_urlsafe(32)}"


def hash_api_key(api_key: str) -> str:
    """
    Hash an API key for storage
    
    Args:
        api_key: Plain API key
        
    Returns:
        Hashed API key
    """
    import hashlib
    return hashlib.sha256(api_key.encode()).hexdigest()


def verify_api_key(plain_key: str, hashed_key: str) -> bool:
    """
    Verify an API key against its hash
    
    Args:
        plain_key: Plain API key
        hashed_key: Stored hash
        
    Returns:
        True if matches, False otherwise
    """
    return hash_api_key(plain_key) == hashed_key

