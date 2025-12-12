"""
Queska Backend - User API Endpoints
Comprehensive RESTful API routes for User operations
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from loguru import logger

from app.api.deps import (
    get_current_user,
    get_current_active_user,
    get_current_admin,
    get_optional_token_data,
    get_pagination_params,
)
from app.core.constants import AccountStatus
from app.core.exceptions import (
    AlreadyExistsError,
    AuthenticationError,
    InvalidCredentialsError,
    NotFoundError,
    ValidationError,
)
from app.models.user import User
from app.models.admin import Admin
from app.schemas.user import (
    UserRegister,
    UserLogin,
    UserCreate,
    UserUpdate,
    UserResponse,
    UserPublicResponse,
    UserMinimalResponse,
    UserTokenResponse,
    UserListParams,
    UserPasswordChange,
    UserPasswordResetRequest,
    UserPasswordReset,
    EmailVerificationRequest,
    EmailVerificationConfirm,
    UserPreferencesUpdate,
    UserNotificationPreferences,
    UserProfilePhotoUpdate,
    UserCoverPhotoUpdate,
    AddFavoriteVendor,
    AddFavoriteDestination,
    FollowUserRequest,
    AssignAgentRequest,
    AdminUserStatusUpdate,
    GoogleAuthRequest,
    FacebookAuthRequest,
    UserDashboardResponse,
    UserAddressCreate,
)
from app.schemas.base import (
    SuccessResponse,
    ErrorResponse,
    DeleteResponse,
)
from app.services.user_service import user_service


router = APIRouter()


# ==========================================
# PUBLIC ENDPOINTS (No Authentication)
# ==========================================

@router.post(
    "/register",
    response_model=Dict[str, Any],
    status_code=status.HTTP_201_CREATED,
    summary="Register new user",
    description="Create a new user account"
)
async def register_user(data: UserRegister, request: Request):
    """
    Register a new user account.
    
    - **email**: Unique email address
    - **password**: Strong password (min 8 chars, uppercase, lowercase, digit)
    - **first_name**: User's first name
    - **last_name**: User's last name
    - **phone**: Optional phone number
    """
    try:
        user = await user_service.register(
            data,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent")
        )
        return {
            "success": True,
            "message": "Account created successfully. Please verify your email.",
            "user_id": str(user.id),
            "email": user.email,
            "referral_code": user.referral_code
        }
    except AlreadyExistsError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        logger.error(f"User registration error: {e}")
        raise HTTPException(status_code=500, detail="Registration failed")


@router.post(
    "/login",
    response_model=UserTokenResponse,
    summary="User login",
    description="Authenticate user and get access tokens"
)
async def login_user(data: UserLogin, request: Request):
    """
    Authenticate user with email and password.
    
    Returns access token, refresh token, and user profile.
    """
    try:
        result = await user_service.login(
            data,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent")
        )
        return result
    except InvalidCredentialsError:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )
    except AuthenticationError as e:
        raise HTTPException(status_code=401, detail=str(e))


@router.post(
    "/refresh-token",
    response_model=Dict[str, Any],
    summary="Refresh access token",
    description="Get new access token using refresh token"
)
async def refresh_token(refresh_token: str):
    """Refresh the access token using a valid refresh token."""
    try:
        result = await user_service.refresh_token(refresh_token)
        return result
    except AuthenticationError as e:
        raise HTTPException(status_code=401, detail=str(e))


@router.post(
    "/logout",
    response_model=SuccessResponse,
    summary="Logout user",
    description="Log out and invalidate tokens"
)
async def logout_user(
    request: Request,
    user: User = Depends(get_current_user)
):
    """Log out user and record activity."""
    await user_service.logout(
        str(user.id),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )
    return SuccessResponse(message="Logged out successfully")


# === OAuth Endpoints ===

@router.post(
    "/auth/google",
    response_model=Dict[str, Any],
    summary="Google OAuth login",
    description="Authenticate or register via Google"
)
async def google_auth(data: GoogleAuthRequest):
    """
    Authenticate with Google OAuth.
    
    If user exists, logs in. If not, creates new account.
    """
    # TODO: Verify Google ID token and extract user info
    # For now, this is a placeholder
    raise HTTPException(
        status_code=501,
        detail="Google OAuth integration pending. Configure GOOGLE_CLIENT_ID."
    )


@router.post(
    "/auth/facebook",
    response_model=Dict[str, Any],
    summary="Facebook OAuth login",
    description="Authenticate or register via Facebook"
)
async def facebook_auth(data: FacebookAuthRequest):
    """
    Authenticate with Facebook OAuth.
    
    If user exists, logs in. If not, creates new account.
    """
    # TODO: Verify Facebook access token and extract user info
    raise HTTPException(
        status_code=501,
        detail="Facebook OAuth integration pending. Configure FACEBOOK_APP_ID."
    )


# === Password Management ===

@router.post(
    "/forgot-password",
    response_model=SuccessResponse,
    summary="Request password reset",
    description="Send password reset email"
)
async def forgot_password(data: UserPasswordResetRequest):
    """Request a password reset link via email."""
    try:
        await user_service.request_password_reset(data.email)
        return SuccessResponse(
            message="If this email exists, you will receive reset instructions"
        )
    except NotFoundError:
        # Don't reveal if email exists
        return SuccessResponse(
            message="If this email exists, you will receive reset instructions"
        )


@router.post(
    "/reset-password",
    response_model=SuccessResponse,
    summary="Reset password",
    description="Reset password using token"
)
async def reset_password(data: UserPasswordReset):
    """Reset password using the token received via email."""
    try:
        await user_service.reset_password(data.token, data.new_password)
        return SuccessResponse(message="Password reset successfully")
    except AuthenticationError as e:
        raise HTTPException(status_code=400, detail=str(e))


# === Email Verification ===

@router.post(
    "/verify-email/request",
    response_model=SuccessResponse,
    summary="Request email verification",
    description="Send verification email"
)
async def request_email_verification(
    user: User = Depends(get_current_user)
):
    """Request email verification link."""
    try:
        await user_service.request_email_verification(str(user.id))
        return SuccessResponse(message="Verification email sent")
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post(
    "/verify-email/confirm",
    response_model=SuccessResponse,
    summary="Confirm email verification",
    description="Verify email with token"
)
async def confirm_email_verification(data: EmailVerificationConfirm):
    """Verify email using the token received via email."""
    try:
        await user_service.verify_email(data.token)
        return SuccessResponse(message="Email verified successfully")
    except AuthenticationError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==========================================
# AUTHENTICATED USER ENDPOINTS
# ==========================================

# === Profile ===

@router.get(
    "/me",
    response_model=Dict[str, Any],
    summary="Get current user profile",
    description="Get authenticated user's full profile"
)
async def get_my_profile(user: User = Depends(get_current_user)):
    """Get the currently authenticated user's profile."""
    return user_service._to_response(user)


