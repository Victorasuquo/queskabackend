"""
Queska Backend - User Schemas
Pydantic schemas for User request/response validation
"""

from datetime import datetime, date
from typing import Any, Dict, List, Optional

from pydantic import EmailStr, Field, field_validator

from app.core.constants import (
    AccountStatus,
    TravelInterest,
    SubscriptionPlan,
)
from app.schemas.base import (
    BaseSchema,
    AddressCreate,
    AddressResponse,
    PaginatedResponse,
)


# === User Preferences Schemas ===

class UserPreferencesCreate(BaseSchema):
    """User preferences creation"""
    interests: List[str] = Field(default_factory=list)
    travel_style: Optional[str] = None  # budget, mid-range, luxury
    dietary_restrictions: List[str] = Field(default_factory=list)
    languages: List[str] = Field(default_factory=lambda: ["English"])
    currency: str = "NGN"


class UserPreferencesResponse(UserPreferencesCreate):
    """User preferences response"""
    pass


class UserPreferencesUpdate(BaseSchema):
    """Update user preferences"""
    interests: Optional[List[str]] = None
    travel_style: Optional[str] = None
    dietary_restrictions: Optional[List[str]] = None
    languages: Optional[List[str]] = None
    currency: Optional[str] = None


# === User Address Schemas ===

class UserAddressCreate(BaseSchema):
    """User address creation"""
    street: Optional[str] = None
    city: str
    state: str
    country: str = "Nigeria"
    postal_code: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class UserAddressResponse(UserAddressCreate):
    """User address response"""
    pass


# === User Registration/Auth Schemas ===

class UserRegister(BaseSchema):
    """User registration request"""
    email: EmailStr
    password: str = Field(..., min_length=8)
    first_name: str = Field(..., min_length=2, max_length=50)
    last_name: str = Field(..., min_length=2, max_length=50)
    phone: Optional[str] = None
    
    @field_validator("email", mode="before")
    @classmethod
    def lowercase_email(cls, v: str) -> str:
        return v.lower() if v else v
    
    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class UserLogin(BaseSchema):
    """User login request"""
    email: EmailStr
    password: str
    
    @field_validator("email", mode="before")
    @classmethod
    def lowercase_email(cls, v: str) -> str:
        return v.lower() if v else v


class UserTokenResponse(BaseSchema):
    """User authentication token response"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: "UserResponse"


class UserRefreshToken(BaseSchema):
    """Refresh token request"""
    refresh_token: str


# === OAuth Schemas ===

class GoogleAuthRequest(BaseSchema):
    """Google OAuth login request"""
    id_token: str


class FacebookAuthRequest(BaseSchema):
    """Facebook OAuth login request"""
    access_token: str


class AppleAuthRequest(BaseSchema):
    """Apple OAuth login request"""
    id_token: str
    authorization_code: Optional[str] = None


class OAuthResponse(BaseSchema):
    """OAuth response with tokens and user"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: "UserResponse"
    is_new_user: bool = False


# === Password Management Schemas ===

class UserPasswordChange(BaseSchema):
    """Change user password"""
    current_password: str
    new_password: str = Field(..., min_length=8)
    
    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class UserPasswordResetRequest(BaseSchema):
    """Request user password reset"""
    email: EmailStr


class UserPasswordReset(BaseSchema):
    """Reset user password"""
    token: str
    new_password: str = Field(..., min_length=8)


# === Email Verification Schemas ===

class EmailVerificationRequest(BaseSchema):
    """Request email verification"""
    email: EmailStr


class EmailVerificationConfirm(BaseSchema):
    """Confirm email verification"""
    token: str


# === User CRUD Schemas ===

class UserCreate(BaseSchema):
    """Admin: Create user account"""
    email: EmailStr
    password: str = Field(..., min_length=8)
    first_name: str = Field(..., min_length=2, max_length=50)
    last_name: str = Field(..., min_length=2, max_length=50)
    phone: Optional[str] = None
    display_name: Optional[str] = None
    bio: Optional[str] = None
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    address: Optional[UserAddressCreate] = None
    preferences: Optional[UserPreferencesCreate] = None
    
    @field_validator("email", mode="before")
    @classmethod
    def lowercase_email(cls, v: str) -> str:
        return v.lower() if v else v


