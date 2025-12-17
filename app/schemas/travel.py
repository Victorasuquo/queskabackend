"""
Queska Backend - Travel Schemas
Pydantic schemas for travel search, booking, and integration with Expedia
"""

from datetime import date, datetime
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, field_validator

from app.schemas.base import BaseSchema, PaginatedResponse


# ================================================================
# COMMON SCHEMAS
# ================================================================

class PriceSchema(BaseSchema):
    """Price information"""
    total: Optional[float] = None
    currency: str = "USD"
    per_night: Optional[float] = None
    per_person: Optional[float] = None
    fees: Optional[float] = None
    taxes: Optional[float] = None
    savings: Optional[float] = None
    formatted: Optional[str] = None


class LocationSchema(BaseSchema):
    """Location information"""
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    postal_code: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class RatingSchema(BaseSchema):
    """Rating information"""
    score: Optional[float] = None
    count: Optional[int] = None
    category: Optional[str] = None  # e.g., "Excellent", "Very Good"


# ================================================================
# HOTEL SCHEMAS
# ================================================================

class HotelSearchRequest(BaseSchema):
    """Request to search for hotels"""
    destination: str = Field(..., description="City, address, or region")
    checkin: date = Field(..., description="Check-in date")
    checkout: date = Field(..., description="Check-out date")
    adults: int = Field(2, ge=1, le=10)
    children: int = Field(0, ge=0, le=6)
    children_ages: Optional[List[int]] = Field(None, description="Ages of children")
    rooms: int = Field(1, ge=1, le=8)
    currency: str = Field("USD", max_length=3)
    star_rating_min: Optional[int] = Field(None, ge=1, le=5)
    price_min: Optional[float] = Field(None, ge=0)
    price_max: Optional[float] = Field(None, ge=0)
    amenities: Optional[List[str]] = None
    sort_by: str = Field("recommended", pattern="^(recommended|price|star_rating|guest_rating|distance)$")
    limit: int = Field(50, ge=1, le=100)
    
    @field_validator("checkout")
    @classmethod
    def checkout_after_checkin(cls, v, info):
        if "checkin" in info.data and v <= info.data["checkin"]:
            raise ValueError("Checkout must be after checkin")
        return v


class HotelRoomSchema(BaseSchema):
    """Hotel room information"""
    room_id: Optional[str] = None
    room_name: str
    description: Optional[str] = None
    rate_id: Optional[str] = None
    price: PriceSchema
    occupancy: Optional[Dict[str, Any]] = None
    bed_type: Optional[str] = None
    beds: Optional[int] = None
    amenities: List[str] = Field(default_factory=list)
    cancellation_policy: Optional[Dict[str, Any]] = None
    refundable: bool = False
    pay_later: bool = False
    book_link: Optional[str] = None


class HotelSchema(BaseSchema):
    """Hotel/property information"""
    id: str
    name: str
    description: Optional[str] = None
    star_rating: Optional[float] = None
    guest_rating: Optional[RatingSchema] = None
    location: LocationSchema
    image_url: Optional[str] = None
    images: List[str] = Field(default_factory=list)
    amenities: List[str] = Field(default_factory=list)
    category: Optional[str] = None
    chain: Optional[str] = None
    brand: Optional[str] = None
    price: Optional[PriceSchema] = None
    rooms: List[HotelRoomSchema] = Field(default_factory=list)
    free_cancellation: bool = False
    pay_later: bool = False
    vip_access: bool = False
    book_url: Optional[str] = None
    provider: str = "expedia"


class HotelSearchResponse(BaseSchema):
    """Hotel search response"""
    success: bool
    hotels: List[HotelSchema] = Field(default_factory=list)
    total: int = 0
    search_params: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class HotelDetailsRequest(BaseSchema):
    """Request for hotel details"""
    property_id: str
    checkin: Optional[date] = None
    checkout: Optional[date] = None
    adults: int = Field(2, ge=1)
    rooms: int = Field(1, ge=1)


class HotelDetailsResponse(BaseSchema):
    """Hotel details response"""
    success: bool
    hotel: Optional[HotelSchema] = None
    error: Optional[str] = None


# ================================================================
# FLIGHT SCHEMAS
# ================================================================

class FlightSearchRequest(BaseSchema):
    """Request to search for flights"""
    origin: str = Field(..., min_length=3, max_length=3, description="Origin airport code")
    destination: str = Field(..., min_length=3, max_length=3, description="Destination airport code")
    departure_date: date
    return_date: Optional[date] = None
    adults: int = Field(1, ge=1, le=9)
    children: int = Field(0, ge=0, le=8)
    infants: int = Field(0, ge=0, le=4)
    cabin_class: str = Field("economy", pattern="^(economy|premium_economy|business|first)$")
    nonstop_only: bool = False
    max_price: Optional[float] = None
    currency: str = Field("USD", max_length=3)
    sort_by: str = Field("price", pattern="^(price|duration|departure_time|arrival_time)$")
    limit: int = Field(50, ge=1, le=100)
    
    @field_validator("origin", "destination")
    @classmethod
    def uppercase_airport_codes(cls, v):
        return v.upper()


