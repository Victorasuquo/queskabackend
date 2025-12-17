"""
Queska Backend - Activity Schemas
Pydantic schemas for activities, tours, and experiences
"""

from datetime import date, datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

from app.schemas.base import BaseSchema, PaginatedResponse


# ================================================================
# EMBEDDED SCHEMAS
# ================================================================

class ActivityLocationSchema(BaseSchema):
    """Activity location"""
    name: str
    address: Optional[str] = None
    city: str
    state: Optional[str] = None
    country: str = "Nigeria"
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    meeting_point: Optional[str] = None
    meeting_point_details: Optional[str] = None


class ActivityDurationSchema(BaseSchema):
    """Duration info"""
    minutes: int
    hours: Optional[float] = None
    days: Optional[int] = None
    display_text: str
    is_flexible: bool = False


class ActivityScheduleSchema(BaseSchema):
    """Schedule info"""
    available_days: List[str] = Field(default_factory=list)
    start_times: List[str] = Field(default_factory=list)
    blackout_dates: List[str] = Field(default_factory=list)
    seasonal: bool = False
    season_start: Optional[str] = None
    season_end: Optional[str] = None


class ActivityPricingSchema(BaseSchema):
    """Pricing info"""
    currency: str = "NGN"
    adult_price: float
    child_price: Optional[float] = None
    infant_price: Optional[float] = None
    group_price: Optional[float] = None
    private_price: Optional[float] = None
    pricing_type: str = "per_person"
    from_price: float
    original_price: Optional[float] = None
    discount_percentage: Optional[float] = None


class ActivityCapacitySchema(BaseSchema):
    """Capacity info"""
    min_participants: int = 1
    max_participants: int = 20
    max_per_booking: int = 10


class ActivityInclusionsSchema(BaseSchema):
    """What's included"""
    included: List[str] = Field(default_factory=list)
    excluded: List[str] = Field(default_factory=list)
    bring_items: List[str] = Field(default_factory=list)
    provided_items: List[str] = Field(default_factory=list)


class ActivityRequirementsSchema(BaseSchema):
    """Requirements"""
    min_age: Optional[int] = None
    max_age: Optional[int] = None
    fitness_level: Optional[str] = None
    skill_level: Optional[str] = None
    health_restrictions: List[str] = Field(default_factory=list)
    not_suitable_for: List[str] = Field(default_factory=list)


class ActivityPoliciesSchema(BaseSchema):
    """Policies"""
    cancellation_policy: str = "moderate"
    cancellation_deadline_hours: int = 24
    instant_confirmation: bool = True
    mobile_ticket: bool = True
    booking_cutoff_hours: int = 2


class ActivityRatingSchema(BaseSchema):
    """Rating info"""
    average: float = 0.0
    count: int = 0


class ActivityProviderSchema(BaseSchema):
    """Provider info"""
    vendor_id: Optional[str] = None
    name: str
    logo: Optional[str] = None
    languages: List[str] = Field(default_factory=list)
    is_verified: bool = False


# ================================================================
# CREATE/UPDATE SCHEMAS
# ================================================================

class ActivityLocationCreate(BaseSchema):
    """Create activity location"""
    name: str = Field(..., min_length=1, max_length=200)
    address: Optional[str] = None
    city: str = Field(..., min_length=1, max_length=100)
    state: Optional[str] = None
    country: str = "Nigeria"
    postal_code: Optional[str] = None
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    meeting_point: Optional[str] = None
    meeting_point_details: Optional[str] = None


class ActivityDurationCreate(BaseSchema):
    """Create duration"""
    minutes: int = Field(..., ge=15, le=43200)  # 15 min to 30 days
    display_text: str = Field(..., max_length=50)
    is_flexible: bool = False


