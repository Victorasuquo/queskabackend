"""
Queska Backend - Agent Schemas
Pydantic schemas for Agent request/response validation
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import EmailStr, Field, field_validator

from app.core.constants import (
    AccountStatus,
    AgentType,
    VerificationStatus,
    SubscriptionPlan,
)
from app.schemas.base import (
    BaseSchema,
    AddressCreate,
    AddressResponse,
    ContactCreate,
    ContactResponse,
    SocialLinksCreate,
    SocialLinksResponse,
    BankAccountCreate,
    BankAccountResponse,
    RatingResponse,
    CommissionCreate,
    CommissionResponse,
    PaginatedResponse,
)


# === Agent Media Schemas ===

class AgentMediaCreate(BaseSchema):
    """Agent media creation schema"""
    profile_photo: Optional[str] = None
    cover_image: Optional[str] = None
    gallery: List[Dict[str, Any]] = Field(default_factory=list)
    portfolio: List[Dict[str, Any]] = Field(default_factory=list)


class AgentMediaResponse(AgentMediaCreate):
    """Agent media response schema"""
    pass


# === Agent Specialization Schemas ===

class AgentSpecializationCreate(BaseSchema):
    """Agent specialization creation"""
    destinations: List[str] = Field(default_factory=list)
    travel_types: List[str] = Field(default_factory=list)
    services: List[str] = Field(default_factory=list)
    languages: List[str] = Field(default_factory=lambda: ["English"])


class AgentSpecializationResponse(AgentSpecializationCreate):
    """Agent specialization response"""
    pass


# === Agent Verification Schemas ===

class AgentVerificationCreate(BaseSchema):
    """Agent verification submission"""
    identity_document: Optional[str] = None
    license_document: Optional[str] = None
    certification: Optional[str] = None
    proof_of_address: Optional[str] = None
    agency_registration: Optional[str] = None


class AgentVerificationResponse(BaseSchema):
    """Agent verification status response"""
    status: VerificationStatus
    identity_document: Optional[str] = None
    license_document: Optional[str] = None
    certification: Optional[str] = None
    proof_of_address: Optional[str] = None
    agency_registration: Optional[str] = None
    submitted_at: Optional[datetime] = None
    reviewed_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None


class AgentVerificationReview(BaseSchema):
    """Admin review of agent verification"""
    status: VerificationStatus
    notes: Optional[str] = None
    rejection_reason: Optional[str] = None


# === Agent Subscription Schemas ===

class AgentSubscriptionResponse(BaseSchema):
    """Agent subscription details"""
    plan: SubscriptionPlan
    started_at: datetime
    expires_at: Optional[datetime] = None
    is_active: bool
    auto_renew: bool
    features: List[str] = Field(default_factory=list)


class AgentSubscriptionUpdate(BaseSchema):
    """Update agent subscription"""
    plan: SubscriptionPlan
    auto_renew: Optional[bool] = None


# === Agent Analytics Schemas ===

class AgentAnalyticsResponse(BaseSchema):
    """Agent analytics summary"""
    total_bookings: int = 0
    total_clients: int = 0
    total_revenue: float = 0.0
    total_commission_earned: float = 0.0
    total_reviews: int = 0
    conversion_rate: float = 0.0
    average_booking_value: float = 0.0
    monthly_stats: Dict[str, Any] = Field(default_factory=dict)
    top_destinations: List[Dict[str, Any]] = Field(default_factory=list)
    last_booking_at: Optional[datetime] = None


# === Agent Agency Schemas ===

class AgentAgencyInfo(BaseSchema):
    """Agent agency information"""
    agency_id: Optional[str] = None
    agency_name: Optional[str] = None
    role: Optional[str] = None
    joined_at: Optional[datetime] = None


# === Agent Registration/Auth Schemas ===

class AgentRegister(BaseSchema):
    """Agent registration request"""
    email: EmailStr
    password: str = Field(..., min_length=8)
    first_name: str = Field(..., min_length=2, max_length=50)
    last_name: str = Field(..., min_length=2, max_length=50)
    phone: str = Field(..., min_length=10)
    agent_type: AgentType = AgentType.INDEPENDENT
    city: str
    state: str
    country: str = "Nigeria"
    referral_code: Optional[str] = None
    
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


class AgentLogin(BaseSchema):
    """Agent login request"""
    email: EmailStr
    password: str
    
    @field_validator("email", mode="before")
    @classmethod
    def lowercase_email(cls, v: str) -> str:
        return v.lower() if v else v


class AgentTokenResponse(BaseSchema):
    """Agent authentication token response"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    agent: "AgentResponse"