@router.put(
    "/me",
    response_model=Dict[str, Any],
    summary="Update profile",
    description="Update authenticated user's profile"
)
async def update_my_profile(
    data: UserUpdate,
    user: User = Depends(get_current_user)
):
    """Update the currently authenticated user's profile."""
    try:
        updated_user = await user_service.update_profile(str(user.id), data)
        return user_service._to_response(updated_user)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="User not found")


@router.post(
    "/me/change-password",
    response_model=SuccessResponse,
    summary="Change password",
    description="Change user password"
)
async def change_password(
    data: UserPasswordChange,
    request: Request,
    user: User = Depends(get_current_user)
):
    """Change the current user's password."""
    try:
        await user_service.change_password(
            str(user.id),
            data.current_password,
            data.new_password,
            ip_address=request.client.host if request.client else None
        )
        return SuccessResponse(message="Password changed successfully")
    except InvalidCredentialsError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put(
    "/me/profile-photo",
    response_model=Dict[str, Any],
    summary="Update profile photo",
    description="Update user's profile photo"
)
async def update_profile_photo(
    data: UserProfilePhotoUpdate,
    user: User = Depends(get_current_user)
):
    """Update profile photo URL."""
    updated_user = await user_service.update_profile_photo(
        str(user.id),
        data.profile_photo
    )
    return {
        "success": True,
        "profile_photo": updated_user.profile_photo
    }


@router.put(
    "/me/cover-photo",
    response_model=Dict[str, Any],
    summary="Update cover photo",
    description="Update user's cover photo"
)
async def update_cover_photo(
    data: UserCoverPhotoUpdate,
    user: User = Depends(get_current_user)
):
    """Update cover photo URL."""
    updated_user = await user_service.update_cover_photo(
        str(user.id),
        data.cover_photo
    )
    return {
        "success": True,
        "cover_photo": updated_user.cover_photo
    }


