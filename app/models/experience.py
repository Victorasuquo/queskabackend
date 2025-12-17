"""
Queska Backend - Experience Model
Core experience document model for travel experience creation and management
"""

from datetime import datetime, date
from typing import Any, Dict, List, Optional

from beanie import Document, Indexed, PydanticObjectId
from pydantic import BaseModel, Field

from app.core.constants import (
    ExperienceStatus,
    PaymentStatus,
    TravelInterest,
    Currency,
    TransportationType,
)
from app.models.base import BaseDocument


# === Embedded Models ===

class TravelLocation(BaseModel):
    """Location with coordinates and details"""
    name: str
    city: str
    state: Optional[str] = None
    country: str = "Nigeria"
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    place_id: Optional[str] = None  # Google/Mapbox place ID
    timezone: str = "Africa/Lagos"


class TravelDates(BaseModel):
    """Travel date range"""
    start_date: date
    end_date: date
    flexible_dates: bool = False
    preferred_arrival_time: Optional[str] = None  # HH:MM
    preferred_departure_time: Optional[str] = None


class TravelGroup(BaseModel):
    """Travel group/passengers information"""
    adults: int = 1
    children: int = 0
    infants: int = 0
    total_passengers: int = 1
    companion_names: List[str] = Field(default_factory=list)
    special_requirements: List[str] = Field(default_factory=list)


class ExperiencePreferences(BaseModel):
    """User preferences for the experience"""
    interests: List[str] = Field(default_factory=list)  # adventure, food, culture, etc.
    travel_style: str = "mid-range"  # budget, mid-range, luxury
    pace: str = "moderate"  # relaxed, moderate, packed
    dietary_restrictions: List[str] = Field(default_factory=list)
    accessibility_needs: List[str] = Field(default_factory=list)
    preferred_cuisines: List[str] = Field(default_factory=list)
    avoid_categories: List[str] = Field(default_factory=list)
    max_walking_distance: Optional[float] = None  # in km
    preferred_transport: List[str] = Field(default_factory=list)


class ExperienceItem(BaseModel):
    """Individual item in an experience (hotel, ride, event, activity, dining)"""
    id: str = Field(default_factory=lambda: str(PydanticObjectId()))
    type: str  # accommodation, ride, event, place, activity, dining, flight
    
    # Basic info
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    
    # Vendor/Provider info
    vendor_id: Optional[str] = None
    vendor_name: Optional[str] = None
    vendor_type: Optional[str] = None
    
    # Location
    location: Optional[TravelLocation] = None
    
    # Timing
    scheduled_date: Optional[date] = None
    start_time: Optional[str] = None  # HH:MM
    end_time: Optional[str] = None
    duration_minutes: Optional[int] = None
    
    # Pricing
    price_per_unit: float = 0.0
    quantity: int = 1
    total_price: float = 0.0
    currency: str = "NGN"
    is_free: bool = False
    
    # Status
    booking_status: str = "pending"  # pending, confirmed, cancelled
    booking_reference: Optional[str] = None
    confirmation_code: Optional[str] = None
    
    # Media
    image_url: Optional[str] = None
    images: List[str] = Field(default_factory=list)
    
    # Additional details (type-specific)
    details: Dict[str, Any] = Field(default_factory=dict)
    """
    For accommodations: room_type, check_in_time, check_out_time, amenities, nights
    For rides: vehicle_type, driver_name, pickup_location, dropoff_location
    For events: event_type, venue, ticket_type, seat_info
    For dining: cuisine_type, reservation_time, party_size, menu_items
    For activities: activity_type, difficulty_level, equipment_included
    For flights: airline, flight_number, departure_airport, arrival_airport
    """
    
    # Travel time from previous item
    travel_time_from_previous: Optional[int] = None  # in minutes
    distance_from_previous: Optional[float] = None  # in km
    
    # Notes
    notes: Optional[str] = None
    internal_notes: Optional[str] = None
    
    # Order in itinerary
    order: int = 0
    day_number: int = 1


class ItineraryDay(BaseModel):
    """Single day in the itinerary"""
    day_number: int
    date: date
    title: Optional[str] = None  # "Arrival Day", "Beach Adventure", etc.
    description: Optional[str] = None
    items: List[ExperienceItem] = Field(default_factory=list)
    
    # Day summary
    total_cost: float = 0.0
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    
    # Weather forecast (if available)
    weather_forecast: Optional[Dict[str, Any]] = None
    
    # Notes
    notes: Optional[str] = None


