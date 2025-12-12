"""
Queska Backend - Base Schemas
Common Pydantic schemas used across the application
"""

from datetime import datetime
from typing import Any, Dict, Generic, List, Optional, TypeVar

from pydantic import BaseModel, Field


# Type variable for generic schemas
T = TypeVar("T")


class BaseSchema(BaseModel):
    """Base schema with common configuration"""
    
    class Config:
        from_attributes = True
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


# === Common Response Schemas ===

class SuccessResponse(BaseSchema):
    """Generic success response"""
    success: bool = True
    message: str


class ErrorResponse(BaseSchema):
    """Generic error response"""
    success: bool = False
    error: str
    error_code: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class DeleteResponse(BaseSchema):
    """Delete operation response"""
    success: bool = True
    message: str = "Successfully deleted"
    id: str


class PaginatedResponse(BaseSchema, Generic[T]):
    """Generic paginated response"""
    items: List[T]
    total: int
    page: int
    limit: int
    pages: int
    has_next: bool
    has_prev: bool


class PaginationParams(BaseSchema):
    """Pagination parameters"""
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=20, ge=1, le=100)


# === Address Schemas ===

class AddressCreate(BaseSchema):
    """Common address creation schema"""
    label: str = "Home"
    street: Optional[str] = None
    city: str
    state: str
    country: str = "Nigeria"
    postal_code: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    is_primary: bool = True


class AddressResponse(AddressCreate):
    """Address response schema"""
    pass


class AddressUpdate(BaseSchema):
    """Address update schema"""
    label: Optional[str] = None
    street: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    postal_code: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    is_primary: Optional[bool] = None


# === Location Schemas ===

class GeoPointCreate(BaseSchema):
    """Geographic point creation"""
    type: str = "Point"
    coordinates: List[float]  # [longitude, latitude]


class GeoPointResponse(GeoPointCreate):
    """Geographic point response"""
    pass


class LocationCreate(BaseSchema):
    """Location creation schema"""
    name: str
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: str = "Nigeria"
    coordinates: Optional[GeoPointCreate] = None


class LocationResponse(LocationCreate):
    """Location response schema"""
    pass


# === Operating Hours Schemas ===

class DayHoursCreate(BaseSchema):
    """Single day hours"""
    is_open: bool = True
    open_time: Optional[str] = None  # "09:00"
    close_time: Optional[str] = None  # "17:00"
    breaks: List[Dict[str, str]] = Field(default_factory=list)  # [{"start": "12:00", "end": "13:00"}]


class OperatingHoursCreate(BaseSchema):
    """Operating hours for a week"""
    monday: Optional[DayHoursCreate] = None
    tuesday: Optional[DayHoursCreate] = None
    wednesday: Optional[DayHoursCreate] = None
    thursday: Optional[DayHoursCreate] = None
    friday: Optional[DayHoursCreate] = None
    saturday: Optional[DayHoursCreate] = None
    sunday: Optional[DayHoursCreate] = None
    timezone: str = "Africa/Lagos"
    special_hours: List[Dict[str, Any]] = Field(default_factory=list)


class OperatingHoursResponse(OperatingHoursCreate):
    """Operating hours response"""
    pass


# === Media Schemas ===

class MediaCreate(BaseSchema):
    """Media creation schema"""
    url: str
    type: str = "image"  # image, video, document
    title: Optional[str] = None
    description: Optional[str] = None
    thumbnail_url: Optional[str] = None
    size: Optional[int] = None
    mime_type: Optional[str] = None


class MediaResponse(MediaCreate):
    """Media response schema"""
    id: Optional[str] = None
    created_at: Optional[datetime] = None


class GalleryResponse(BaseSchema):
    """Gallery response"""
    images: List[MediaResponse] = Field(default_factory=list)
    videos: List[MediaResponse] = Field(default_factory=list)
    total: int = 0


# === Rating Schemas ===

class RatingCreate(BaseSchema):
    """Rating creation schema"""
    score: float = Field(..., ge=1, le=5)
    title: Optional[str] = None
    comment: Optional[str] = None


class RatingResponse(BaseSchema):
    """Rating summary response"""
    average: float = 0.0
    count: int = 0
    breakdown: Dict[str, int] = Field(default_factory=dict)


class RatingDetailResponse(RatingResponse):
    """Detailed rating response"""
    recent_reviews: List[Dict[str, Any]] = Field(default_factory=list)


# === Social Links Schemas ===

class SocialLinksCreate(BaseSchema):
    """Social links creation"""
    website: Optional[str] = None
    instagram: Optional[str] = None
    facebook: Optional[str] = None
    twitter: Optional[str] = None
    youtube: Optional[str] = None
    linkedin: Optional[str] = None
    tiktok: Optional[str] = None


class SocialLinksResponse(SocialLinksCreate):
    """Social links response"""
    pass


# === Bank Account Schemas ===

class BankAccountCreate(BaseSchema):
    """Bank account creation"""
    bank_name: str
    account_number: str
    account_name: str
    bank_code: Optional[str] = None
    is_default: bool = False


class BankAccountResponse(BaseSchema):
    """Bank account response (masked)"""
    id: str
    bank_name: str
    account_number: str  # Last 4 digits only
    account_name: str
    is_default: bool
    is_verified: bool = False


# === Contact Schemas ===

class ContactInfoCreate(BaseSchema):
    """Contact information"""
    email: Optional[str] = None
    phone: Optional[str] = None
    phone_country_code: Optional[str] = "+234"
    alternate_phone: Optional[str] = None
    whatsapp: Optional[str] = None


class ContactInfoResponse(ContactInfoCreate):
    """Contact info response"""
    pass


# === Search & Filter Schemas ===

class SearchParams(BaseSchema):
    """Common search parameters"""
    q: Optional[str] = None
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=20, ge=1, le=100)
    sort_by: str = "created_at"
    sort_order: str = "desc"


class DateRangeFilter(BaseSchema):
    """Date range filter"""
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class GeoFilter(BaseSchema):
    """Geographic filter"""
    latitude: float
    longitude: float
    radius_km: float = 10.0


# === Notification Schemas ===

class NotificationPreferences(BaseSchema):
    """Notification preferences"""
    email_enabled: bool = True
    push_enabled: bool = True
    sms_enabled: bool = False
    in_app_enabled: bool = True


# === Activity Log Schemas ===

class ActivityLogResponse(BaseSchema):
    """Activity log entry response"""
    id: str
    action: str
    description: str
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    created_at: datetime


# === Verification Schemas ===

class VerificationStatusResponse(BaseSchema):
    """Verification status response"""
    status: str
    submitted_at: Optional[datetime] = None
    verified_at: Optional[datetime] = None
    rejected_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None


# === Subscription Schemas ===

class SubscriptionResponse(BaseSchema):
    """Subscription status response"""
    plan: str
    started_at: datetime
    expires_at: Optional[datetime] = None
    is_active: bool
    auto_renew: bool
    features: List[str] = Field(default_factory=list)


# === Health Check Schemas ===

class HealthCheckResponse(BaseSchema):
    """Health check response"""
    status: str = "healthy"
    version: str
    timestamp: datetime
    services: Dict[str, str] = Field(default_factory=dict)