@router.delete(
    "/me",
    response_model=SuccessResponse,
    summary="Delete account",
    description="Delete user's own account"
)
async def delete_my_account(
    reason: Optional[str] = None,
    user: User = Depends(get_current_user)
):
    """Delete the current user's account (soft delete)."""
    await user_service.delete_user(str(user.id), reason=reason, soft=True)
    return SuccessResponse(message="Account deleted successfully")


# === Preferences ===

@router.get(
    "/me/preferences",
    response_model=Dict[str, Any],
    summary="Get preferences",
    description="Get user's travel preferences"
)
async def get_my_preferences(user: User = Depends(get_current_user)):
    """Get the current user's preferences."""
    return {
        "preferences": user.preferences.model_dump() if user.preferences else None,
        "notification_preferences": user.notification_preferences
    }


@router.put(
    "/me/preferences",
    response_model=Dict[str, Any],
    summary="Update preferences",
    description="Update travel preferences"
)
async def update_my_preferences(
    data: UserPreferencesUpdate,
    user: User = Depends(get_current_user)
):
    """Update the current user's travel preferences."""
    updated_user = await user_service.update_preferences(str(user.id), data)
    return {
        "success": True,
        "preferences": updated_user.preferences.model_dump() if updated_user.preferences else None
    }


@router.put(
    "/me/notification-preferences",
    response_model=Dict[str, Any],
    summary="Update notification preferences",
    description="Update notification settings"
)
async def update_notification_preferences(
    data: UserNotificationPreferences,
    user: User = Depends(get_current_user)
):
    """Update notification preferences."""
    updated_user = await user_service.update_notification_preferences(
        str(user.id),
        data.model_dump()
    )
    return {
        "success": True,
        "notification_preferences": updated_user.notification_preferences
    }


# === Addresses ===

@router.get(
    "/me/addresses",
    response_model=List[Dict[str, Any]],
    summary="Get addresses",
    description="Get user's saved addresses"
)
async def get_my_addresses(user: User = Depends(get_current_user)):
    """Get the current user's saved addresses."""
    return [addr.model_dump() for addr in user.addresses]


@router.post(
    "/me/addresses",
    response_model=Dict[str, Any],
    status_code=status.HTTP_201_CREATED,
    summary="Add address",
    description="Add a new address"
)
async def add_address(
    data: UserAddressCreate,
    user: User = Depends(get_current_user)
):
    """Add a new address to the user's profile."""
    from app.repositories.user_repository import user_repository
    
    updated_user = await user_repository.add_address(
        str(user.id),
        data.model_dump()
    )
    return {
        "success": True,
        "message": "Address added successfully",
        "addresses_count": len(updated_user.addresses)
    }


# === Favorites ===

@router.get(
    "/me/favorites",
    response_model=Dict[str, Any],
    summary="Get favorites",
    description="Get user's favorite vendors and destinations"
)
async def get_my_favorites(user: User = Depends(get_current_user)):
    """Get the current user's favorites."""
    return await user_service.get_user_favorites(str(user.id))


@router.post(
    "/me/favorites/vendors",
    response_model=SuccessResponse,
    summary="Add favorite vendor",
    description="Add vendor to favorites"
)
async def add_favorite_vendor(
    data: AddFavoriteVendor,
    user: User = Depends(get_current_user)
):
    """Add a vendor to favorites."""
    try:
        await user_service.add_favorite_vendor(str(user.id), data.vendor_id)
        return SuccessResponse(message="Vendor added to favorites")
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete(
    "/me/favorites/vendors/{vendor_id}",
    response_model=SuccessResponse,
    summary="Remove favorite vendor",
    description="Remove vendor from favorites"
)
async def remove_favorite_vendor(
    vendor_id: str,
    user: User = Depends(get_current_user)
):
    """Remove a vendor from favorites."""
    await user_service.remove_favorite_vendor(str(user.id), vendor_id)
    return SuccessResponse(message="Vendor removed from favorites")


@router.post(
    "/me/favorites/destinations",
    response_model=SuccessResponse,
    summary="Add favorite destination",
    description="Add destination to favorites"
)
async def add_favorite_destination(
    data: AddFavoriteDestination,
    user: User = Depends(get_current_user)
):
    """Add a destination to favorites."""
    await user_service.add_favorite_destination(str(user.id), data.destination)
    return SuccessResponse(message="Destination added to favorites")