class FlightSegmentSchema(BaseSchema):
    """Single flight segment"""
    carrier: str
    carrier_code: Optional[str] = None
    flight_number: str
    aircraft: Optional[str] = None
    departure_airport: str
    departure_airport_code: str
    departure_terminal: Optional[str] = None
    departure_datetime: datetime
    arrival_airport: str
    arrival_airport_code: str
    arrival_terminal: Optional[str] = None
    arrival_datetime: datetime
    duration_minutes: int
    duration_text: str


class FlightLegSchema(BaseSchema):
    """Flight leg (outbound or return)"""
    departure_airport: str
    departure_airport_code: str
    arrival_airport: str
    arrival_airport_code: str
    departure_time: datetime
    arrival_time: datetime
    duration_minutes: int
    duration_text: str
    stops: int
    segments: List[FlightSegmentSchema] = Field(default_factory=list)


class FlightSchema(BaseSchema):
    """Flight option"""
    id: str
    price: PriceSchema
    outbound: FlightLegSchema
    return_leg: Optional[FlightLegSchema] = Field(None, alias="return")
    trip_type: str  # one_way, round_trip
    cabin_class: Optional[str] = None
    fare_class: Optional[str] = None
    seats_remaining: Optional[int] = None
    refundable: bool = False
    changeable: bool = False
    book_url: Optional[str] = None
    provider: str = "expedia"
    
    class Config:
        populate_by_name = True


class FlightSearchResponse(BaseSchema):
    """Flight search response"""
    success: bool
    flights: List[FlightSchema] = Field(default_factory=list)
    total: int = 0
    search_params: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


# ================================================================
# ACTIVITY SCHEMAS
# ================================================================

class ActivitySearchRequest(BaseSchema):
    """Request to search for activities"""
    destination: str
    date: date
    category: Optional[str] = None
    price_max: Optional[float] = None
    currency: str = Field("USD", max_length=3)
    sort_by: str = Field("recommended", pattern="^(recommended|price|rating|duration)$")
    limit: int = Field(50, ge=1, le=100)


class ActivitySchema(BaseSchema):
    """Activity/tour information"""
    id: str
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    duration: Optional[str] = None
    duration_text: Optional[str] = None
    rating: Optional[float] = None
    review_count: Optional[int] = None
    image_url: Optional[str] = None
    images: List[str] = Field(default_factory=list)
    price: PriceSchema
    location: Optional[str] = None
    highlights: List[str] = Field(default_factory=list)
    inclusions: List[str] = Field(default_factory=list)
    exclusions: List[str] = Field(default_factory=list)
    free_cancellation: bool = False
    instant_confirmation: bool = False
    mobile_ticket: bool = False
    book_url: Optional[str] = None
    provider: str = "expedia"


class ActivitySearchResponse(BaseSchema):
    """Activity search response"""
    success: bool
    activities: List[ActivitySchema] = Field(default_factory=list)
    total: int = 0
    search_params: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


# ================================================================
# CAR RENTAL SCHEMAS
# ================================================================

class CarSearchRequest(BaseSchema):
    """Request to search for car rentals"""
    pickup_location: str = Field(..., description="Airport code or city")
    pickup_date: date
    pickup_time: str = Field(..., pattern="^([01]?[0-9]|2[0-3]):[0-5][0-9]$")
    dropoff_date: date
    dropoff_time: str = Field(..., pattern="^([01]?[0-9]|2[0-3]):[0-5][0-9]$")
    dropoff_location: Optional[str] = None
    car_class: Optional[str] = Field(None, pattern="^(economy|compact|midsize|full|luxury|suv|van|convertible)$")
    currency: str = Field("USD", max_length=3)
    sort_by: str = Field("price", pattern="^(price|rating|class)$")
    limit: int = Field(50, ge=1, le=100)


class CarVehicleSchema(BaseSchema):
    """Vehicle information"""
    name: str
    make: Optional[str] = None
    model: Optional[str] = None
    car_class: Optional[str] = None
    car_type: Optional[str] = None
    transmission: Optional[str] = None
    fuel_type: Optional[str] = None
    passengers: Optional[int] = None
    bags: Optional[int] = None
    doors: Optional[int] = None
    air_conditioning: bool = True
    image_url: Optional[str] = None


class CarSupplierSchema(BaseSchema):
    """Car rental supplier"""
    name: str
    logo: Optional[str] = None
    rating: Optional[float] = None


