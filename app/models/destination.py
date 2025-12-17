"""
Queska Backend - Destination Model
Curated destinations managed by admins for featured content
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from beanie import Document, Indexed, PydanticObjectId
from pydantic import BaseModel, Field

from app.models.base import BaseDocument


# === Embedded Models ===

class DestinationLocation(BaseModel):
    """Location details for destination"""
    city: str
    state: Optional[str] = None
    country: str
    region: Optional[str] = None
    continent: Optional[str] = None
    latitude: float
    longitude: float
    timezone: Optional[str] = None


class DestinationMedia(BaseModel):
    """Media content for destination"""
    hero_image: Optional[str] = None
    thumbnail: Optional[str] = None
    gallery: List[str] = Field(default_factory=list)
    video_url: Optional[str] = None


class DestinationStats(BaseModel):
    """Statistics for the destination"""
    hotels_count: int = 0
    restaurants_count: int = 0
    attractions_count: int = 0
    activities_count: int = 0
    experiences_created: int = 0
    total_bookings: int = 0
    average_rating: float = 0.0
    review_count: int = 0


class DestinationTravelInfo(BaseModel):
    """Travel information for destination"""
    best_time_to_visit: List[str] = Field(default_factory=list)  # ["March", "April", "May"]
    average_temperature: Optional[Dict[str, float]] = None  # {"summer": 28, "winter": 15}
    currency: str = "USD"
    language: str = "English"
    visa_required: bool = False
    visa_info: Optional[str] = None
    safety_rating: Optional[str] = None  # "very_safe", "safe", "moderate", "caution"
    travel_advisory: Optional[str] = None


class DestinationCategory(BaseModel):
    """Category/type of destination"""
    type: str  # city, beach, mountain, island, countryside, desert, cultural, adventure
    tags: List[str] = Field(default_factory=list)  # ["romantic", "family", "solo", "budget", "luxury"]
    highlights: List[str] = Field(default_factory=list)  # ["Eiffel Tower", "Louvre", "Notre Dame"]


# === API Provider IDs ===

class DestinationProviderIds(BaseModel):
    """IDs from travel API providers for easy lookup"""
    booking_com_id: Optional[str] = None
    booking_com_type: Optional[str] = None  # city, region, landmark
    expedia_region_id: Optional[str] = None
    google_place_id: Optional[str] = None
    mapbox_id: Optional[str] = None


# === Main Document ===

class Destination(BaseDocument):
    """
    Curated destination managed by admins.
    
    Used for:
    - Featured destinations on homepage
    - Popular destinations by region
    - Recommended destinations
    - SEO-optimized destination pages
    """
    
    # Basic info
    name: Indexed(str)
    slug: Indexed(str, unique=True)
    display_name: str  # "Paris, France"
    short_description: Optional[str] = None
    description: Optional[str] = None
    tagline: Optional[str] = None  # "The City of Love"
    
    # Location
    location: DestinationLocation
    
    # Media
    media: DestinationMedia = Field(default_factory=DestinationMedia)
    
    # Category and type
    category: DestinationCategory = Field(default_factory=DestinationCategory)
    
    # Travel info
    travel_info: DestinationTravelInfo = Field(default_factory=DestinationTravelInfo)
    
    # Provider IDs
    provider_ids: DestinationProviderIds = Field(default_factory=DestinationProviderIds)
    
    # Stats (updated periodically)
    stats: DestinationStats = Field(default_factory=DestinationStats)
    
    # Pricing guide
    average_daily_budget: Optional[Dict[str, float]] = None  # {"budget": 50, "mid_range": 150, "luxury": 400}
    
    # Featured settings
    is_featured: bool = False
    is_popular: bool = False
    is_trending: bool = False
    featured_order: int = 0
    
    # Regional grouping
    region_group: Optional[str] = None  # "europe", "asia", "africa", "north_america", etc.
    
    # Related destinations
    nearby_destinations: List[str] = Field(default_factory=list)  # List of destination slugs
    similar_destinations: List[str] = Field(default_factory=list)
    
    # SEO
    seo_title: Optional[str] = None
    seo_description: Optional[str] = None
    seo_keywords: List[str] = Field(default_factory=list)
    
    # Status
    is_active: bool = True
    
    # Admin info
    created_by: Optional[str] = None
    last_updated_by: Optional[str] = None
    
    class Settings:
        name = "destinations"
        indexes = [
            "name",
            "slug",
            "is_featured",
            "is_popular",
            "is_trending",
            "is_active",
            "region_group",
            "location.country",
            "category.type",
            [("featured_order", 1)],
            [("stats.experiences_created", -1)],
        ]


class DestinationReview(BaseDocument):
    """
    User reviews for destinations (separate from vendor reviews).
    """
    destination_id: Indexed(str)
    user_id: Indexed(str)
    
    # Rating
    overall_rating: float = Field(..., ge=1, le=5)
    ratings: Dict[str, float] = Field(default_factory=dict)  # {"value": 4, "safety": 5, "attractions": 4}
    
    # Review content
    title: Optional[str] = None
    content: str
    
    # Travel context
    travel_date: Optional[str] = None  # "2024-03"
    travel_type: Optional[str] = None  # "solo", "couple", "family", "business", "group"
    trip_duration: Optional[int] = None  # days
    
    # Media
    photos: List[str] = Field(default_factory=list)
    
    # Moderation
    is_approved: bool = False
    is_featured: bool = False
    
    # Engagement
    helpful_count: int = 0
    
    class Settings:
        name = "destination_reviews"
        indexes = [
            "destination_id",
            "user_id",
            "is_approved",
            "is_featured",
            [("overall_rating", -1)],
            [("helpful_count", -1)],
        ]