# === Agent CRUD Schemas ===

class AgentCreate(BaseSchema):
    """Admin: Create agent account"""
    email: EmailStr
    password: str = Field(..., min_length=8)
    first_name: str = Field(..., min_length=2, max_length=50)
    last_name: str = Field(..., min_length=2, max_length=50)
    display_name: Optional[str] = None
    phone: str
    agent_type: AgentType = AgentType.INDEPENDENT
    bio: Optional[str] = None
    tagline: Optional[str] = None
    address: Optional[AddressCreate] = None
    contact: Optional[ContactCreate] = None
    social_links: Optional[SocialLinksCreate] = None
    specialization: Optional[AgentSpecializationCreate] = None
    years_of_experience: int = 0
    max_clients: int = 50
    
    @field_validator("email", mode="before")
    @classmethod
    def lowercase_email(cls, v: str) -> str:
        return v.lower() if v else v


class AgentUpdate(BaseSchema):
    """Update agent profile"""
    first_name: Optional[str] = Field(None, min_length=2, max_length=50)
    last_name: Optional[str] = Field(None, min_length=2, max_length=50)
    display_name: Optional[str] = None
    phone: Optional[str] = None
    agent_type: Optional[AgentType] = None
    bio: Optional[str] = None
    tagline: Optional[str] = None
    address: Optional[AddressCreate] = None
    contact: Optional[ContactCreate] = None
    social_links: Optional[SocialLinksCreate] = None
    specialization: Optional[AgentSpecializationCreate] = None
    years_of_experience: Optional[int] = None
    is_available: Optional[bool] = None
    max_clients: Optional[int] = None
    availability_schedule: Optional[Dict[str, Any]] = None
    response_time: Optional[str] = None
    notification_preferences: Optional[Dict[str, bool]] = None


class AgentPasswordChange(BaseSchema):
    """Change agent password"""
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


class AgentPasswordReset(BaseSchema):
    """Reset agent password"""
    token: str
    new_password: str = Field(..., min_length=8)


class AgentPasswordResetRequest(BaseSchema):
    """Request agent password reset"""
    email: EmailStr


# === Agent Response Schemas ===

class AgentMinimalResponse(BaseSchema):
    """Minimal agent response for listings"""
    id: str
    first_name: str
    last_name: str
    display_name: Optional[str] = None
    slug: str
    agent_type: AgentType
    tagline: Optional[str] = None
    is_verified: bool
    is_featured: bool
    is_available: bool
    profile_photo: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    rating: Optional[RatingResponse] = None
    years_of_experience: int = 0


class AgentResponse(BaseSchema):
    """Full agent response"""
    id: str
    email: str
    first_name: str
    last_name: str
    display_name: Optional[str] = None
    full_name: Optional[str] = None
    slug: str
    agent_type: AgentType
    bio: Optional[str] = None
    tagline: Optional[str] = None
    phone: str
    status: AccountStatus
    is_verified: bool
    is_featured: bool
    is_premium: bool
    is_active: bool
    is_available: bool
    address: Optional[AddressResponse] = None
    contact: Optional[ContactResponse] = None
    social_links: Optional[SocialLinksResponse] = None
    specialization: Optional[AgentSpecializationResponse] = None
    media: Optional[AgentMediaResponse] = None
    agency: Optional[AgentAgencyInfo] = None
    verification: Optional[AgentVerificationResponse] = None
    subscription: Optional[AgentSubscriptionResponse] = None
    rating: Optional[RatingResponse] = None
    analytics: Optional[AgentAnalyticsResponse] = None
    referral_code: Optional[str] = None
    referral_count: int = 0
    client_count: int = 0
    max_clients: int = 50
    can_accept_clients: bool = True
    certifications: List[Dict[str, Any]] = Field(default_factory=list)
    awards: List[Dict[str, Any]] = Field(default_factory=list)
    years_of_experience: int = 0
    response_time: Optional[str] = None
    booking_link: Optional[str] = None
    stripe_connected: bool = False
    payout_enabled: bool = False
    notification_preferences: Dict[str, bool] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime
    last_login_at: Optional[datetime] = None
    verified_at: Optional[datetime] = None


