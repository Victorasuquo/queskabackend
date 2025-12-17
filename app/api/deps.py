"""
Queska Backend - API Dependencies
FastAPI dependencies for authentication and authorization
"""

from typing import Any, Dict, Optional, Tuple

from beanie import PydanticObjectId
from fastapi import Depends, Header, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError

from app.core.config import settings
from app.core.exceptions import (
    AuthenticationError,
    ForbiddenError,
    NotFoundError,
)
from app.core.security import verify_token, TokenData
from app.models.user import User
from app.models.vendor import Vendor
from app.models.agent import Agent
from app.models.admin import Admin
from app.repositories.user_repository import user_repository
from app.repositories.vendor_repository import vendor_repository
from app.repositories.agent_repository import agent_repository
from app.repositories.admin_repository import admin_repository


# OAuth2 scheme for JWT
security = HTTPBearer(auto_error=False)


# === Token Dependencies ===

async def get_token_data(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> TokenData:
    """
    Extract and validate token data from Authorization header.
    Raises 401 if token is invalid or missing.
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        token_data = verify_token(credentials.credentials, "access")
        if not token_data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return token_data
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_optional_token_data(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Optional[TokenData]:
    """
    Extract token data if present, return None otherwise.
    Used for endpoints that work both authenticated and unauthenticated.
    """
    if not credentials:
        return None
    
    try:
        return verify_token(credentials.credentials, "access")
    except JWTError:
        return None


# === User Dependencies ===

async def get_current_user(
    token_data: TokenData = Depends(get_token_data)
) -> User:
    """
    Get the current authenticated user.
    Validates that the token belongs to a regular user.
    """
    if token_data.user_type != "user":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User access required"
        )
    
    user = await user_repository.get_by_id(token_data.user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if user.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account has been deleted"
        )
    
    return user


async def get_current_active_user(
    user: User = Depends(get_current_user)
) -> User:
    """
    Get the current authenticated active user.
    Raises 403 if account is not active.
    """
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is not active"
        )
    return user


async def get_current_user_optional(
    token_data: Optional[TokenData] = Depends(get_optional_token_data)
) -> Optional[User]:
    """
    Get the current user if authenticated, None otherwise.
    Used for endpoints that work both authenticated and unauthenticated.
    """
    if not token_data:
        return None
    
    if token_data.user_type != "user":
        return None
    
    user = await user_repository.get_by_id(token_data.user_id)
    if not user or user.is_deleted:
        return None
    
    return user


# === Vendor Dependencies ===

async def get_current_vendor(
    token_data: TokenData = Depends(get_token_data)
) -> Vendor:
    """
    Get the current authenticated vendor.
    """
    if token_data.user_type != "vendor":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Vendor access required"
        )
    
    vendor = await vendor_repository.get_by_id(token_data.user_id)
    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vendor not found"
        )
    
    if vendor.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Vendor account has been deleted"
        )
    
    return vendor


async def get_current_active_vendor(
    vendor: Vendor = Depends(get_current_vendor)
) -> Vendor:
    """
    Get the current authenticated active vendor.
    """
    if not vendor.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Vendor account is not active"
        )
    return vendor


async def get_current_verified_vendor(
    vendor: Vendor = Depends(get_current_active_vendor)
) -> Vendor:
    """
    Get the current authenticated verified vendor.
    """
    if not vendor.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Vendor account is not verified"
        )
    return vendor


# === Agent Dependencies ===

async def get_current_agent(
    token_data: TokenData = Depends(get_token_data)
) -> Agent:
    """
    Get the current authenticated agent.
    """
    if token_data.user_type != "agent":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Agent access required"
        )
    
    agent = await agent_repository.get_by_id(token_data.user_id)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )
    
    if agent.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Agent account has been deleted"
        )
    
    return agent


async def get_current_active_agent(
    agent: Agent = Depends(get_current_agent)
) -> Agent:
    """
    Get the current authenticated active agent.
    """
    if not agent.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Agent account is not active"
        )
    return agent


async def get_current_verified_agent(
    agent: Agent = Depends(get_current_active_agent)
) -> Agent:
    """
    Get the current authenticated verified agent.
    """
    if not agent.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Agent account is not verified"
        )
    return agent


# === Admin Dependencies ===

async def get_current_admin(
    token_data: TokenData = Depends(get_token_data)
) -> Admin:
    """
    Get the current authenticated admin.
    """
    if token_data.user_type != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    admin = await admin_repository.get_by_id(token_data.user_id)
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Admin not found"
        )
    
    return admin


async def get_super_admin(
    admin: Admin = Depends(get_current_admin)
) -> Admin:
    """
    Get the current super admin.
    """
    if not admin.is_super_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super admin access required"
        )
    return admin


# === Permission Checks ===

def require_permission(permission: str):
    """
    Dependency factory for permission-based access control.
    
    Usage:
        @router.get("/admin/users")
        async def list_users(
            admin: Admin = Depends(require_permission("manage_users"))
        ):
            ...
    """
    async def permission_checker(
        admin: Admin = Depends(get_current_admin)
    ) -> Admin:
        if admin.is_super_admin:
            return admin
        
        if permission not in admin.permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission '{permission}' required"
            )
        return admin
    
    return permission_checker


# === Pagination Dependencies ===

def get_pagination_params(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
) -> Tuple[int, int]:
    """
    Get pagination parameters as a tuple of (skip, limit).
    """
    skip = (page - 1) * limit
    return skip, limit


def get_sort_params(
    sort_by: str = Query("created_at", description="Field to sort by"),
    sort_order: str = Query("desc", enum=["asc", "desc"], description="Sort order"),
) -> Tuple[str, int]:
    """
    Get sorting parameters as a tuple of (field, direction).
    """
    direction = -1 if sort_order == "desc" else 1
    return sort_by, direction


# === Common Headers ===

async def get_client_info(
    x_forwarded_for: Optional[str] = Header(None, alias="X-Forwarded-For"),
    user_agent: Optional[str] = Header(None, alias="User-Agent"),
) -> Dict[str, Optional[str]]:
    """
    Extract client information from request headers.
    """
    ip_address = None
    if x_forwarded_for:
        ip_address = x_forwarded_for.split(",")[0].strip()
    
    return {
        "ip_address": ip_address,
        "user_agent": user_agent
    }
