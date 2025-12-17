"""
Queska Backend - Experience Card Schemas
Pydantic schemas for shareable experience cards
"""

from datetime import datetime, date
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.core.constants import ExperienceStatus
from app.schemas.base import BaseSchema, PaginatedResponse
from app.schemas.experience import (
    TravelLocationSchema,
    TravelDatesResponse,
    TravelGroupResponse,
    ItineraryDayResponse,
    ExperiencePricingResponse,
)


# === Embedded Schemas ===

class CardOwnerSchema(BaseSchema):
    """Card owner info"""
    user_id: str
    name: str
    avatar_url: Optional[str] = None
    is_verified: bool = False


class CardOwnerPublicSchema(BaseSchema):
    """Public owner info (privacy-safe)"""
    name: str
    avatar_url: Optional[str] = None


class CardHighlightSchema(BaseSchema):
    """Experience highlight"""
    type: str
    name: str
    description: Optional[str] = None
    image_url: Optional[str] = None
    icon: Optional[str] = None


class CardLocationSchema(BaseSchema):
    """Real-time location"""
    name: str
    latitude: float
    longitude: float
    updated_at: datetime


class TravelTimeEstimateSchema(BaseSchema):
    """Travel time from viewer's location"""
    driving_time_minutes: Optional[int] = None
    driving_distance_km: Optional[float] = None
    flight_time_minutes: Optional[int] = None
    walking_time_minutes: Optional[int] = None
    friendly_distance: str = ""  # "45 km away", "4 hours drive"


class CardSettingsSchema(BaseSchema):
    """Card settings"""
    is_public: bool = False
    is_active: bool = True
    expires_at: Optional[datetime] = None
    show_owner_name: bool = True
    show_owner_avatar: bool = True
    show_prices: bool = False
    show_vendor_details: bool = True
    show_real_time_location: bool = False
    allow_cloning: bool = True
    theme: str = "default"
    cover_style: str = "full"
    accent_color: Optional[str] = None


class CardSettingsUpdate(BaseSchema):
    """Update card settings"""
    is_public: Optional[bool] = None
    is_active: Optional[bool] = None
    expires_at: Optional[datetime] = None
    show_owner_name: Optional[bool] = None
    show_owner_avatar: Optional[bool] = None
    show_prices: Optional[bool] = None
    show_vendor_details: Optional[bool] = None
    show_real_time_location: Optional[bool] = None
    allow_cloning: Optional[bool] = None
    theme: Optional[str] = None
    cover_style: Optional[str] = None
    accent_color: Optional[str] = None


class CardStatsSchema(BaseSchema):
    """Card statistics"""
    view_count: int = 0
    unique_viewers: int = 0
    share_count: int = 0
    clone_count: int = 0
    save_count: int = 0


# === Main Card Schemas ===

class ExperienceCardCreate(BaseSchema):
    """Create card (usually automatic after payment)"""
    experience_id: str
    settings: Optional[CardSettingsSchema] = None
    include_full_itinerary: bool = False


class ExperienceCardUpdate(BaseSchema):
    """Update card details"""
    title: Optional[str] = None
    description: Optional[str] = None
    tagline: Optional[str] = None
    cover_image: Optional[str] = None
    include_full_itinerary: Optional[bool] = None
    settings: Optional[CardSettingsUpdate] = None
    tags: Optional[List[str]] = None


class ExperienceCardResponse(BaseSchema):
    """Full card response (for owner)"""
    id: str = Field(alias="_id")
    experience_id: str
    
    # Identifiers
    card_code: str
    short_url: Optional[str] = None
    share_url: str
    qr_code_url: Optional[str] = None
    
    # Owner
    owner: CardOwnerSchema
    
    # Content
    title: str
    description: Optional[str] = None
    tagline: Optional[str] = None
    cover_image: Optional[str] = None
    images: List[str] = Field(default_factory=list)
    
    # Trip details
    destination: TravelLocationSchema
    origin: Optional[TravelLocationSchema] = None
    dates: TravelDatesResponse
    travelers: TravelGroupResponse
    
    # Highlights
    highlights: List[CardHighlightSchema] = Field(default_factory=list)
    
    # Itinerary (if included)
    itinerary: List[ItineraryDayResponse] = Field(default_factory=list)
    include_full_itinerary: bool = False
    
    # Pricing (if shown)
    pricing: Optional[ExperiencePricingResponse] = None
    
    # Status
    experience_status: ExperienceStatus
    is_active: bool = True
    
    # Real-time location
    owner_location: Optional[CardLocationSchema] = None
    
    # Settings
    settings: CardSettingsSchema
    
    # Stats
    stats: CardStatsSchema
    
    # Social
    liked_by_count: int = 0
    saved_by_count: int = 0
    is_liked_by_me: bool = False
    is_saved_by_me: bool = False
    
    # Tags
    tags: List[str] = Field(default_factory=list)
    
    # AI content
    ai_description: Optional[str] = None
    ai_recommendations: List[str] = Field(default_factory=list)
    ai_travel_tips: List[str] = Field(default_factory=list)
    
    # Timestamps
    created_at: datetime
    updated_at: datetime
    
    # Trip status
    days_until_trip: int = 0
    is_trip_ongoing: bool = False

    class Config:
        populate_by_name = True


