"""
Queska Backend - Authentication API Endpoints
Google OAuth, token management, and authentication routes
"""

from typing import Any, Dict, Optional
from urllib.parse import urlencode

from fastapi import APIRouter, HTTPException, Query, Request, status
from fastapi.responses import RedirectResponse
from loguru import logger

from app.core.config import settings
from app.core.exceptions import (
    AuthenticationError,
    InvalidCredentialsError,
    ValidationError,
)
from app.schemas.user import (
    GoogleAuthRequest,
    OAuthResponse,
)
from app.services.user_service import user_service


router = APIRouter()


# ==========================================
# GOOGLE OAUTH ENDPOINTS
# ==========================================

# Google OAuth URLs
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"


@router.get(
    "/google/login",
    summary="Initiate Google OAuth login",
    description="Redirects user to Google OAuth consent screen"
)
async def google_login(
    redirect_uri: Optional[str] = Query(
        None,
        description="Optional custom redirect URI after auth"
    )
):
    """
    Initiate Google OAuth flow.
    
    Redirects the user to Google's OAuth consent screen.
    After consent, Google redirects back to our callback endpoint.
    """
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=503,
            detail="Google OAuth is not configured"
        )
    
    # Build Google OAuth URL
    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "consent",
    }
    
    # Store custom redirect URI in state if provided
    if redirect_uri:
        params["state"] = redirect_uri
    
    auth_url = f"{GOOGLE_AUTH_URL}?{urlencode(params)}"
    
    return {"auth_url": auth_url}


@router.get(
    "/google/callback",
    summary="Google OAuth callback",
    description="Handles the callback from Google OAuth"
)
async def google_callback(
    code: str = Query(..., description="Authorization code from Google"),
    state: Optional[str] = Query(None, description="Optional state/redirect URI"),
    request: Request = None
):
    """
    Handle Google OAuth callback.
    
    Exchanges the authorization code for tokens and creates/logs in the user.
    """
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        raise HTTPException(
            status_code=503,
            detail="Google OAuth is not configured"
        )
    
    try:
        result = await user_service.google_oauth_callback(
            code=code,
            ip_address=request.client.host if request and request.client else None,
            user_agent=request.headers.get("user-agent") if request else None
        )
        
        # If state contains a redirect URI, redirect with tokens as query params
        if state and state.startswith("http"):
            redirect_url = f"{state}?access_token={result['access_token']}&refresh_token={result['refresh_token']}"
            return RedirectResponse(url=redirect_url)
        
        return result
        
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except AuthenticationError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        logger.error(f"Google OAuth callback error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to complete Google authentication"
        )


@router.post(
    "/google/token",
    response_model=Dict[str, Any],
    summary="Google OAuth with ID token",
    description="Authenticate using a Google ID token (for mobile/frontend)"
)
async def google_token_auth(
    data: GoogleAuthRequest,
    request: Request
):
    """
    Authenticate using a Google ID token.
    
    This endpoint is for mobile apps and frontends that have already
    obtained a Google ID token through their own OAuth flow.
    
    - **id_token**: The Google ID token from the frontend
    """
    try:
        result = await user_service.google_id_token_auth(
            id_token=data.id_token,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent")
        )
        return result
        
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except AuthenticationError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        logger.error(f"Google token auth error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to authenticate with Google"
        )


# ==========================================
# TOKEN MANAGEMENT ENDPOINTS
# ==========================================

@router.post(
    "/refresh",
    response_model=Dict[str, Any],
    summary="Refresh access token",
    description="Get a new access token using a refresh token"
)
async def refresh_access_token(refresh_token: str):
    """
    Refresh the access token.
    
    - **refresh_token**: A valid refresh token
    """
    try:
        result = await user_service.refresh_token(refresh_token)
        return result
    except AuthenticationError as e:
        raise HTTPException(status_code=401, detail=str(e))


@router.post(
    "/logout",
    response_model=Dict[str, Any],
    summary="Logout user",
    description="Invalidate the user's tokens"
)
async def logout(
    access_token: Optional[str] = None,
    refresh_token: Optional[str] = None
):
    """
    Logout the user by invalidating tokens.
    
    In a stateless JWT system, this is mostly symbolic.
    For full logout, implement token blacklisting with Redis.
    """
    return {
        "success": True,
        "message": "Logged out successfully"
    }


# ==========================================
# OAUTH STATUS ENDPOINT
# ==========================================

@router.get(
    "/oauth/status",
    response_model=Dict[str, Any],
    summary="Check OAuth providers status",
    description="Check which OAuth providers are configured"
)
async def oauth_status():
    """
    Check which OAuth providers are available.
    
    Returns configuration status for Google, Facebook, and Apple OAuth.
    """
    return {
        "google": {
            "enabled": bool(settings.GOOGLE_CLIENT_ID),
            "login_url": "/api/v1/auth/google/login" if settings.GOOGLE_CLIENT_ID else None
        },
        "facebook": {
            "enabled": False,  # Not implemented yet
            "login_url": None
        },
        "apple": {
            "enabled": False,  # Not implemented yet
            "login_url": None
        }
    }
