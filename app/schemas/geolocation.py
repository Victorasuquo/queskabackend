"""
Queska Backend - Geolocation Schemas
Pydantic schemas for geolocation API requests and responses
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field, field_validator

from app.schemas.base import BaseSchema, PaginatedResponse


# === Coordinate Schemas ===

class CoordinatesSchema(BaseSchema):
    """Geographic coordinates"""
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    altitude: Optional[float] = None
    accuracy: Optional[float] = None
    heading: Optional[float] = None
    speed: Optional[float] = None


class AddressSchema(BaseSchema):
    """Structured address"""
    street: Optional[str] = None
    street_number: Optional[str] = None
    neighborhood: Optional[str] = None
    city: Optional[str] = None
    region: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    country_code: Optional[str] = None
    postal_code: Optional[str] = None
    formatted: Optional[str] = None


# === Geocoding Schemas ===

class GeocodeRequest(BaseSchema):
    """Request to geocode an address"""
    query: str = Field(..., min_length=2, max_length=500)
    country: Optional[str] = Field(None, max_length=2, description="ISO 3166-1 alpha-2 country code")
    limit: int = Field(5, ge=1, le=10)
    proximity_lat: Optional[float] = None
    proximity_lng: Optional[float] = None
    types: Optional[List[str]] = None
    language: str = "en"


class ReverseGeocodeRequest(BaseSchema):
    """Request to reverse geocode coordinates"""
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    types: Optional[List[str]] = None
    language: str = "en"


class GeocodeResult(BaseSchema):
    """Single geocoding result"""
    place_id: Optional[str] = None
    name: str
    full_name: Optional[str] = None
    coordinates: CoordinatesSchema
    type: Optional[str] = None
    relevance: Optional[float] = None
    address: AddressSchema
    bbox: Optional[List[float]] = None


class GeocodeResponse(BaseSchema):
    """Geocoding response"""
    success: bool
    results: List[GeocodeResult]
    error: Optional[str] = None


# === Directions Schemas ===

class DirectionsRequest(BaseSchema):
    """Request for route directions"""
    origin_lat: float = Field(..., ge=-90, le=90)
    origin_lng: float = Field(..., ge=-180, le=180)
    destination_lat: float = Field(..., ge=-90, le=90)
    destination_lng: float = Field(..., ge=-180, le=180)
    waypoints: Optional[List[Dict[str, float]]] = None  # [{"lat": x, "lng": y}]
    profile: str = Field("driving", pattern="^(driving|walking|cycling|transit)$")
    alternatives: bool = True
    steps: bool = True
    language: str = "en"


class RouteStep(BaseSchema):
    """Single step in route directions"""
    instruction: Optional[str] = None
    distance_meters: Optional[float] = None
    duration_seconds: Optional[float] = None
    maneuver_type: Optional[str] = None
    maneuver_modifier: Optional[str] = None
    name: Optional[str] = None


class RouteLeg(BaseSchema):
    """Leg of a route (between waypoints)"""
    duration_seconds: Optional[float] = None
    duration_text: Optional[str] = None
    distance_meters: Optional[float] = None
    distance_text: Optional[str] = None
    summary: Optional[str] = None
    steps: List[RouteStep] = Field(default_factory=list)


class RouteResult(BaseSchema):
    """Single route result"""
    duration_seconds: float
    duration_minutes: float
    duration_text: str
    distance_meters: float
    distance_km: float
    distance_text: str
    geometry: Optional[Dict[str, Any]] = None  # GeoJSON
    legs: List[RouteLeg] = Field(default_factory=list)


class DirectionsResponse(BaseSchema):
    """Directions response"""
    success: bool
    routes: List[RouteResult]
    error: Optional[str] = None


# === Distance Matrix Schemas ===

class DistanceMatrixRequest(BaseSchema):
    """Request for distance matrix"""
    origins: List[Dict[str, float]]  # [{"lat": x, "lng": y}]
    destinations: List[Dict[str, float]]
    profile: str = "driving"


class MatrixElement(BaseSchema):
    """Single element in distance matrix"""
    duration_seconds: Optional[float] = None
    duration_text: Optional[str] = None
    distance_meters: Optional[float] = None
    distance_text: Optional[str] = None
    status: Optional[str] = None


class DistanceMatrixResponse(BaseSchema):
    """Distance matrix response"""
    success: bool
    matrix: List[List[MatrixElement]] = Field(default_factory=list)
    error: Optional[str] = None


# === Place Search Schemas ===

class PlaceSearchRequest(BaseSchema):
    """Request to search for places"""
    query: Optional[str] = None
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    radius: int = Field(5000, ge=100, le=50000)
    category: Optional[str] = None
    limit: int = Field(10, ge=1, le=50)
    language: str = "en"


class PlaceResult(BaseSchema):
    """Place search result"""
    place_id: str
    name: str
    formatted_address: Optional[str] = None
    vicinity: Optional[str] = None
    coordinates: CoordinatesSchema
    types: List[str] = Field(default_factory=list)
    rating: Optional[float] = None
    user_ratings_total: Optional[int] = None
    price_level: Optional[int] = None
    open_now: Optional[bool] = None
    photo_url: Optional[str] = None
    icon: Optional[str] = None
    distance_meters: Optional[float] = None


class PlaceSearchResponse(BaseSchema):
    """Place search response"""
    success: bool
    places: List[PlaceResult]
    error: Optional[str] = None


class PlaceDetailsResponse(BaseSchema):
    """Place details response"""
    success: bool
    place: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


# === Isochrone Schemas ===

class IsochroneRequest(BaseSchema):
    """Request for isochrone (reachable area)"""
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    contours_minutes: List[int] = Field(default=[15, 30, 60])
    profile: str = "driving"


class IsochroneResponse(BaseSchema):
    """Isochrone response"""
    success: bool
    isochrones: List[Dict[str, Any]] = Field(default_factory=list)  # GeoJSON features
    error: Optional[str] = None


# === Static Map Schemas ===

class StaticMapRequest(BaseSchema):
    """Request for static map image"""
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    zoom: int = Field(14, ge=0, le=22)
    width: int = Field(600, ge=100, le=1280)
    height: int = Field(400, ge=100, le=1280)
    style: str = "streets-v12"
    markers: Optional[List[Dict[str, Any]]] = None  # [{"lat": x, "lng": y, "color": "red"}]
    path: Optional[List[Dict[str, float]]] = None  # Route path
    retina: bool = True


class StaticMapResponse(BaseSchema):
    """Static map response"""
    url: str
    width: int
    height: int


# === Trip Optimization Schemas ===

class OptimizeRouteRequest(BaseSchema):
    """Request to optimize route through waypoints"""
    waypoints: List[Dict[str, Any]]  # [{"lat": x, "lng": y, "name": "Stop 1"}]
    profile: str = "driving"
    roundtrip: bool = True


class OptimizeRouteResponse(BaseSchema):
    """Optimized route response"""
    success: bool
    optimized_order: List[int] = Field(default_factory=list)
    duration_seconds: Optional[float] = None
    duration_text: Optional[str] = None
    distance_meters: Optional[float] = None
    distance_text: Optional[str] = None
    geometry: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


# === Saved Place Schemas ===

class SavedPlaceCreate(BaseSchema):
    """Create a saved place"""
    name: str
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    place_id: Optional[str] = None
    address: Optional[AddressSchema] = None
    category: str = "favorite"  # home, work, favorite, etc.
    custom_category: Optional[str] = None
    label: Optional[str] = None
    notes: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    is_favorite: bool = False


class SavedPlaceUpdate(BaseSchema):
    """Update a saved place"""
    name: Optional[str] = None
    category: Optional[str] = None
    custom_category: Optional[str] = None
    label: Optional[str] = None
    notes: Optional[str] = None
    tags: Optional[List[str]] = None
    is_favorite: Optional[bool] = None


class SavedPlaceResponse(BaseSchema):
    """Saved place response"""
    id: str = Field(alias="_id")
    name: str
    place_id: Optional[str] = None
    coordinates: CoordinatesSchema
    address: Optional[AddressSchema] = None
    category: Optional[str] = None
    custom_category: Optional[str] = None
    label: Optional[str] = None
    notes: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    is_favorite: bool = False
    visit_count: int = 0
    last_visited_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        populate_by_name = True


class PaginatedSavedPlacesResponse(PaginatedResponse):
    """Paginated saved places"""
    data: List[SavedPlaceResponse]


# === Location Tracking Schemas ===

class UpdateLocationRequest(BaseSchema):
    """Update user's current location"""
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    altitude: Optional[float] = None
    accuracy: Optional[float] = None
    heading: Optional[float] = None
    speed: Optional[float] = None
    experience_id: Optional[str] = None
    share_publicly: bool = False