class CarSchema(BaseSchema):
    """Car rental option"""
    id: str
    vehicle: CarVehicleSchema
    supplier: CarSupplierSchema
    pickup_location: Optional[str] = None
    dropoff_location: Optional[str] = None
    price: PriceSchema
    mileage: Optional[str] = None
    insurance_included: bool = False
    free_cancellation: bool = False
    features: List[str] = Field(default_factory=list)
    book_url: Optional[str] = None
    provider: str = "expedia"


class CarSearchResponse(BaseSchema):
    """Car rental search response"""
    success: bool
    cars: List[CarSchema] = Field(default_factory=list)
    total: int = 0
    search_params: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


# ================================================================
# PACKAGE SCHEMAS (Flight + Hotel)
# ================================================================

class PackageSearchRequest(BaseSchema):
    """Request to search for vacation packages"""
    origin: str = Field(..., min_length=3, max_length=3)
    destination: str
    departure_date: date
    return_date: date
    adults: int = Field(2, ge=1, le=8)
    children: int = Field(0, ge=0, le=6)
    rooms: int = Field(1, ge=1, le=4)
    currency: str = Field("USD", max_length=3)
    limit: int = Field(30, ge=1, le=50)


class PackageFlightSchema(BaseSchema):
    """Package flight summary"""
    carrier: Optional[str] = None
    departure_time: Optional[datetime] = None
    arrival_time: Optional[datetime] = None
    stops: int = 0


class PackageHotelSchema(BaseSchema):
    """Package hotel summary"""
    name: str
    star_rating: Optional[float] = None
    guest_rating: Optional[float] = None
    image_url: Optional[str] = None
    address: Optional[str] = None


class PackageSchema(BaseSchema):
    """Vacation package"""
    id: str
    hotel: PackageHotelSchema
    outbound_flight: PackageFlightSchema
    return_flight: PackageFlightSchema
    price: PriceSchema
    free_cancellation: bool = False
    book_url: Optional[str] = None
    provider: str = "expedia"


class PackageSearchResponse(BaseSchema):
    """Package search response"""
    success: bool
    packages: List[PackageSchema] = Field(default_factory=list)
    total: int = 0
    search_params: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


# ================================================================
# BOOKING SCHEMAS
# ================================================================

class TravelerSchema(BaseSchema):
    """Traveler information"""
    given_name: str
    family_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    nationality: Optional[str] = None
    passport_number: Optional[str] = None
    passport_expiry: Optional[date] = None


class BookingContactSchema(BaseSchema):
    """Booking contact information"""
    given_name: str
    family_name: str
    email: str
    phone: str
    address: Optional[LocationSchema] = None


class HotelBookingRequest(BaseSchema):
    """Request to book a hotel"""
    property_id: str
    room_id: str
    rate_id: str
    checkin: date
    checkout: date
    contact: BookingContactSchema
    travelers: List[TravelerSchema]
    special_requests: Optional[str] = None
    payment_token: Optional[str] = None  # For payment processing


class HotelBookingResponse(BaseSchema):
    """Hotel booking response"""
    success: bool
    booking_id: Optional[str] = None
    confirmation_number: Optional[str] = None
    status: Optional[str] = None
    hotel_name: Optional[str] = None
    checkin: Optional[date] = None
    checkout: Optional[date] = None
    total_price: Optional[PriceSchema] = None
    cancellation_policy: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class BookingRetrieveRequest(BaseSchema):
    """Request to retrieve a booking"""
    booking_id: str
    email: str


class BookingCancelRequest(BaseSchema):
    """Request to cancel a booking"""
    booking_id: str
    email: str
    reason: Optional[str] = None


class BookingCancelResponse(BaseSchema):
    """Booking cancellation response"""
    success: bool
    booking_id: str
    status: str
    refund_amount: Optional[PriceSchema] = None
    error: Optional[str] = None


# ================================================================
# DESTINATION / REGION SCHEMAS
# ================================================================

class DestinationSearchRequest(BaseSchema):
    """Request to search for destinations"""
    query: str = Field(..., min_length=2)
    limit: int = Field(20, ge=1, le=50)


class DestinationSchema(BaseSchema):
    """Destination/region information"""
    id: str
    name: str
    full_name: Optional[str] = None
    type: Optional[str] = None  # city, region, country, airport, poi
    country: Optional[str] = None
    country_code: Optional[str] = None
    coordinates: Optional[Dict[str, float]] = None


class DestinationSearchResponse(BaseSchema):
    """Destination search response"""
    success: bool
    destinations: List[DestinationSchema] = Field(default_factory=list)
    error: Optional[str] = None


# ================================================================
# SERVICE STATUS
# ================================================================

class TravelServiceStatus(BaseSchema):
    """Travel API service status"""
    expedia_rapid: Dict[str, Any]
    expedia_xap: Dict[str, Any]
    amadeus: Optional[Dict[str, Any]] = None
    booking_com: Optional[Dict[str, Any]] = None