class ActivityPricingCreate(BaseSchema):
    """Create pricing"""
    currency: str = Field("NGN", max_length=3)
    adult_price: float = Field(..., ge=0)
    child_price: Optional[float] = Field(None, ge=0)
    infant_price: Optional[float] = Field(None, ge=0)
    group_price: Optional[float] = Field(None, ge=0)
    group_min_size: Optional[int] = Field(None, ge=2)
    group_max_size: Optional[int] = Field(None, ge=2)
    private_price: Optional[float] = Field(None, ge=0)
    pricing_type: str = Field("per_person", pattern="^(per_person|per_group|flat_rate)$")


class ActivityCreate(BaseSchema):
    """Create activity"""
    name: str = Field(..., min_length=3, max_length=200)
    short_description: str = Field(..., min_length=10, max_length=300)
    description: str = Field(..., min_length=50, max_length=5000)
    
    category: str = Field(..., pattern="^(tours|adventure|cultural|food|wellness|entertainment|nature|water|classes|nightlife|shopping|transportation|other)$")
    subcategory: Optional[str] = None
    activity_type: str = Field("experience", pattern="^(tour|class|workshop|adventure|show|tasting|experience|excursion|transfer)$")
    tags: List[str] = Field(default_factory=list, max_length=10)
    
    location: ActivityLocationCreate
    duration: ActivityDurationCreate
    pricing: ActivityPricingCreate
    
    # Optional schedule
    schedule: Optional[ActivityScheduleSchema] = None
    
    # Capacity
    min_participants: int = Field(1, ge=1)
    max_participants: int = Field(20, ge=1, le=1000)
    
    # Inclusions
    included: List[str] = Field(default_factory=list)
    excluded: List[str] = Field(default_factory=list)
    bring_items: List[str] = Field(default_factory=list)
    
    # Requirements
    min_age: Optional[int] = Field(None, ge=0, le=100)
    max_age: Optional[int] = Field(None, ge=0, le=100)
    fitness_level: Optional[str] = Field(None, pattern="^(easy|moderate|challenging|extreme)$")
    
    # Highlights
    highlights: List[str] = Field(default_factory=list, max_length=10)
    
    # Media
    cover_image: Optional[str] = None
    images: List[str] = Field(default_factory=list, max_length=20)
    video_url: Optional[str] = None
    
    # Policies
    cancellation_policy: str = Field("moderate", pattern="^(free|flexible|moderate|strict|non_refundable)$")
    cancellation_deadline_hours: int = Field(24, ge=0, le=168)
    instant_confirmation: bool = True
    
    # Languages
    available_languages: List[str] = Field(default_factory=lambda: ["English"])
    
    # Accessibility
    wheelchair_accessible: bool = False
    accessibility_info: Optional[str] = None


class ActivityUpdate(BaseSchema):
    """Update activity"""
    name: Optional[str] = Field(None, min_length=3, max_length=200)
    short_description: Optional[str] = Field(None, min_length=10, max_length=300)
    description: Optional[str] = Field(None, min_length=50, max_length=5000)
    
    category: Optional[str] = None
    subcategory: Optional[str] = None
    activity_type: Optional[str] = None
    tags: Optional[List[str]] = None
    
    location: Optional[ActivityLocationCreate] = None
    duration: Optional[ActivityDurationCreate] = None
    pricing: Optional[ActivityPricingCreate] = None
    schedule: Optional[ActivityScheduleSchema] = None
    
    min_participants: Optional[int] = None
    max_participants: Optional[int] = None
    
    included: Optional[List[str]] = None
    excluded: Optional[List[str]] = None
    bring_items: Optional[List[str]] = None
    
    min_age: Optional[int] = None
    fitness_level: Optional[str] = None
    
    highlights: Optional[List[str]] = None
    
    cover_image: Optional[str] = None
    images: Optional[List[str]] = None
    video_url: Optional[str] = None
    
    cancellation_policy: Optional[str] = None
    cancellation_deadline_hours: Optional[int] = None
    instant_confirmation: Optional[bool] = None
    
    available_languages: Optional[List[str]] = None
    wheelchair_accessible: Optional[bool] = None
    
    is_active: Optional[bool] = None