class LocationUpdateResponse(BaseSchema):
    """Location update response"""
    success: bool
    recorded_at: datetime
    address: Optional[AddressSchema] = None
    nearby_places: List[PlaceResult] = Field(default_factory=list)


class LocationHistoryRequest(BaseSchema):
    """Request for location history"""
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    experience_id: Optional[str] = None
    limit: int = Field(100, ge=1, le=1000)


class LocationHistoryPoint(BaseSchema):
    """Single point in location history"""
    coordinates: CoordinatesSchema
    address: Optional[AddressSchema] = None
    recorded_at: datetime
    activity_type: Optional[str] = None


class LocationHistoryResponse(BaseSchema):
    """Location history response"""
    success: bool
    points: List[LocationHistoryPoint]
    total_distance_km: Optional[float] = None
    error: Optional[str] = None


# === Distance Calculation ===

class CalculateDistanceRequest(BaseSchema):
    """Calculate distance between two points"""
    from_lat: float = Field(..., ge=-90, le=90)
    from_lng: float = Field(..., ge=-180, le=180)
    to_lat: float = Field(..., ge=-90, le=90)
    to_lng: float = Field(..., ge=-180, le=180)
    profile: str = "driving"


class DistanceResult(BaseSchema):
    """Distance calculation result"""
    straight_line_km: float
    straight_line_text: str
    driving_km: Optional[float] = None
    driving_text: Optional[str] = None
    driving_minutes: Optional[float] = None
    driving_duration_text: Optional[str] = None
    walking_km: Optional[float] = None
    walking_minutes: Optional[float] = None