class UserUpdate(BaseSchema):
    """Update user profile"""
    first_name: Optional[str] = Field(None, min_length=2, max_length=50)
    last_name: Optional[str] = Field(None, min_length=2, max_length=50)
    display_name: Optional[str] = None
    phone: Optional[str] = None
    bio: Optional[str] = None
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    address: Optional[UserAddressCreate] = None


class UserProfilePhotoUpdate(BaseSchema):
    """Update profile photo"""
    profile_photo: str


class UserCoverPhotoUpdate(BaseSchema):
    """Update cover photo"""
    cover_photo: str


# === Notification Preferences ===

class UserNotificationPreferences(BaseSchema):
    """User notification preferences"""
    email_bookings: bool = True
    email_promotions: bool = False
    email_newsletter: bool = False
    email_experience_updates: bool = True
    email_agent_messages: bool = True
    push_bookings: bool = True
    push_messages: bool = True
    push_promotions: bool = False
    push_experience_updates: bool = True
    sms_bookings: bool = False
    sms_verification: bool = True


# === User Subscription Schemas ===

class UserSubscriptionResponse(BaseSchema):
    """User subscription details"""
    plan: SubscriptionPlan
    started_at: datetime
    expires_at: Optional[datetime] = None
    is_active: bool
    auto_renew: bool
    features: List[str] = Field(default_factory=list)


class UserSubscriptionUpdate(BaseSchema):
    """Update user subscription"""
    plan: SubscriptionPlan
    auto_renew: Optional[bool] = None


# === User Response Schemas ===

class UserMinimalResponse(BaseSchema):
    """Minimal user response for lists"""
    id: str
    first_name: str
    last_name: str
    display_name: Optional[str] = None
    profile_photo: Optional[str] = None
    is_email_verified: bool = False


class UserResponse(BaseSchema):
    """Full user response"""
    id: str
    email: str
    first_name: str
    last_name: str
    display_name: Optional[str] = None
    full_name: Optional[str] = None
    phone: Optional[str] = None
    bio: Optional[str] = None
    profile_photo: Optional[str] = None
    cover_photo: Optional[str] = None
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    status: AccountStatus
    is_email_verified: bool
    is_phone_verified: bool
    is_active: bool
    address: Optional[UserAddressResponse] = None
    preferences: Optional[UserPreferencesResponse] = None
    notification_preferences: Dict[str, bool] = Field(default_factory=dict)
    subscription: Optional[UserSubscriptionResponse] = None
    followers_count: int = 0
    following_count: int = 0
    experiences_count: int = 0
    reviews_count: int = 0
    assigned_agent_id: Optional[str] = None
    favorite_destinations: List[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
    last_login_at: Optional[datetime] = None


class UserPublicResponse(BaseSchema):
    """Public user profile (for other users)"""
    id: str
    first_name: str
    last_name: str
    display_name: Optional[str] = None
    full_name: Optional[str] = None
    bio: Optional[str] = None
    profile_photo: Optional[str] = None
    cover_photo: Optional[str] = None
    followers_count: int = 0
    following_count: int = 0
    experiences_count: int = 0
    reviews_count: int = 0
    favorite_destinations: List[str] = Field(default_factory=list)
    created_at: datetime


# === User Listing/Search Schemas ===

class UserListParams(BaseSchema):
    """User listing parameters"""
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=20, ge=1, le=100)
    search: Optional[str] = None
    status: Optional[AccountStatus] = None
    is_email_verified: Optional[bool] = None
    is_active: Optional[bool] = None
    assigned_agent_id: Optional[str] = None
    sort_by: str = "created_at"
    sort_order: str = "desc"


