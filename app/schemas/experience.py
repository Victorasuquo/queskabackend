"""
Queska Backend - Experience Schemas
Pydantic schemas for experience API requests and responses
"""

from datetime import datetime, date
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator, HttpUrl

from app.core.constants import ExperienceStatus, PaymentStatus
from app.schemas.base import BaseSchema, PaginatedResponse


# === Embedded Schemas ===

class TravelLocationSchema(BaseSchema):
    """Location schema"""
    name: str
    city: str
    state: Optional[str] = None
    country: str = "Nigeria"
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    place_id: Optional[str] = None
    timezone: str = "Africa/Lagos"


class TravelDatesCreate(BaseSchema):
    """Dates for creating experience"""
    start_date: date
    end_date: date
    flexible_dates: bool = False
    preferred_arrival_time: Optional[str] = None
    preferred_departure_time: Optional[str] = None
    
    @field_validator('end_date')
    @classmethod
    def end_after_start(cls, v, info):
        if 'start_date' in info.data and v < info.data['start_date']:
            raise ValueError('end_date must be after start_date')
        return v


class TravelDatesResponse(TravelDatesCreate):
    """Dates response"""
    pass


class TravelGroupCreate(BaseSchema):
    """Travelers/passengers create schema"""
    adults: int = Field(default=1, ge=1, le=20)
    children: int = Field(default=0, ge=0, le=10)
    infants: int = Field(default=0, ge=0, le=5)
    companion_names: List[str] = Field(default_factory=list)
    special_requirements: List[str] = Field(default_factory=list)


class TravelGroupResponse(TravelGroupCreate):
    """Travelers response"""
    total_passengers: int = 1


class ExperiencePreferencesSchema(BaseSchema):
    """Preferences schema"""
    interests: List[str] = Field(default_factory=list)
    travel_style: str = "mid-range"
    pace: str = "moderate"
    dietary_restrictions: List[str] = Field(default_factory=list)
    accessibility_needs: List[str] = Field(default_factory=list)
    preferred_cuisines: List[str] = Field(default_factory=list)
    avoid_categories: List[str] = Field(default_factory=list)
    max_walking_distance: Optional[float] = None
    preferred_transport: List[str] = Field(default_factory=list)


# === Experience Item Schemas ===

class ExperienceItemCreate(BaseSchema):
    """Create an item to add to experience"""
    type: str = Field(..., description="Type: accommodation, ride, event, place, activity, dining, flight")
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    
    # Vendor
    vendor_id: Optional[str] = None
    vendor_name: Optional[str] = None
    
    # Location
    location: Optional[TravelLocationSchema] = None
    
    # Timing
    scheduled_date: Optional[date] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    duration_minutes: Optional[int] = None
    
    # Pricing
    price_per_unit: float = Field(default=0.0, ge=0)
    quantity: int = Field(default=1, ge=1)
    currency: str = "NGN"
    is_free: bool = False
    
    # Media
    image_url: Optional[str] = None
    images: List[str] = Field(default_factory=list)
    
    # Type-specific details
    details: Dict[str, Any] = Field(default_factory=dict)
    
    # Notes
    notes: Optional[str] = None


class ExperienceItemUpdate(BaseSchema):
    """Update an item in experience"""
    name: Optional[str] = None
    description: Optional[str] = None
    scheduled_date: Optional[date] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    price_per_unit: Optional[float] = None
    quantity: Optional[int] = None
    notes: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class ExperienceItemResponse(BaseSchema):
    """Item response"""
    id: str
    type: str
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    
    vendor_id: Optional[str] = None
    vendor_name: Optional[str] = None
    
    location: Optional[TravelLocationSchema] = None
    
    scheduled_date: Optional[date] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    duration_minutes: Optional[int] = None
    
    price_per_unit: float = 0.0
    quantity: int = 1
    total_price: float = 0.0
    currency: str = "NGN"
    is_free: bool = False
    
    booking_status: str = "pending"
    booking_reference: Optional[str] = None
    
    image_url: Optional[str] = None
    images: List[str] = Field(default_factory=list)
    
    details: Dict[str, Any] = Field(default_factory=dict)
    
    travel_time_from_previous: Optional[int] = None
    distance_from_previous: Optional[float] = None
    
    notes: Optional[str] = None
    order: int = 0
    day_number: int = 1