class ExperiencePricing(BaseModel):
    """Complete pricing breakdown"""
    currency: str = "NGN"
    
    # Item costs
    accommodation_total: float = 0.0
    transportation_total: float = 0.0
    events_total: float = 0.0
    activities_total: float = 0.0
    dining_total: float = 0.0
    flights_total: float = 0.0
    
    # Subtotals
    items_subtotal: float = 0.0
    
    # Fees
    service_fee: float = 0.0
    service_fee_percentage: float = 5.0  # Platform fee
    taxes: float = 0.0
    
    # Discounts
    discount_amount: float = 0.0
    discount_code: Optional[str] = None
    discount_percentage: Optional[float] = None
    
    # Total
    grand_total: float = 0.0
    
    # Per person
    price_per_person: float = 0.0
    
    # Payment
    amount_paid: float = 0.0
    balance_due: float = 0.0
    payment_status: PaymentStatus = PaymentStatus.PENDING
    
    def calculate_totals(self, items: List[ExperienceItem], passengers: int = 1):
        """Calculate all totals from items"""
        self.accommodation_total = sum(
            i.total_price for i in items if i.type == "accommodation"
        )
        self.transportation_total = sum(
            i.total_price for i in items if i.type in ["ride", "transportation"]
        )
        self.events_total = sum(
            i.total_price for i in items if i.type == "event"
        )
        self.activities_total = sum(
            i.total_price for i in items if i.type == "activity"
        )
        self.dining_total = sum(
            i.total_price for i in items if i.type == "dining"
        )
        self.flights_total = sum(
            i.total_price for i in items if i.type == "flight"
        )
        
        self.items_subtotal = (
            self.accommodation_total +
            self.transportation_total +
            self.events_total +
            self.activities_total +
            self.dining_total +
            self.flights_total
        )
        
        self.service_fee = self.items_subtotal * (self.service_fee_percentage / 100)
        self.grand_total = self.items_subtotal + self.service_fee + self.taxes - self.discount_amount
        self.balance_due = self.grand_total - self.amount_paid
        
        if passengers > 0:
            self.price_per_person = self.grand_total / passengers


class ExperienceSharing(BaseModel):
    """Sharing settings and stats"""
    is_public: bool = False
    is_shareable: bool = True
    share_code: Optional[str] = None  # Unique shareable code
    share_url: Optional[str] = None
    
    # Privacy
    hide_prices: bool = False
    hide_personal_details: bool = True
    
    # Stats
    view_count: int = 0
    share_count: int = 0
    clone_count: int = 0
    
    # Recipients
    shared_with_emails: List[str] = Field(default_factory=list)
    shared_with_user_ids: List[str] = Field(default_factory=list)


class ExperienceAnalytics(BaseModel):
    """Analytics and tracking"""
    total_distance_km: float = 0.0
    total_travel_time_minutes: int = 0
    
    # Counts
    total_items: int = 0
    total_days: int = 0
    places_count: int = 0
    events_count: int = 0
    activities_count: int = 0
    dining_count: int = 0
    
    # AI-generated insights
    ai_summary: Optional[str] = None
    highlights: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)


# === Main Experience Document ===

