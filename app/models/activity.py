"""
Queska Backend - Activity Model
Activities, tours, experiences, and things to do
"""

from datetime import datetime, date, time
from typing import Any, Dict, List, Optional

from beanie import Document, Indexed, PydanticObjectId
from pydantic import BaseModel, Field

from app.models.base import BaseDocument


# === Embedded Models ===

class ActivityLocation(BaseModel):
    """Activity location details"""
    name: str
    address: Optional[str] = None
    city: str
    state: Optional[str] = None
    country: str = "Nigeria"
    postal_code: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    meeting_point: Optional[str] = None  # Where to meet for the activity
    meeting_point_details: Optional[str] = None


class ActivityDuration(BaseModel):
    """Duration information"""
    minutes: int
    hours: Optional[float] = None
    days: Optional[int] = None
    display_text: str  # "2 hours", "Full day", "3 days"
    is_flexible: bool = False


class ActivitySchedule(BaseModel):
    """Scheduling information"""
    available_days: List[str] = Field(default_factory=list)  # ["monday", "tuesday", ...]
    start_times: List[str] = Field(default_factory=list)  # ["09:00", "14:00"]
    end_time: Optional[str] = None
    blackout_dates: List[date] = Field(default_factory=list)
    seasonal: bool = False
    season_start: Optional[str] = None  # "March"
    season_end: Optional[str] = None  # "October"


class ActivityPricing(BaseModel):
    """Pricing information"""
    currency: str = "NGN"
    
    # Base pricing
    adult_price: float
    child_price: Optional[float] = None
    infant_price: Optional[float] = None
    
    # Group pricing
    group_price: Optional[float] = None
    group_min_size: Optional[int] = None
    group_max_size: Optional[int] = None
    
    # Private options
    private_price: Optional[float] = None
    
    # Pricing type
    pricing_type: str = "per_person"  # per_person, per_group, flat_rate
    
    # Dynamic pricing
    weekend_surcharge: Optional[float] = None
    holiday_surcharge: Optional[float] = None
    
    # Display
    from_price: float  # Lowest price for display
    original_price: Optional[float] = None  # For showing discounts
    discount_percentage: Optional[float] = None


class ActivityCapacity(BaseModel):
    """Capacity and booking limits"""
    min_participants: int = 1
    max_participants: int = 20
    max_per_booking: int = 10
    remaining_spots: Optional[int] = None


class ActivityInclusions(BaseModel):
    """What's included/excluded"""
    included: List[str] = Field(default_factory=list)
    excluded: List[str] = Field(default_factory=list)
    bring_items: List[str] = Field(default_factory=list)  # What to bring
    provided_items: List[str] = Field(default_factory=list)  # Equipment provided


class ActivityRequirements(BaseModel):
    """Requirements and restrictions"""
    min_age: Optional[int] = None
    max_age: Optional[int] = None
    fitness_level: Optional[str] = None  # "easy", "moderate", "challenging", "extreme"
    skill_level: Optional[str] = None  # "beginner", "intermediate", "advanced"
    height_min_cm: Optional[int] = None
    weight_max_kg: Optional[int] = None
    health_restrictions: List[str] = Field(default_factory=list)
    not_suitable_for: List[str] = Field(default_factory=list)
    prerequisites: List[str] = Field(default_factory=list)


class ActivityPolicies(BaseModel):
    """Booking and cancellation policies"""
    cancellation_policy: str = "moderate"  # free, flexible, moderate, strict, non_refundable
    cancellation_deadline_hours: int = 24
    full_refund_deadline_hours: Optional[int] = None
    partial_refund_percentage: Optional[float] = None
    
    instant_confirmation: bool = True
    mobile_ticket: bool = True
    printed_ticket_required: bool = False
    
    booking_cutoff_hours: int = 2  # How many hours before activity can be booked
    advance_booking_days: int = 365  # How far in advance can be booked


