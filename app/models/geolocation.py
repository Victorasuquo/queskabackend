"""
Queska Backend - Geolocation Models
Models for location tracking, saved places, and travel history
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from beanie import Document, Indexed, PydanticObjectId
from pydantic import BaseModel, Field

from app.models.base import BaseDocument


# === Embedded Models ===

class Coordinates(BaseModel):
    """Geographic coordinates"""
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    altitude: Optional[float] = None  # meters
    accuracy: Optional[float] = None  # meters
    heading: Optional[float] = None  # degrees from north
    speed: Optional[float] = None  # m/s


class Address(BaseModel):
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


class PlaceCategory(BaseModel):
    """Place category/type"""
    id: str
    name: str
    icon: Optional[str] = None


# === Main Documents ===

class SavedPlace(BaseDocument):
    """
    User's saved/favorite places.
    """
    user_id: Indexed(str)
    
    # Place info
    name: str
    place_id: Optional[str] = None  # External provider ID
    provider: str = "mapbox"  # mapbox, google, manual
    
    # Location
    coordinates: Coordinates
    address: Optional[Address] = None
    
    # Categorization
    category: Optional[str] = None  # home, work, favorite, hotel, restaurant, etc.
    custom_category: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    
    # User customization
    label: Optional[str] = None  # User's custom label
    notes: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    
    # Media
    photo_url: Optional[str] = None
    photos: List[str] = Field(default_factory=list)
    
    # Metadata
    is_favorite: bool = False
    visit_count: int = 0
    last_visited_at: Optional[datetime] = None
    
    class Settings:
        name = "saved_places"
        indexes = [
            "user_id",
            "category",
            "is_favorite",
        ]


class LocationHistory(BaseDocument):
    """
    User's location history for tracking and analytics.
    Stored with consent for trip tracking during experiences.
    """
    user_id: Indexed(str)
    
    # Experience context (if tracking during a trip)
    experience_id: Optional[str] = None
    experience_card_id: Optional[str] = None
    
    # Location
    coordinates: Coordinates
    address: Optional[Address] = None
    
    # Context
    activity_type: Optional[str] = None  # stationary, walking, driving, flying
    battery_level: Optional[int] = None
    network_type: Optional[str] = None  # wifi, cellular, offline
    
    # Consent
    tracking_enabled: bool = True
    shared_publicly: bool = False
    
    # Timestamp (using created_at from base)
    recorded_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Settings:
        name = "location_history"
        indexes = [
            "user_id",
            "experience_id",
            "recorded_at",
        ]


class Route(BaseDocument):
    """
    Saved routes between locations.
    """
    user_id: Optional[str] = None
    
    # Route info
    name: str
    description: Optional[str] = None
    
    # Start and end
    origin: Coordinates
    origin_name: Optional[str] = None
    origin_address: Optional[Address] = None
    
    destination: Coordinates
    destination_name: Optional[str] = None
    destination_address: Optional[Address] = None
    
    # Waypoints
    waypoints: List[Dict[str, Any]] = Field(default_factory=list)
    """
    [
        {"coordinates": {"latitude": x, "longitude": y}, "name": "Stop 1"},
        ...
    ]
    """
    
    # Route details
    profile: str = "driving"  # driving, walking, cycling, transit
    distance_meters: Optional[float] = None
    duration_seconds: Optional[float] = None
    geometry: Optional[Dict[str, Any]] = None  # GeoJSON
    
    # Cached route data
    route_data: Optional[Dict[str, Any]] = None
    cached_at: Optional[datetime] = None
    
    # Usage
    use_count: int = 0
    last_used_at: Optional[datetime] = None
    
    # Tags
    tags: List[str] = Field(default_factory=list)
    is_favorite: bool = False
    
    class Settings:
        name = "routes"
        indexes = [
            "user_id",
            "is_favorite",
        ]


class GeofenceZone(BaseDocument):
    """
    Geofence zones for location-based triggers.
    """
    user_id: Optional[str] = None
    
    # Zone info
    name: str
    description: Optional[str] = None
    
    # Center point
    center: Coordinates
    
    # Radius in meters
    radius: float = 100
    
    # Or polygon boundary
    polygon: Optional[List[List[float]]] = None  # [[lng, lat], [lng, lat], ...]
    
    # Trigger settings
    trigger_on_enter: bool = True
    trigger_on_exit: bool = True
    trigger_on_dwell: bool = False
    dwell_time_seconds: int = 300  # 5 minutes
    
    # Actions
    notify_user: bool = True
    notification_message: Optional[str] = None
    webhook_url: Optional[str] = None
    
    # Status
    is_active: bool = True
    
    # Statistics
    enter_count: int = 0
    exit_count: int = 0
    last_triggered_at: Optional[datetime] = None
    
    class Settings:
        name = "geofence_zones"
        indexes = [
            "user_id",
            "is_active",
        ]


class NearbySearch(BaseDocument):
    """
    Cached nearby search results for places.
    """
    # Search parameters
    center_lat: float
    center_lng: float
    radius: int
    category: Optional[str] = None
    query: Optional[str] = None
    
    # Results
    results: List[Dict[str, Any]] = Field(default_factory=list)
    result_count: int = 0
    
    # Provider
    provider: str = "mapbox"  # mapbox, google
    
    # Cache info
    expires_at: datetime
    
    class Settings:
        name = "nearby_searches"
        indexes = [
            "center_lat",
            "center_lng",
            "category",
            "expires_at",
        ]