@router.delete(
    "/me/favorites/destinations/{destination}",
    response_model=SuccessResponse,
    summary="Remove favorite destination",
    description="Remove destination from favorites"
)
async def remove_favorite_destination(
    destination: str,
    user: User = Depends(get_current_user)
):
    """Remove a destination from favorites."""
    await user_service.remove_favorite_destination(str(user.id), destination)
    return SuccessResponse(message="Destination removed from favorites")


# === Social/Following ===

@router.get(
    "/me/followers",
    response_model=Dict[str, Any],
    summary="Get followers",
    description="Get list of users following me"
)
async def get_my_followers(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user)
):
    """Get the current user's followers."""
    followers, total = await user_service.get_followers(
        str(user.id), skip, limit
    )
    return {
        "followers": followers,
        "total": total,
        "page": (skip // limit) + 1,
        "limit": limit
    }


@router.get(
    "/me/following",
    response_model=Dict[str, Any],
    summary="Get following",
    description="Get list of users I follow"
)
async def get_my_following(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user)
):
    """Get users that the current user follows."""
    following, total = await user_service.get_following(
        str(user.id), skip, limit
    )
    return {
        "following": following,
        "total": total,
        "page": (skip // limit) + 1,
        "limit": limit
    }


@router.post(
    "/me/follow",
    response_model=SuccessResponse,
    summary="Follow user",
    description="Follow another user"
)
async def follow_user(
    data: FollowUserRequest,
    user: User = Depends(get_current_user)
):
    """Follow another user."""
    try:
        await user_service.follow_user(str(user.id), data.user_id)
        return SuccessResponse(message="Now following user")
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete(
    "/me/follow/{target_user_id}",
    response_model=SuccessResponse,
    summary="Unfollow user",
    description="Unfollow a user"
)
async def unfollow_user(
    target_user_id: str,
    user: User = Depends(get_current_user)
):
    """Unfollow a user."""
    try:
        await user_service.unfollow_user(str(user.id), target_user_id)
        return SuccessResponse(message="Unfollowed user")
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))


# === Agent Assignment ===

@router.get(
    "/me/agent",
    response_model=Dict[str, Any],
    summary="Get assigned agent",
    description="Get my assigned travel agent"
)
async def get_my_agent(user: User = Depends(get_current_user)):
    """Get the current user's assigned agent."""
    if not user.assigned_agent_id:
        return {"agent": None}
    
    from app.repositories.agent_repository import agent_repository
    agent = await agent_repository.get_by_id(str(user.assigned_agent_id))
    
    if not agent:
        return {"agent": None}
    
    return {
        "agent": {
            "id": str(agent.id),
            "name": agent.full_name,
            "profile_photo": agent.media.profile_photo if agent.media else None,
            "phone": agent.phone,
            "email": agent.email,
            "rating": agent.rating.average if agent.rating else 0,
            "is_available": agent.is_available,
        }
    }


@router.post(
    "/me/agent",
    response_model=SuccessResponse,
    summary="Request agent",
    description="Request a travel agent assignment"
)
async def request_agent_assignment(
    data: AssignAgentRequest,
    user: User = Depends(get_current_user)
):
    """Request to be assigned to a specific agent."""
    try:
        await user_service.assign_agent(str(user.id), data.agent_id)
        return SuccessResponse(message="Agent assigned successfully")
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete(
    "/me/agent",
    response_model=SuccessResponse,
    summary="Remove agent",
    description="Remove assigned agent"
)
async def remove_agent_assignment(
    user: User = Depends(get_current_user)
):
    """Remove agent assignment."""
    await user_service.unassign_agent(str(user.id))
    return SuccessResponse(message="Agent removed successfully")


# === Activity Logs ===