class ActivityRating(BaseModel):
    """Rating information"""
    average: float = 0.0
    count: int = 0
    distribution: Dict[str, int] = Field(default_factory=dict)  # {"5": 100, "4": 50, ...}


class ActivityProvider(BaseModel):
    """Activity provider/operator info"""
    vendor_id: Optional[str] = None
    name: str
    description: Optional[str] = None
    logo: Optional[str] = None
    contact_phone: Optional[str] = None
    contact_email: Optional[str] = None
    languages: List[str] = Field(default_factory=list)
    response_time: Optional[str] = None  # "Within 24 hours"
    years_experience: Optional[int] = None
    is_verified: bool = False


class ActivityExternalIds(BaseModel):
    """IDs from external providers"""
    booking_com_id: Optional[str] = None
    expedia_id: Optional[str] = None
    viator_id: Optional[str] = None
    getyourguide_id: Optional[str] = None


# === Main Document ===

class Activity(BaseDocument):
    """
    Activity/tour/experience document.
    
    Can be:
    - Vendor-created local activities
    - Admin-curated activities
    - Aggregated from external APIs
    """
    
    # Basic info
    name: Indexed(str)
    slug: Indexed(str, unique=True)
    short_description: str
    description: str
    
    # Category and type
    category: Indexed(str)  # tours, adventure, cultural, food, wellness, entertainment, etc.
    subcategory: Optional[str] = None
    activity_type: str = "experience"  # tour, class, workshop, adventure, show, tasting, etc.
    tags: List[str] = Field(default_factory=list)
    
    # Location
    location: ActivityLocation
    
    # Duration and schedule
    duration: ActivityDuration
    schedule: ActivitySchedule = Field(default_factory=ActivitySchedule)
    
    # Pricing
    pricing: ActivityPricing
    
    # Capacity
    capacity: ActivityCapacity = Field(default_factory=ActivityCapacity)
    
    # What's included
    inclusions: ActivityInclusions = Field(default_factory=ActivityInclusions)
    
    # Requirements
    requirements: ActivityRequirements = Field(default_factory=ActivityRequirements)
    
    # Policies
    policies: ActivityPolicies = Field(default_factory=ActivityPolicies)
    
    # Highlights
    highlights: List[str] = Field(default_factory=list)
    itinerary: List[Dict[str, Any]] = Field(default_factory=list)  # Step-by-step itinerary
    
    # Media
    cover_image: Optional[str] = None
    images: List[str] = Field(default_factory=list)
    video_url: Optional[str] = None
    
    # Provider
    provider: Optional[ActivityProvider] = None
    
    # Rating
    rating: ActivityRating = Field(default_factory=ActivityRating)
    
    # External IDs
    external_ids: ActivityExternalIds = Field(default_factory=ActivityExternalIds)
    source: str = "internal"  # internal, booking_com, expedia, viator
    external_url: Optional[str] = None  # Deep link for external activities
    
    # Accessibility
    wheelchair_accessible: bool = False
    accessibility_info: Optional[str] = None
    
    # Languages
    available_languages: List[str] = Field(default_factory=lambda: ["English"])
    audio_guide_languages: List[str] = Field(default_factory=list)
    
    # Status
    is_active: bool = True
    is_featured: bool = False
    is_popular: bool = False
    is_new: bool = True
    
    # Vendor relationship
    vendor_id: Optional[Indexed(str)] = None
    
    # Admin
    created_by: Optional[str] = None
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    
    # Stats
    view_count: int = 0
    booking_count: int = 0
    wishlist_count: int = 0
    
    class Settings:
        name = "activities"
        indexes = [
            "name",
            "slug",
            "category",
            "vendor_id",
            "is_active",
            "is_featured",
            "is_popular",
            "source",
            "location.city",
            "location.country",
            [("rating.average", -1)],
            [("pricing.from_price", 1)],
            [("booking_count", -1)],
            [("created_at", -1)],
        ]