# ================================================================
# RESPONSE SCHEMAS
# ================================================================

class ActivityResponse(BaseSchema):
    """Activity response"""
    id: str
    name: str
    slug: str
    short_description: str
    description: str
    
    category: str
    subcategory: Optional[str] = None
    activity_type: str
    tags: List[str] = Field(default_factory=list)
    
    location: ActivityLocationSchema
    duration: ActivityDurationSchema
    pricing: ActivityPricingSchema
    capacity: ActivityCapacitySchema
    
    inclusions: ActivityInclusionsSchema
    requirements: ActivityRequirementsSchema
    policies: ActivityPoliciesSchema
    
    highlights: List[str] = Field(default_factory=list)
    
    cover_image: Optional[str] = None
    images: List[str] = Field(default_factory=list)
    video_url: Optional[str] = None
    
    provider: Optional[ActivityProviderSchema] = None
    rating: ActivityRatingSchema
    
    source: str = "internal"
    external_url: Optional[str] = None
    
    available_languages: List[str] = Field(default_factory=list)
    wheelchair_accessible: bool = False
    
    is_featured: bool = False
    is_popular: bool = False
    
    vendor_id: Optional[str] = None
    
    booking_count: int = 0
    
    created_at: datetime


class ActivityListResponse(BaseSchema):
    """Simplified activity for lists"""
    id: str
    name: str
    slug: str
    short_description: str
    category: str
    
    city: str
    country: str
    
    duration_text: str
    from_price: float
    currency: str
    
    cover_image: Optional[str] = None
    rating: float = 0.0
    review_count: int = 0
    
    is_featured: bool = False
    instant_confirmation: bool = True
    free_cancellation: bool = False
    
    provider_name: Optional[str] = None
    source: str = "internal"


class PaginatedActivitiesResponse(PaginatedResponse):
    """Paginated activities"""
    data: List[ActivityListResponse]


# ================================================================
# AVAILABILITY SCHEMAS
# ================================================================

class AvailabilitySlot(BaseSchema):
    """Single availability slot"""
    id: str
    date: date
    start_time: str
    end_time: Optional[str] = None
    total_spots: int
    remaining_spots: int
    price: Optional[float] = None
    is_available: bool = True


class AvailabilityRequest(BaseSchema):
    """Check availability"""
    activity_id: str
    start_date: date
    end_date: date
    participants: int = Field(1, ge=1, le=100)


class AvailabilityResponse(BaseSchema):
    """Availability response"""
    activity_id: str
    slots: List[AvailabilitySlot]


# ================================================================
# BOOKING SCHEMAS
# ================================================================

class ParticipantInfo(BaseSchema):
    """Participant details"""
    name: str
    age: Optional[int] = None
    special_requirements: Optional[str] = None


class ActivityBookingCreate(BaseSchema):
    """Create booking"""
    activity_id: str
    availability_id: Optional[str] = None
    
    activity_date: date
    start_time: str
    
    adults: int = Field(1, ge=1, le=50)
    children: int = Field(0, ge=0, le=20)
    infants: int = Field(0, ge=0, le=10)
    
    participants: List[ParticipantInfo] = Field(default_factory=list)
    special_requirements: Optional[str] = None
    
    contact_name: str = Field(..., min_length=2, max_length=100)
    contact_email: str
    contact_phone: str
    
    experience_id: Optional[str] = None  # If part of experience
    
    @field_validator("activity_date")
    @classmethod
    def date_not_in_past(cls, v):
        if v < date.today():
            raise ValueError("Activity date cannot be in the past")
        return v