# === Itinerary Schemas ===

class ItineraryDayResponse(BaseSchema):
    """Single day in itinerary"""
    day_number: int
    date: date
    title: Optional[str] = None
    description: Optional[str] = None
    items: List[ExperienceItemResponse] = Field(default_factory=list)
    total_cost: float = 0.0
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    weather_forecast: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None


# === Pricing Schemas ===

class ExperiencePricingResponse(BaseSchema):
    """Pricing breakdown"""
    currency: str = "NGN"
    
    accommodation_total: float = 0.0
    transportation_total: float = 0.0
    events_total: float = 0.0
    activities_total: float = 0.0
    dining_total: float = 0.0
    flights_total: float = 0.0
    
    items_subtotal: float = 0.0
    service_fee: float = 0.0
    service_fee_percentage: float = 5.0
    taxes: float = 0.0
    
    discount_amount: float = 0.0
    discount_code: Optional[str] = None
    
    grand_total: float = 0.0
    price_per_person: float = 0.0
    
    amount_paid: float = 0.0
    balance_due: float = 0.0
    payment_status: PaymentStatus = PaymentStatus.PENDING


# === Analytics Schemas ===

class ExperienceAnalyticsResponse(BaseSchema):
    """Experience analytics"""
    total_distance_km: float = 0.0
    total_travel_time_minutes: int = 0
    total_items: int = 0
    total_days: int = 0
    places_count: int = 0
    events_count: int = 0
    activities_count: int = 0
    dining_count: int = 0
    ai_summary: Optional[str] = None
    highlights: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)


# === Sharing Schemas ===

class ExperienceSharingSettings(BaseSchema):
    """Sharing settings update"""
    is_public: Optional[bool] = None
    is_shareable: Optional[bool] = None
    hide_prices: Optional[bool] = None
    hide_personal_details: Optional[bool] = None


class ExperienceSharingResponse(BaseSchema):
    """Sharing info response"""
    is_public: bool = False
    is_shareable: bool = True
    share_code: Optional[str] = None
    share_url: Optional[str] = None
    hide_prices: bool = False
    view_count: int = 0
    share_count: int = 0
    clone_count: int = 0


# === Main Experience Schemas ===