class ActivityAvailability(BaseDocument):
    """
    Availability slots for activities.
    For activities with specific time slots and limited capacity.
    """
    activity_id: Indexed(str)
    
    # Date and time
    date: Indexed(date)
    start_time: str  # "09:00"
    end_time: Optional[str] = None
    
    # Capacity
    total_spots: int
    booked_spots: int = 0
    remaining_spots: int
    
    # Pricing (can override base pricing)
    price_override: Optional[float] = None
    
    # Status
    is_available: bool = True
    is_sold_out: bool = False
    
    # Booking IDs
    booking_ids: List[str] = Field(default_factory=list)
    
    class Settings:
        name = "activity_availability"
        indexes = [
            "activity_id",
            "date",
            "is_available",
            [("activity_id", 1), ("date", 1), ("start_time", 1)],
        ]


class ActivityBooking(BaseDocument):
    """
    Activity booking record.
    """
    activity_id: Indexed(str)
    availability_id: Optional[str] = None
    user_id: Indexed(str)
    experience_id: Optional[str] = None  # If part of an experience
    
    # Booking details
    booking_reference: Indexed(str, unique=True)
    
    # Date and time
    activity_date: date
    start_time: str
    
    # Participants
    adults: int = 1
    children: int = 0
    infants: int = 0
    total_participants: int = 1
    
    # Participant details
    participant_names: List[str] = Field(default_factory=list)
    special_requirements: Optional[str] = None
    
    # Pricing
    unit_price: float
    subtotal: float
    fees: float = 0.0
    taxes: float = 0.0
    discount: float = 0.0
    total_price: float
    currency: str = "NGN"
    
    # Contact
    contact_name: str
    contact_email: str
    contact_phone: str
    
    # Status
    status: str = "pending"  # pending, confirmed, cancelled, completed, no_show
    payment_status: str = "pending"  # pending, paid, refunded, partially_refunded
    
    # Confirmation
    confirmation_code: Optional[str] = None
    voucher_url: Optional[str] = None
    qr_code_url: Optional[str] = None
    
    # External booking (for API activities)
    external_booking_id: Optional[str] = None
    external_booking_url: Optional[str] = None
    
    # Timestamps
    confirmed_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Cancellation
    cancellation_reason: Optional[str] = None
    refund_amount: Optional[float] = None
    refund_status: Optional[str] = None
    
    class Settings:
        name = "activity_bookings"
        indexes = [
            "activity_id",
            "user_id",
            "booking_reference",
            "status",
            "activity_date",
            "experience_id",
            [("created_at", -1)],
        ]


class ActivityReview(BaseDocument):
    """
    User reviews for activities.
    """
    activity_id: Indexed(str)
    user_id: Indexed(str)
    booking_id: Optional[str] = None
    
    # Rating
    overall_rating: float = Field(..., ge=1, le=5)
    ratings: Dict[str, float] = Field(default_factory=dict)  # {"guide": 5, "value": 4, "organization": 5}
    
    # Review content
    title: Optional[str] = None
    content: str
    
    # Context
    activity_date: Optional[date] = None
    travel_type: Optional[str] = None  # solo, couple, family, friends, business
    
    # Media
    photos: List[str] = Field(default_factory=list)
    
    # Moderation
    is_approved: bool = False
    is_featured: bool = False
    
    # Response
    vendor_response: Optional[str] = None
    vendor_response_at: Optional[datetime] = None
    
    # Engagement
    helpful_count: int = 0
    
    class Settings:
        name = "activity_reviews"
        indexes = [
            "activity_id",
            "user_id",
            "booking_id",
            "is_approved",
            "is_featured",
            [("overall_rating", -1)],
            [("helpful_count", -1)],
            [("created_at", -1)],
        ]


class ActivityWishlist(BaseDocument):
    """
    User wishlist for activities.
    """
    user_id: Indexed(str)
    activity_id: Indexed(str)
    
    # Optional notes
    notes: Optional[str] = None
    planned_date: Optional[date] = None
    
    class Settings:
        name = "activity_wishlists"
        indexes = [
            [("user_id", 1), ("activity_id", 1)],
        ]

