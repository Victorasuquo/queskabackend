"""
Queska Backend - Vendor Schemas
Pydantic schemas for Vendor request/response validation
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import EmailStr, Field, field_validator

from app.core.constants import (
    AccountStatus,
    VendorCategory,
    VerificationStatus,
    CancellationPolicy,
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
    OperatingHoursCreate,
    OperatingHoursResponse,
    BankAccountCreate,
    BankAccountResponse,
    RatingResponse,
    CommissionCreate,
    CommissionResponse,
    PaginatedResponse,
)


# === Price Range Schema ===

class PriceRangeCreate(BaseSchema):
    """Price range schema"""
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    currency: str = "NGN"


class PriceRangeResponse(PriceRangeCreate):
    """Price range response schema"""
    pass


# === Vendor Media Schemas ===

class VendorMediaCreate(BaseSchema):
    """Vendor media creation schema"""
    logo: Optional[str] = None
    cover_image: Optional[str] = None
    gallery: List[Dict[str, Any]] = Field(default_factory=list)
    videos: List[Dict[str, Any]] = Field(default_factory=list)


class VendorMediaResponse(VendorMediaCreate):
    """Vendor media response schema"""
    pass


# === Vendor Verification Schemas ===

class VendorVerificationCreate(BaseSchema):
    """Vendor verification submission"""
    business_registration: Optional[str] = None
    tax_certificate: Optional[str] = None
    license_document: Optional[str] = None
    identity_document: Optional[str] = None
    proof_of_address: Optional[str] = None


class VendorVerificationResponse(BaseSchema):
    """Vendor verification status response"""
    status: VerificationStatus
    business_registration: Optional[str] = None
    tax_certificate: Optional[str] = None
    license_document: Optional[str] = None
    identity_document: Optional[str] = None
    proof_of_address: Optional[str] = None
    submitted_at: Optional[datetime] = None
    reviewed_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None


class VendorVerificationReview(BaseSchema):
    """Admin review of vendor verification"""
    status: VerificationStatus
    notes: Optional[str] = None
    rejection_reason: Optional[str] = None


# === Vendor Subscription Schemas ===

class VendorSubscriptionResponse(BaseSchema):
    """Vendor subscription details"""
    plan: SubscriptionPlan
    started_at: datetime
    expires_at: Optional[datetime] = None
    is_active: bool
    auto_renew: bool
    features: List[str] = Field(default_factory=list)


class VendorSubscriptionUpdate(BaseSchema):
    """Update vendor subscription"""
    plan: SubscriptionPlan
    auto_renew: Optional[bool] = None


# === Vendor Analytics Schemas ===

class VendorAnalyticsResponse(BaseSchema):
    """Vendor analytics summary"""
    total_bookings: int = 0
    total_revenue: float = 0.0
    total_reviews: int = 0
    total_views: int = 0
    total_favorites: int = 0
    conversion_rate: float = 0.0
    average_booking_value: float = 0.0
    monthly_stats: Dict[str, Any] = Field(default_factory=dict)
    last_booking_at: Optional[datetime] = None


# === Vendor Registration/Auth Schemas ===

class VendorRegister(BaseSchema):
    """Vendor registration request"""
    email: EmailStr
    password: str = Field(..., min_length=8)
    business_name: str = Field(..., min_length=2, max_length=100)
    category: VendorCategory
    owner_first_name: str = Field(..., min_length=2, max_length=50)
    owner_last_name: str = Field(..., min_length=2, max_length=50)
    owner_phone: str = Field(..., min_length=10)
    city: str
    state: str
    country: str = "Nigeria"
    
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


class VendorLogin(BaseSchema):
    """Vendor login request"""
    email: EmailStr
    password: str
    
    @field_validator("email", mode="before")
    @classmethod
    def lowercase_email(cls, v: str) -> str:
        return v.lower() if v else v


class VendorTokenResponse(BaseSchema):
    """Vendor authentication token response"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    vendor: "VendorResponse"


# === Vendor CRUD Schemas ===

class VendorCreate(BaseSchema):
    """Admin: Create vendor account"""
    email: EmailStr
    password: str = Field(..., min_length=8)
    business_name: str = Field(..., min_length=2, max_length=100)
    category: VendorCategory
    subcategories: List[str] = Field(default_factory=list)
    description: Optional[str] = None
    short_description: Optional[str] = None
    tagline: Optional[str] = None
    owner_first_name: str
    owner_last_name: str
    owner_phone: str
    owner_email: Optional[EmailStr] = None
    address: Optional[AddressCreate] = None
    contact: Optional[ContactCreate] = None
    social_links: Optional[SocialLinksCreate] = None
    operating_hours: Optional[OperatingHoursCreate] = None
    amenities: List[str] = Field(default_factory=list)
    services: List[str] = Field(default_factory=list)
    features: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    cancellation_policy: CancellationPolicy = CancellationPolicy.MODERATE
    languages_spoken: List[str] = Field(default_factory=lambda: ["English"])
    
    @field_validator("email", mode="before")
    @classmethod
    def lowercase_email(cls, v: str) -> str:
        return v.lower() if v else v


class VendorUpdate(BaseSchema):
    """Update vendor profile"""
    business_name: Optional[str] = Field(None, min_length=2, max_length=100)
    category: Optional[VendorCategory] = None
    subcategories: Optional[List[str]] = None
    description: Optional[str] = None
    short_description: Optional[str] = None
    tagline: Optional[str] = None
    owner_first_name: Optional[str] = None
    owner_last_name: Optional[str] = None
    owner_phone: Optional[str] = None
    owner_email: Optional[EmailStr] = None
    address: Optional[AddressCreate] = None
    contact: Optional[ContactCreate] = None
    social_links: Optional[SocialLinksCreate] = None
    operating_hours: Optional[OperatingHoursCreate] = None
    amenities: Optional[List[str]] = None
    services: Optional[List[str]] = None
    features: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    cancellation_policy: Optional[CancellationPolicy] = None
    refund_policy: Optional[str] = None
    terms_and_conditions: Optional[str] = None
    languages_spoken: Optional[List[str]] = None
    price_range: Optional[PriceRangeCreate] = None
    notification_preferences: Optional[Dict[str, bool]] = None