class UserListResponse(PaginatedResponse[UserMinimalResponse]):
    """Paginated user list response"""
    pass


# === Favorites Management ===

class AddFavoriteVendor(BaseSchema):
    """Add vendor to favorites"""
    vendor_id: str


class RemoveFavoriteVendor(BaseSchema):
    """Remove vendor from favorites"""
    vendor_id: str


class AddFavoriteDestination(BaseSchema):
    """Add destination to favorites"""
    destination: str


class RemoveFavoriteDestination(BaseSchema):
    """Remove destination from favorites"""
    destination: str


class UserFavoritesResponse(BaseSchema):
    """User favorites response"""
    favorite_vendors: List[Dict[str, Any]] = Field(default_factory=list)
    favorite_destinations: List[str] = Field(default_factory=list)


# === Social/Follow Schemas ===

class FollowUserRequest(BaseSchema):
    """Follow user request"""
    user_id: str


class UnfollowUserRequest(BaseSchema):
    """Unfollow user request"""
    user_id: str


class UserFollowersResponse(BaseSchema):
    """User followers list"""
    followers: List[UserMinimalResponse]
    total: int


class UserFollowingResponse(BaseSchema):
    """User following list"""
    following: List[UserMinimalResponse]
    total: int


# === Agent Assignment ===

class AssignAgentRequest(BaseSchema):
    """Assign agent to user"""
    agent_id: str


# === Dashboard Schemas ===

class UserDashboardStats(BaseSchema):
    """User dashboard statistics"""
    total_experiences: int = 0
    completed_experiences: int = 0
    upcoming_experiences: int = 0
    cancelled_experiences: int = 0
    total_bookings: int = 0
    total_spent: float = 0.0
    total_reviews: int = 0
    average_rating_given: float = 0.0
    favorite_destinations_count: int = 0
    favorite_vendors_count: int = 0
    followers_count: int = 0
    following_count: int = 0


class UserDashboardExperience(BaseSchema):
    """Experience summary for dashboard"""
    id: str
    title: str
    destination: str
    status: str
    start_date: datetime
    end_date: datetime
    total_cost: float
    currency: str = "NGN"
    cover_image: Optional[str] = None


class UserDashboardBooking(BaseSchema):
    """Booking summary for dashboard"""
    id: str
    type: str  # hotel, event, activity, dining, ride
    title: str
    status: str
    booking_date: datetime
    amount: float
    currency: str = "NGN"
    vendor_name: Optional[str] = None


class UserDashboardNotification(BaseSchema):
    """Recent notification for dashboard"""
    id: str
    type: str
    title: str
    message: str
    is_read: bool
    created_at: datetime


class UserDashboardResponse(BaseSchema):
    """Comprehensive user dashboard response"""
    stats: UserDashboardStats
    upcoming_experiences: List[UserDashboardExperience] = Field(default_factory=list)
    recent_bookings: List[UserDashboardBooking] = Field(default_factory=list)
    recent_notifications: List[UserDashboardNotification] = Field(default_factory=list)
    recommended_destinations: List[Dict[str, Any]] = Field(default_factory=list)
    recommended_experiences: List[Dict[str, Any]] = Field(default_factory=list)
    assigned_agent: Optional[Dict[str, Any]] = None


class UserActivityLog(BaseSchema):
    """User activity log entry"""
    id: str
    action: str
    description: str
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    created_at: datetime


class UserActivityLogsResponse(BaseSchema):
    """User activity logs response"""
    activities: List[UserActivityLog]
    total: int
    page: int
    pages: int


# === Admin User Schemas ===

class AdminUserStatusUpdate(BaseSchema):
    """Admin: Update user status"""
    status: AccountStatus
    reason: Optional[str] = None


class AdminUserBulkAction(BaseSchema):
    """Admin: Bulk action on users"""
    user_ids: List[str]
    action: str  # activate, suspend, delete
    reason: Optional[str] = None


# Update forward references
UserTokenResponse.model_rebuild()
OAuthResponse.model_rebuild()