# === Nearby Categories ===

class NearbyCategory(BaseSchema):
    """Category for nearby search"""
    id: str
    name: str
    icon: str
    mapbox_types: List[str] = Field(default_factory=list)
    google_types: List[str] = Field(default_factory=list)


# Standard categories
NEARBY_CATEGORIES = [
    NearbyCategory(id="restaurant", name="Restaurants", icon="🍽️", mapbox_types=["restaurant"], google_types=["restaurant"]),
    NearbyCategory(id="hotel", name="Hotels", icon="🏨", mapbox_types=["hotel"], google_types=["lodging"]),
    NearbyCategory(id="cafe", name="Cafes", icon="☕", mapbox_types=["cafe"], google_types=["cafe"]),
    NearbyCategory(id="bar", name="Bars", icon="🍺", mapbox_types=["bar"], google_types=["bar"]),
    NearbyCategory(id="attraction", name="Attractions", icon="🎭", mapbox_types=["attraction", "museum"], google_types=["tourist_attraction", "museum"]),
    NearbyCategory(id="shopping", name="Shopping", icon="🛍️", mapbox_types=["shop"], google_types=["shopping_mall", "store"]),
    NearbyCategory(id="transport", name="Transport", icon="🚌", mapbox_types=["bus_station", "train_station"], google_types=["transit_station"]),
    NearbyCategory(id="airport", name="Airports", icon="✈️", mapbox_types=["airport"], google_types=["airport"]),
    NearbyCategory(id="gas", name="Gas Stations", icon="⛽", mapbox_types=["fuel"], google_types=["gas_station"]),
    NearbyCategory(id="parking", name="Parking", icon="🅿️", mapbox_types=["parking"], google_types=["parking"]),
    NearbyCategory(id="atm", name="ATMs", icon="🏧", mapbox_types=["atm"], google_types=["atm"]),
    NearbyCategory(id="pharmacy", name="Pharmacies", icon="💊", mapbox_types=["pharmacy"], google_types=["pharmacy"]),
    NearbyCategory(id="hospital", name="Hospitals", icon="🏥", mapbox_types=["hospital"], google_types=["hospital"]),
    NearbyCategory(id="beach", name="Beaches", icon="🏖️", mapbox_types=["beach"], google_types=["natural_feature"]),
    NearbyCategory(id="park", name="Parks", icon="🌳", mapbox_types=["park"], google_types=["park"]),
]