class ExperienceCardPublicResponse(BaseSchema):
    """Public card view (for sharing)"""
    card_code: str
    share_url: str
    
    # Owner (privacy-safe)
    owner: Optional[CardOwnerPublicSchema] = None
    
    # Content
    title: str
    description: Optional[str] = None
    tagline: Optional[str] = None
    cover_image: Optional[str] = None
    images: List[str] = Field(default_factory=list)
    
    # Trip details
    destination_name: str
    destination_city: str
    destination_country: str
    
    # Dates
    start_date: date
    end_date: date
    total_days: int
    
    # Travelers
    travelers_count: int
    
    # Highlights
    highlights: List[CardHighlightSchema] = Field(default_factory=list)
    
    # Simple itinerary (if allowed)
    itinerary_summary: Optional[List[Dict[str, Any]]] = None
    
    # Pricing (if shown)
    total_price: Optional[float] = None
    price_per_person: Optional[float] = None
    currency: str = "NGN"
    
    # Real-time location (if allowed)
    owner_location: Optional[CardLocationSchema] = None
    distance_from_me: Optional[TravelTimeEstimateSchema] = None
    
    # Stats
    view_count: int = 0
    share_count: int = 0
    
    # Cloning
    can_clone: bool = True
    
    # Tags
    tags: List[str] = Field(default_factory=list)
    
    # AI tips
    travel_tips: List[str] = Field(default_factory=list)
    
    # Trip status
    days_until_trip: int = 0
    is_trip_ongoing: bool = False
    trip_status: str = "upcoming"  # upcoming, ongoing, completed


class ExperienceCardSummary(BaseSchema):
    """Card summary for lists"""
    id: str = Field(alias="_id")
    card_code: str
    title: str
    cover_image: Optional[str] = None
    destination_city: str
    destination_country: str
    start_date: date
    end_date: date
    total_days: int
    travelers_count: int
    highlights_count: int
    view_count: int
    is_public: bool
    is_active: bool
    created_at: datetime

    class Config:
        populate_by_name = True


# === Location Update ===

class UpdateLocationRequest(BaseSchema):
    """Update owner's real-time location"""
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    accuracy: Optional[float] = None


class LocationResponse(BaseSchema):
    """Location update response"""
    success: bool
    updated_at: datetime
    is_sharing: bool


# === View Card ===

class ViewCardRequest(BaseSchema):
    """Request to view a card"""
    viewer_latitude: Optional[float] = None
    viewer_longitude: Optional[float] = None


class ViewCardResponse(BaseSchema):
    """View card response with distance info"""
    card: ExperienceCardPublicResponse
    travel_estimate: Optional[TravelTimeEstimateSchema] = None
    viewer_distance_km: Optional[float] = None
    viewer_message: Optional[str] = None  # "45 km away", "4 hours drive from you"


# === Share Card ===

class ShareCardRequest(BaseSchema):
    """Share card with others"""
    emails: List[str] = Field(default_factory=list)
    phone_numbers: List[str] = Field(default_factory=list)
    message: Optional[str] = None
    share_via: str = "link"  # link, email, sms, whatsapp


class ShareCardResponse(BaseSchema):
    """Share response"""
    share_url: str
    card_code: str
    shared_with_count: int
    share_method: str


# === Clone Card ===

class CloneCardRequest(BaseSchema):
    """Clone an experience from card"""
    new_start_date: date
    travelers: Optional[Dict[str, int]] = None  # {adults: 2, children: 1}
    adjust_dates_proportionally: bool = True  # Adjust all item dates relative to new start


class CloneCardResponse(BaseSchema):
    """Clone response"""
    new_experience_id: str
    new_experience_title: str
    original_card_code: str
    status: str  # draft or pending_payment
    estimated_total: float
    currency: str = "NGN"
    requires_payment: bool = True
    checkout_url: Optional[str] = None


# === Interactions ===

class LikeCardResponse(BaseSchema):
    """Like/unlike response"""
    is_liked: bool
    total_likes: int


class SaveCardResponse(BaseSchema):
    """Save/unsave response"""
    is_saved: bool
    total_saves: int


# === Search/Filter ===

class CardSearchFilters(BaseSchema):
    """Filters for searching public cards"""
    destination_city: Optional[str] = None
    destination_country: Optional[str] = None
    start_date_from: Optional[date] = None
    start_date_to: Optional[date] = None
    min_travelers: Optional[int] = None
    max_travelers: Optional[int] = None
    min_days: Optional[int] = None
    max_days: Optional[int] = None
    tags: Optional[List[str]] = None
    interests: Optional[List[str]] = None
    near_latitude: Optional[float] = None
    near_longitude: Optional[float] = None
    max_distance_km: Optional[float] = None


# === Pagination ===

class PaginatedCardsResponse(PaginatedResponse):
    """Paginated cards list"""
    data: List[ExperienceCardSummary]


class PaginatedPublicCardsResponse(PaginatedResponse):
    """Paginated public cards"""
    data: List[ExperienceCardPublicResponse]


# === QR Code ===

class GenerateQRCodeRequest(BaseSchema):
    """Generate QR code for card"""
    size: int = Field(default=256, ge=128, le=1024)
    format: str = "png"  # png, svg
    include_logo: bool = True


class GenerateQRCodeResponse(BaseSchema):
    """QR code response"""
    qr_code_url: str
    card_code: str
    share_url: str