class ExperienceCreate(BaseSchema):
    """Create a new experience - Step 1"""
    title: str = Field(..., min_length=3, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    
    # Origin (where user is coming from)
    origin: Optional[TravelLocationSchema] = None
    
    # Destination (where they're going)
    destination: TravelLocationSchema
    
    # Dates
    dates: TravelDatesCreate
    
    # Passengers
    travelers: TravelGroupCreate = Field(default_factory=TravelGroupCreate)
    
    # Preferences
    preferences: ExperiencePreferencesSchema = Field(default_factory=ExperiencePreferencesSchema)
    
    # Optional
    cover_image: Optional[str] = None
    tags: List[str] = Field(default_factory=list)


class ExperienceUpdate(BaseSchema):
    """Update experience details"""
    title: Optional[str] = Field(None, min_length=3, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    origin: Optional[TravelLocationSchema] = None
    destination: Optional[TravelLocationSchema] = None
    dates: Optional[TravelDatesCreate] = None
    travelers: Optional[TravelGroupCreate] = None
    preferences: Optional[ExperiencePreferencesSchema] = None
    cover_image: Optional[str] = None
    tags: Optional[List[str]] = None


class ExperienceResponse(BaseSchema):
    """Full experience response"""
    id: str = Field(alias="_id")
    
    # Owner
    user_id: str
    user_name: Optional[str] = None
    
    # Agent
    agent_id: Optional[str] = None
    agent_name: Optional[str] = None
    created_by_agent: bool = False
    
    # Basic
    title: str
    slug: Optional[str] = None
    description: Optional[str] = None
    cover_image: Optional[str] = None
    images: List[str] = Field(default_factory=list)
    
    # Location
    origin: Optional[TravelLocationSchema] = None
    destination: TravelLocationSchema
    
    # Dates
    dates: TravelDatesResponse
    
    # Travelers
    travelers: TravelGroupResponse
    
    # Preferences
    preferences: ExperiencePreferencesSchema
    
    # Items
    items: List[ExperienceItemResponse] = Field(default_factory=list)
    items_count: int = 0
    
    # Itinerary
    itinerary: List[ItineraryDayResponse] = Field(default_factory=list)
    
    # Pricing
    pricing: ExperiencePricingResponse
    
    # Status
    status: ExperienceStatus = ExperienceStatus.DRAFT
    
    # Sharing
    sharing: ExperienceSharingResponse
    
    # Analytics
    analytics: ExperienceAnalyticsResponse
    
    # Experience Card
    experience_card_id: Optional[str] = None
    card_generated: bool = False
    
    # Cloning
    is_clone: bool = False
    cloned_from_card_code: Optional[str] = None
    
    # Tags
    tags: List[str] = Field(default_factory=list)
    categories: List[str] = Field(default_factory=list)
    
    # Timestamps
    created_at: datetime
    updated_at: datetime
    submitted_at: Optional[datetime] = None
    paid_at: Optional[datetime] = None
    
    # Computed
    total_days: int = 1
    is_upcoming: bool = True

    class Config:
        populate_by_name = True


class ExperienceSummaryResponse(BaseSchema):
    """Compact experience summary for lists"""
    id: str = Field(alias="_id")
    title: str
    cover_image: Optional[str] = None
    destination_city: str
    destination_country: str
    start_date: date
    end_date: date
    total_days: int
    travelers_count: int
    items_count: int
    total_price: float
    currency: str = "NGN"
    status: ExperienceStatus
    card_generated: bool = False
    share_code: Optional[str] = None
    created_at: datetime

    class Config:
        populate_by_name = True


# === Add Items Schemas ===

class AddAccommodationRequest(BaseSchema):
    """Add hotel/accommodation to experience"""
    vendor_id: Optional[str] = None
    name: str
    location: TravelLocationSchema
    check_in_date: date
    check_out_date: date
    room_type: str
    nights: int = Field(ge=1)
    price_per_night: float = Field(ge=0)
    guests: int = Field(default=1, ge=1)
    amenities: List[str] = Field(default_factory=list)
    check_in_time: str = "14:00"
    check_out_time: str = "11:00"
    image_url: Optional[str] = None
    notes: Optional[str] = None


class AddRideRequest(BaseSchema):
    """Add ride/transportation to experience"""
    vendor_id: Optional[str] = None
    vehicle_type: str  # car, suv, van, bus, taxi
    pickup_location: TravelLocationSchema
    dropoff_location: TravelLocationSchema
    scheduled_date: date
    pickup_time: str
    passengers: int = Field(default=1, ge=1)
    price: float = Field(ge=0)
    distance_km: Optional[float] = None
    duration_minutes: Optional[int] = None
    driver_name: Optional[str] = None
    notes: Optional[str] = None


class AddEventRequest(BaseSchema):
    """Add event to experience"""
    vendor_id: Optional[str] = None
    name: str
    event_type: str  # concert, festival, show, sports, etc.
    location: TravelLocationSchema
    event_date: date
    start_time: str
    end_time: Optional[str] = None
    ticket_type: str = "general"  # vip, general, backstage
    tickets_count: int = Field(default=1, ge=1)
    price_per_ticket: float = Field(ge=0)
    is_free: bool = False
    venue: Optional[str] = None
    image_url: Optional[str] = None
    notes: Optional[str] = None


class AddActivityRequest(BaseSchema):
    """Add activity to experience"""
    vendor_id: Optional[str] = None
    name: str
    activity_type: str  # tour, adventure, wellness, workshop
    location: TravelLocationSchema
    scheduled_date: date
    start_time: str
    duration_minutes: int = Field(ge=30)
    participants: int = Field(default=1, ge=1)
    price_per_person: float = Field(ge=0)
    difficulty_level: str = "moderate"  # easy, moderate, difficult
    equipment_included: bool = True
    what_to_bring: List[str] = Field(default_factory=list)
    image_url: Optional[str] = None
    notes: Optional[str] = None


class AddDiningRequest(BaseSchema):
    """Add restaurant/dining to experience"""
    vendor_id: Optional[str] = None
    name: str
    cuisine_type: str
    location: TravelLocationSchema
    reservation_date: date
    reservation_time: str
    party_size: int = Field(default=1, ge=1)
    estimated_cost_per_person: float = Field(ge=0)
    meal_type: str = "dinner"  # breakfast, lunch, dinner, brunch
    dietary_options: List[str] = Field(default_factory=list)
    dress_code: Optional[str] = None
    image_url: Optional[str] = None
    notes: Optional[str] = None


class AddPlaceRequest(BaseSchema):
    """Add place to visit"""
    name: str
    place_type: str  # museum, landmark, beach, park, market
    location: TravelLocationSchema
    visit_date: date
    visit_time: str
    duration_minutes: int = Field(default=60, ge=15)
    visitors: int = Field(default=1, ge=1)
    entrance_fee: float = Field(default=0, ge=0)
    is_free: bool = True
    opening_hours: Optional[str] = None
    image_url: Optional[str] = None
    notes: Optional[str] = None


class AddFlightRequest(BaseSchema):
    """Add flight to experience"""
    airline: str
    flight_number: str
    departure_airport: str
    arrival_airport: str
    departure_date: date
    departure_time: str
    arrival_time: str
    flight_duration_minutes: int
    passengers: int = Field(default=1, ge=1)
    price_per_passenger: float = Field(ge=0)
    cabin_class: str = "economy"  # economy, business, first
    baggage_included: bool = True
    booking_reference: Optional[str] = None
    notes: Optional[str] = None


# === Checkout & Payment ===

class ApplyDiscountRequest(BaseSchema):
    """Apply discount code"""
    discount_code: str


class CheckoutRequest(BaseSchema):
    """Submit experience for checkout"""
    payment_method: str  # card, bank_transfer, wallet
    discount_code: Optional[str] = None
    billing_email: Optional[str] = None
    billing_phone: Optional[str] = None
    notes: Optional[str] = None


class CheckoutResponse(BaseSchema):
    """Checkout response with payment info"""
    experience_id: str
    total_amount: float
    currency: str
    payment_url: Optional[str] = None  # Stripe checkout URL
    payment_reference: Optional[str] = None
    status: ExperienceStatus
    expires_at: Optional[datetime] = None


# === Clone Experience ===

class CloneExperienceRequest(BaseSchema):
    """Clone experience from share code"""
    share_code: str
    new_start_date: date
    travelers: Optional[TravelGroupCreate] = None
    customize_items: bool = False  # If true, clone as draft for editing


class CloneExperienceResponse(BaseSchema):
    """Clone response"""
    new_experience_id: str
    original_experience_id: str
    original_card_code: str
    status: ExperienceStatus
    requires_payment: bool = True
    estimated_total: float
    currency: str = "NGN"


# === AI Assistance ===

class AIRecommendationsRequest(BaseSchema):
    """Request AI recommendations for experience"""
    category: Optional[str] = None  # accommodation, dining, activities, all
    budget_limit: Optional[float] = None
    preferences_override: Optional[ExperiencePreferencesSchema] = None


class AIRecommendationsResponse(BaseSchema):
    """AI recommendations response"""
    recommendations: List[ExperienceItemResponse]
    ai_summary: str
    suggested_itinerary: Optional[List[ItineraryDayResponse]] = None


# === Pagination ===

class PaginatedExperiencesResponse(PaginatedResponse):
    """Paginated experiences list"""
    data: List[ExperienceSummaryResponse]


# === Filters ===

class ExperienceFilters(BaseSchema):
    """Filters for listing experiences"""
    status: Optional[ExperienceStatus] = None
    destination_city: Optional[str] = None
    destination_country: Optional[str] = None
    start_date_from: Optional[date] = None
    start_date_to: Optional[date] = None
    min_budget: Optional[float] = None
    max_budget: Optional[float] = None
    travelers_min: Optional[int] = None
    travelers_max: Optional[int] = None
    tags: Optional[List[str]] = None
    is_upcoming: Optional[bool] = None
    card_generated: Optional[bool] = None