@router.get(
    "/me/activity",
    response_model=Dict[str, Any],
    summary="Get activity logs",
    description="Get user's activity history"
)
async def get_my_activity(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user)
):
    """Get the current user's activity logs."""
    activities, total = await user_service.get_activity_logs(
        str(user.id), skip, limit
    )
    pages = (total + limit - 1) // limit
    
    return {
        "activities": activities,
        "total": total,
        "page": (skip // limit) + 1,
        "pages": pages,
        "limit": limit
    }


# === Referrals ===

@router.get(
    "/me/referrals",
    response_model=Dict[str, Any],
    summary="Get referral info",
    description="Get user's referral code and stats"
)
async def get_my_referrals(user: User = Depends(get_current_user)):
    """Get the current user's referral information."""
    return {
        "referral_code": user.referral_code,
        "referral_count": user.referral_count,
        "referral_credits": user.referral_credits
    }


# ==========================================
# PUBLIC USER PROFILES
# ==========================================

@router.get(
    "/{user_id}/public",
    response_model=Dict[str, Any],
    summary="Get public profile",
    description="Get a user's public profile"
)
async def get_public_profile(user_id: str):
    """Get a user's public profile."""
    try:
        user = await user_service.get_user(user_id)
        return user.to_public_dict()
    except NotFoundError:
        raise HTTPException(status_code=404, detail="User not found")


@router.get(
    "/{user_id}/followers",
    response_model=Dict[str, Any],
    summary="Get user followers",
    description="Get a user's followers"
)
async def get_user_followers(
    user_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100)
):
    """Get a user's followers list."""
    try:
        followers, total = await user_service.get_followers(user_id, skip, limit)
        return {
            "followers": followers,
            "total": total
        }
    except NotFoundError:
        raise HTTPException(status_code=404, detail="User not found")


@router.get(
    "/{user_id}/following",
    response_model=Dict[str, Any],
    summary="Get user following",
    description="Get users that a user follows"
)
async def get_user_following(
    user_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100)
):
    """Get users that this user follows."""
    try:
        following, total = await user_service.get_following(user_id, skip, limit)
        return {
            "following": following,
            "total": total
        }
    except NotFoundError:
        raise HTTPException(status_code=404, detail="User not found")


# ==========================================
# ADMIN USER MANAGEMENT
# ==========================================

@router.get(
    "/admin/stats",
    response_model=Dict[str, Any],
    summary="Get user statistics",
    description="Admin: Get overall user statistics"
)
async def get_user_stats(admin: Admin = Depends(get_current_admin)):
    """Get user statistics for admin dashboard."""
    return await user_service.get_user_stats()


@router.get(
    "/admin/list",
    response_model=Dict[str, Any],
    summary="List all users",
    description="Admin: List users with filters"
)
async def admin_list_users(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    status: Optional[AccountStatus] = None,
    is_email_verified: Optional[bool] = None,
    is_active: Optional[bool] = None,
    assigned_agent_id: Optional[str] = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
    admin: Admin = Depends(get_current_admin)
):
    """Admin: List all users with filters."""
    params = UserListParams(
        page=page,
        limit=limit,
        search=search,
        status=status,
        is_email_verified=is_email_verified,
        is_active=is_active,
        assigned_agent_id=assigned_agent_id,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    
    users, total, pages = await user_service.list_users(params)
    
    return {
        "items": users,
        "total": total,
        "page": page,
        "limit": limit,
        "pages": pages,
        "has_next": page < pages,
        "has_prev": page > 1
    }


@router.get(
    "/admin/{user_id}",
    response_model=Dict[str, Any],
    summary="Get user details",
    description="Admin: Get full user details"
)
async def admin_get_user(
    user_id: str,
    admin: Admin = Depends(get_current_admin)
):
    """Admin: Get full user details."""
    try:
        user = await user_service.get_user(user_id)
        return user_service._to_response(user)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="User not found")


@router.put(
    "/admin/{user_id}/status",
    response_model=Dict[str, Any],
    summary="Update user status",
    description="Admin: Update user account status"
)
async def admin_update_user_status(
    user_id: str,
    data: AdminUserStatusUpdate,
    admin: Admin = Depends(get_current_admin)
):
    """Admin: Update user account status (activate, suspend, disable)."""
    try:
        await user_service.update_status(user_id, data.status, data.reason)
        return {
            "success": True,
            "message": f"User status updated to {data.status.value}"
        }
    except NotFoundError:
        raise HTTPException(status_code=404, detail="User not found")


@router.delete(
    "/admin/{user_id}",
    response_model=DeleteResponse,
    summary="Delete user",
    description="Admin: Delete user account"
)
async def admin_delete_user(
    user_id: str,
    reason: Optional[str] = None,
    admin: Admin = Depends(get_current_admin)
):
    """Admin: Soft delete a user account."""
    try:
        await user_service.delete_user(user_id, reason=reason, soft=True)
        return DeleteResponse(id=user_id)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="User not found")