class AgentPublicResponse(BaseSchema):
    """Public agent profile (for clients)"""
    id: str
    first_name: str
    last_name: str
    display_name: Optional[str] = None
    full_name: Optional[str] = None
    slug: str
    agent_type: AgentType
    bio: Optional[str] = None
    tagline: Optional[str] = None
    is_verified: bool
    is_featured: bool
    is_premium: bool
    is_available: bool
    address: Optional[AddressResponse] = None
    contact: Optional[ContactResponse] = None
    social_links: Optional[SocialLinksResponse] = None
    specialization: Optional[AgentSpecializationResponse] = None
    media: Optional[AgentMediaResponse] = None
    rating: Optional[RatingResponse] = None
    certifications: List[Dict[str, Any]] = Field(default_factory=list)
    years_of_experience: int = 0
    response_time: Optional[str] = None
    booking_link: Optional[str] = None
    can_accept_clients: bool = True
    created_at: datetime


# === Agent Client Management Schemas ===

class AgentClientAdd(BaseSchema):
    """Add client to agent"""
    client_id: str


class AgentClientRemove(BaseSchema):
    """Remove client from agent"""
    client_id: str


class AgentClientListResponse(BaseSchema):
    """Agent's client list"""
    clients: List[Dict[str, Any]]
    total: int


# === Agent Bank Account Schemas ===

class AgentBankAccountAdd(BankAccountCreate):
    """Add agent bank account"""
    is_primary: bool = False


class AgentBankAccountResponse(BankAccountResponse):
    """Agent bank account response"""
    id: str
    verified_at: Optional[datetime] = None


# === Agent Commission Schemas ===

class AgentCommissionUpdate(CommissionCreate):
    """Update agent commission"""
    pass


class AgentCommissionResponse(CommissionResponse):
    """Agent commission response"""
    pass


# === Agent Listing/Search Schemas ===

class AgentListParams(BaseSchema):
    """Agent listing parameters"""
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=20, ge=1, le=100)
    search: Optional[str] = None
    agent_type: Optional[AgentType] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    is_verified: Optional[bool] = None
    is_featured: Optional[bool] = None
    is_available: Optional[bool] = None
    min_rating: Optional[float] = None
    min_experience: Optional[int] = None
    destinations: Optional[List[str]] = None
    travel_types: Optional[List[str]] = None
    languages: Optional[List[str]] = None
    sort_by: str = "created_at"
    sort_order: str = "desc"
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    radius_km: Optional[float] = None


class AgentListResponse(PaginatedResponse[AgentMinimalResponse]):
    """Paginated agent list response"""
    pass


# === Admin Agent Schemas ===

class AgentStatusUpdate(BaseSchema):
    """Admin: Update agent status"""
    status: AccountStatus
    reason: Optional[str] = None


class AgentFeatureToggle(BaseSchema):
    """Admin: Toggle agent features"""
    is_featured: Optional[bool] = None
    is_premium: Optional[bool] = None
    is_verified: Optional[bool] = None


class AgentBulkAction(BaseSchema):
    """Admin: Bulk action on agents"""
    agent_ids: List[str]
    action: str  # activate, suspend, delete, feature
    reason: Optional[str] = None


# === Agent Referral Schemas ===

class AgentReferralStats(BaseSchema):
    """Agent referral statistics"""
    referral_code: str
    referral_count: int
    referral_earnings: float
    referred_agents: List[Dict[str, Any]] = Field(default_factory=list)


# Update forward reference
AgentTokenResponse.model_rebuild()