class ActivityBookingResponse(BaseSchema):
    """Booking response"""
    id: str
    booking_reference: str
    
    activity_id: str
    activity_name: str
    
    activity_date: date
    start_time: str
    
    adults: int
    children: int
    infants: int
    total_participants: int
    
    unit_price: float
    subtotal: float
    fees: float
    taxes: float
    discount: float
    total_price: float
    currency: str
    
    status: str
    payment_status: str
    
    confirmation_code: Optional[str] = None
    voucher_url: Optional[str] = None
    qr_code_url: Optional[str] = None
    
    contact_name: str
    contact_email: str
    contact_phone: str
    
    created_at: datetime
    confirmed_at: Optional[datetime] = None


class PaginatedBookingsResponse(PaginatedResponse):
    """Paginated bookings"""
    data: List[ActivityBookingResponse]


class BookingCancelRequest(BaseSchema):
    """Cancel booking"""
    reason: Optional[str] = None


# ================================================================
# REVIEW SCHEMAS
# ================================================================

class ActivityReviewCreate(BaseSchema):
    """Create review"""
    activity_id: str
    booking_id: Optional[str] = None
    
    overall_rating: float = Field(..., ge=1, le=5)
    ratings: Dict[str, float] = Field(default_factory=dict)
    
    title: Optional[str] = Field(None, max_length=100)
    content: str = Field(..., min_length=20, max_length=2000)
    
    activity_date: Optional[date] = None
    travel_type: Optional[str] = Field(None, pattern="^(solo|couple|family|friends|business)$")
    
    photos: List[str] = Field(default_factory=list, max_length=5)


class ActivityReviewResponse(BaseSchema):
    """Review response"""
    id: str
    activity_id: str
    user_id: str
    user_name: str
    user_avatar: Optional[str] = None
    
    overall_rating: float
    ratings: Dict[str, float]
    
    title: Optional[str] = None
    content: str
    
    activity_date: Optional[date] = None
    travel_type: Optional[str] = None
    
    photos: List[str] = Field(default_factory=list)
    
    vendor_response: Optional[str] = None
    vendor_response_at: Optional[datetime] = None
    
    helpful_count: int = 0
    
    created_at: datetime


class PaginatedReviewsResponse(PaginatedResponse):
    """Paginated reviews"""
    data: List[ActivityReviewResponse]


# ================================================================
# SEARCH SCHEMAS
# ================================================================

class ActivitySearchRequest(BaseSchema):
    """Search activities"""
    destination: Optional[str] = None
    category: Optional[str] = None
    activity_date: Optional[date] = None
    
    price_min: Optional[float] = Field(None, ge=0)
    price_max: Optional[float] = Field(None, ge=0)
    
    duration_min: Optional[int] = Field(None, ge=0)  # minutes
    duration_max: Optional[int] = Field(None, ge=0)
    
    rating_min: Optional[float] = Field(None, ge=1, le=5)
    
    tags: Optional[List[str]] = None
    
    free_cancellation: Optional[bool] = None
    instant_confirmation: Optional[bool] = None
    
    sort_by: str = Field("recommended", pattern="^(recommended|price_asc|price_desc|rating|popularity|newest)$")


class ActivitySearchResponse(BaseSchema):
    """Search results"""
    success: bool
    activities: List[ActivityListResponse]
    total: int
    filters_applied: Dict[str, Any] = Field(default_factory=dict)
    providers_used: List[str] = Field(default_factory=list)


# ================================================================
# WISHLIST SCHEMAS
# ================================================================

class WishlistAddRequest(BaseSchema):
    """Add to wishlist"""
    activity_id: str
    notes: Optional[str] = None
    planned_date: Optional[date] = None


class WishlistResponse(BaseSchema):
    """Wishlist item"""
    id: str
    activity: ActivityListResponse
    notes: Optional[str] = None
    planned_date: Optional[date] = None
    added_at: datetime


class PaginatedWishlistResponse(PaginatedResponse):
    """Paginated wishlist"""
    data: List[WishlistResponse]