class Experience(BaseDocument):
    """
    Core Experience document - represents a complete travel experience.
    
    This is the heart of Queska - users create experiences by:
    1. Selecting destination, dates, passengers
    2. Choosing interests/preferences
    3. Adding items (hotels, rides, events, places, activities, dining)
    4. Checking out and paying
    5. Receiving an Experience Card
    """
    
    # Owner
    user_id: Indexed(str)
    user_name: Optional[str] = None
    user_email: Optional[str] = None
    
    # Agent/Consultant (if created by agent on behalf of client)
    agent_id: Optional[str] = None
    agent_name: Optional[str] = None
    created_by_agent: bool = False
    
    # Basic Info
    title: str
    slug: Optional[str] = None
    description: Optional[str] = None
    cover_image: Optional[str] = None
    images: List[str] = Field(default_factory=list)
    
    # Origin and Destination
    origin: Optional[TravelLocation] = None
    destination: TravelLocation
    
    # Dates
    dates: TravelDates
    
    # Passengers/Group
    travelers: TravelGroup = Field(default_factory=TravelGroup)
    
    # Preferences
    preferences: ExperiencePreferences = Field(default_factory=ExperiencePreferences)
    
    # Items (all bookings in this experience)
    items: List[ExperienceItem] = Field(default_factory=list)
    
    # Itinerary (organized by day)
    itinerary: List[ItineraryDay] = Field(default_factory=list)
    
    # Pricing
    pricing: ExperiencePricing = Field(default_factory=ExperiencePricing)
    
    # Status
    status: ExperienceStatus = ExperienceStatus.DRAFT
    
    # Sharing
    sharing: ExperienceSharing = Field(default_factory=ExperienceSharing)
    
    # Analytics
    analytics: ExperienceAnalytics = Field(default_factory=ExperienceAnalytics)
    
    # Experience Card (generated after payment)
    experience_card_id: Optional[str] = None
    card_generated: bool = False
    
    # Cloning (if this experience was cloned from another)
    cloned_from_id: Optional[str] = None
    cloned_from_card_code: Optional[str] = None
    is_clone: bool = False
    
    # Timestamps
    submitted_at: Optional[datetime] = None
    paid_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    
    # AI assistance
    ai_assisted: bool = False
    ai_suggestions_used: List[str] = Field(default_factory=list)
    
    # Tags and categories
    tags: List[str] = Field(default_factory=list)
    categories: List[str] = Field(default_factory=list)
    
    # Rating (after completion)
    rating: Optional[float] = None
    review: Optional[str] = None
    
    class Settings:
        name = "experiences"
        indexes = [
            "user_id",
            "agent_id",
            "status",
            "destination.city",
            "dates.start_date",
            "sharing.share_code",
            "experience_card_id",
        ]
    
    # === Helper Methods ===
    
    def add_item(self, item: ExperienceItem) -> None:
        """Add an item to the experience"""
        item.order = len(self.items)
        self.items.append(item)
        self._recalculate_pricing()
        self._update_analytics()
    
    def remove_item(self, item_id: str) -> bool:
        """Remove an item by ID"""
        for i, item in enumerate(self.items):
            if item.id == item_id:
                self.items.pop(i)
                self._recalculate_pricing()
                self._update_analytics()
                return True
        return False
    
    def update_item(self, item_id: str, updates: Dict[str, Any]) -> bool:
        """Update an item by ID"""
        for item in self.items:
            if item.id == item_id:
                for key, value in updates.items():
                    if hasattr(item, key):
                        setattr(item, key, value)
                self._recalculate_pricing()
                return True
        return False
    
    def _recalculate_pricing(self) -> None:
        """Recalculate all pricing"""
        self.pricing.calculate_totals(self.items, self.travelers.total_passengers)
    
    def _update_analytics(self) -> None:
        """Update analytics from current items"""
        self.analytics.total_items = len(self.items)
        self.analytics.places_count = sum(1 for i in self.items if i.type == "place")
        self.analytics.events_count = sum(1 for i in self.items if i.type == "event")
        self.analytics.activities_count = sum(1 for i in self.items if i.type == "activity")
        self.analytics.dining_count = sum(1 for i in self.items if i.type == "dining")
    
    def generate_itinerary(self) -> None:
        """Generate day-by-day itinerary from items"""
        from collections import defaultdict
        
        # Group items by date
        items_by_date: Dict[date, List[ExperienceItem]] = defaultdict(list)
        for item in self.items:
            if item.scheduled_date:
                items_by_date[item.scheduled_date].append(item)
        
        # Generate itinerary days
        self.itinerary = []
        start = self.dates.start_date
        end = self.dates.end_date
        
        day_num = 1
        current = start
        while current <= end:
            day_items = sorted(
                items_by_date.get(current, []),
                key=lambda x: (x.start_time or "00:00", x.order)
            )
            
            day_total = sum(i.total_price for i in day_items)
            
            self.itinerary.append(ItineraryDay(
                day_number=day_num,
                date=current,
                title=f"Day {day_num}" if not day_items else None,
                items=day_items,
                total_cost=day_total,
                start_time=day_items[0].start_time if day_items else None,
                end_time=day_items[-1].end_time if day_items else None
            ))
            
            day_num += 1
            current = date.fromordinal(current.toordinal() + 1)
        
        self.analytics.total_days = len(self.itinerary)
    
    @property
    def total_days(self) -> int:
        """Calculate total days of the experience"""
        return (self.dates.end_date - self.dates.start_date).days + 1
    
    @property
    def is_upcoming(self) -> bool:
        """Check if experience is upcoming"""
        return self.dates.start_date > date.today()
    
    @property
    def is_ongoing(self) -> bool:
        """Check if experience is currently ongoing"""
        today = date.today()
        return self.dates.start_date <= today <= self.dates.end_date
    
    @property
    def is_past(self) -> bool:
        """Check if experience has passed"""
        return self.dates.end_date < date.today()