class VendorPasswordChange(BaseSchema):
    """Change vendor password"""
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


class VendorPasswordReset(BaseSchema):
    """Reset vendor password"""
    token: str
    new_password: str = Field(..., min_length=8)


class VendorPasswordResetRequest(BaseSchema):
    """Request vendor password reset"""
    email: EmailStr


# === Vendor Response Schemas ===

class VendorMinimalResponse(BaseSchema):
    """Minimal vendor response for listings"""
    id: str
    business_name: str
    slug: str
    category: VendorCategory
    short_description: Optional[str] = None
    is_verified: bool
    is_featured: bool
    logo: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    rating: Optional[RatingResponse] = None
    price_range: Optional[PriceRangeCreate] = None


class VendorResponse(BaseSchema):
    """Full vendor response"""
    id: str
    email: str
    business_name: str
    slug: str
    category: VendorCategory
    subcategories: List[str] = Field(default_factory=list)
    description: Optional[str] = None
    short_description: Optional[str] = None
    tagline: Optional[str] = None
    owner_first_name: str
    owner_last_name: str
    owner_phone: str
    owner_email: Optional[str] = None
    status: AccountStatus
    is_verified: bool
    is_featured: bool
    is_premium: bool
    is_active: bool
    address: Optional[AddressResponse] = None
    contact: Optional[ContactResponse] = None
    social_links: Optional[SocialLinksResponse] = None
    operating_hours: Optional[OperatingHoursResponse] = None
    media: Optional[VendorMediaResponse] = None
    verification: Optional[VendorVerificationResponse] = None
    subscription: Optional[VendorSubscriptionResponse] = None
    rating: Optional[RatingResponse] = None
    analytics: Optional[VendorAnalyticsResponse] = None
    amenities: List[str] = Field(default_factory=list)
    services: List[str] = Field(default_factory=list)
    features: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    price_range: Optional[PriceRangeCreate] = None
    currency: str = "NGN"
    languages_spoken: List[str] = Field(default_factory=list)
    cancellation_policy: CancellationPolicy
    certifications: List[Dict[str, Any]] = Field(default_factory=list)
    awards: List[Dict[str, Any]] = Field(default_factory=list)
    stripe_connected: bool = False
    payout_enabled: bool = False
    notification_preferences: Dict[str, bool] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime
    last_login_at: Optional[datetime] = None
    verified_at: Optional[datetime] = None


class VendorPublicResponse(BaseSchema):
    """Public vendor profile (for customers)"""
    id: str
    business_name: str
    slug: str
    category: VendorCategory
    subcategories: List[str] = Field(default_factory=list)
    description: Optional[str] = None
    short_description: Optional[str] = None
    tagline: Optional[str] = None
    is_verified: bool
    is_featured: bool
    is_premium: bool
    address: Optional[AddressResponse] = None
    contact: Optional[ContactResponse] = None
    social_links: Optional[SocialLinksResponse] = None
    operating_hours: Optional[OperatingHoursResponse] = None
    media: Optional[VendorMediaResponse] = None
    rating: Optional[RatingResponse] = None
    amenities: List[str] = Field(default_factory=list)
    services: List[str] = Field(default_factory=list)
    features: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    price_range: Optional[PriceRangeCreate] = None
    currency: str = "NGN"
    languages_spoken: List[str] = Field(default_factory=list)
    cancellation_policy: CancellationPolicy
    created_at: datetime


# === Vendor Bank Account Schemas ===

class VendorBankAccountAdd(BankAccountCreate):
    """Add vendor bank account"""
    is_primary: bool = False


class VendorBankAccountResponse(BankAccountResponse):
    """Vendor bank account response"""
    id: str
    verified_at: Optional[datetime] = None


# === Vendor Commission Schemas ===

class VendorCommissionUpdate(CommissionCreate):
    """Update vendor commission"""
    pass


class VendorCommissionResponse(CommissionResponse):
    """Vendor commission response"""
    pass


# === Vendor Listing/Search Schemas ===

class VendorListParams(BaseSchema):
    """Vendor listing parameters"""
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=20, ge=1, le=100)
    search: Optional[str] = None
    category: Optional[VendorCategory] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    is_verified: Optional[bool] = None
    is_featured: Optional[bool] = None
    is_premium: Optional[bool] = None
    min_rating: Optional[float] = None
    max_price: Optional[float] = None
    amenities: Optional[List[str]] = None
    sort_by: str = "created_at"
    sort_order: str = "desc"
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    radius_km: Optional[float] = None  # For geo search


class VendorListResponse(PaginatedResponse[VendorMinimalResponse]):
    """Paginated vendor list response"""
    pass


# === Admin Vendor Schemas ===

class VendorStatusUpdate(BaseSchema):
    """Admin: Update vendor status"""
    status: AccountStatus
    reason: Optional[str] = None


class VendorFeatureToggle(BaseSchema):
    """Admin: Toggle vendor features"""
    is_featured: Optional[bool] = None
    is_premium: Optional[bool] = None
    is_verified: Optional[bool] = None


class VendorBulkAction(BaseSchema):
    """Admin: Bulk action on vendors"""
    vendor_ids: List[str]
    action: str  # activate, suspend, delete, feature
    reason: Optional[str] = None


# Update forward reference
VendorTokenResponse.model_rebuild()

