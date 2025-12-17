"""
Queska Backend - Experience Card Model
Shareable experience cards created after payment confirmation
"""

from datetime import datetime, date
from typing import Any, Dict, List, Optional
import secrets
import string

from beanie import Document, Indexed, PydanticObjectId
from pydantic import BaseModel, Field

from app.core.constants import ExperienceStatus
from app.models.base import BaseDocument
from app.models.experience import (
    TravelLocation,
    TravelDates,
    TravelGroup,
    ExperienceItem,
    ItineraryDay,
    ExperiencePricing,
)


# === Embedded Models ===

class CardOwner(BaseModel):
    """Owner information displayed on card"""
    user_id: str
    name: str
    avatar_url: Optional[str] = None
    is_verified: bool = False


class CardLocation(BaseModel):
    """Location for real-time tracking"""
    user_id: str
    name: str
    latitude: float
    longitude: float
    accuracy: Optional[float] = None
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    is_sharing: bool = True


class CardHighlight(BaseModel):
    """Featured highlight from the experience"""
    type: str  # accommodation, event, activity, dining, place
    name: str
    description: Optional[str] = None
    image_url: Optional[str] = None
    icon: Optional[str] = None  # emoji or icon name


class TravelTimeEstimate(BaseModel):
    """Travel time estimate from viewer's location"""
    from_location: Optional[TravelLocation] = None
    to_destination: TravelLocation
    driving_time_minutes: Optional[int] = None
    driving_distance_km: Optional[float] = None
    flight_time_minutes: Optional[int] = None
    transit_time_minutes: Optional[int] = None
    walking_time_minutes: Optional[int] = None
    calculated_at: datetime = Field(default_factory=datetime.utcnow)


class CardInteraction(BaseModel):
    """Record of user interaction with the card"""
    user_id: Optional[str] = None
    user_email: Optional[str] = None
    action: str  # viewed, saved, cloned, shared
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    location: Optional[Dict[str, float]] = None  # {lat, lng}
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class CardSettings(BaseModel):
    """Card display and privacy settings"""
    # Visibility
    is_public: bool = False
    is_active: bool = True
    expires_at: Optional[datetime] = None
    
    # Privacy
    show_owner_name: bool = True
    show_owner_avatar: bool = True
    show_prices: bool = False
    show_vendor_details: bool = True
    show_real_time_location: bool = False
    
    # Cloning
    allow_cloning: bool = True
    clone_requires_payment: bool = True
    
    # Appearance
    theme: str = "default"  # default, dark, vibrant, minimal
    cover_style: str = "full"  # full, split, minimal
    accent_color: Optional[str] = None  # hex color


class CardStats(BaseModel):
    """Card engagement statistics"""
    view_count: int = 0
    unique_viewers: int = 0
    share_count: int = 0
    clone_count: int = 0
    save_count: int = 0
    
    # Engagement
    average_view_duration_seconds: float = 0.0
    completion_rate: float = 0.0  # How many viewers see the full card
    
    # Geographic
    viewer_countries: Dict[str, int] = Field(default_factory=dict)
    viewer_cities: Dict[str, int] = Field(default_factory=dict)


# === Main Experience Card Document ===

class ExperienceCard(BaseDocument):
    """
    Shareable Experience Card - Generated after payment is confirmed.
    
    Features:
    - Unique shareable link/code
    - Beautiful card display of the experience
    - Real-time location sharing
    - Distance/time estimation from viewer's location
    - Clonable by other users (requires payment)
    - Analytics and engagement tracking
    """
    
    # Source experience
    experience_id: Indexed(str)
    
    # Owner
    owner: CardOwner
    
    # Unique identifiers
    card_code: Indexed(str, unique=True)  # 8-char unique code (e.g., QESK-ABCD)
    short_url: Optional[str] = None  # https://queska.app/c/ABCD
    qr_code_url: Optional[str] = None
    
    # Experience summary
    title: str
    description: Optional[str] = None
    tagline: Optional[str] = None  # AI-generated catchy summary
    
    # Media
    cover_image: Optional[str] = None
    images: List[str] = Field(default_factory=list)
    video_url: Optional[str] = None
    
    # Destination
    destination: TravelLocation
    origin: Optional[TravelLocation] = None
    
    # Dates
    dates: TravelDates
    
    # Travelers
    travelers: TravelGroup
    
    # Highlights (key items to display)
    highlights: List[CardHighlight] = Field(default_factory=list)
    
    # Full itinerary (optional, if owner allows)
    itinerary: List[ItineraryDay] = Field(default_factory=list)
    include_full_itinerary: bool = False
    
    # Pricing (if displayed)
    pricing: Optional[ExperiencePricing] = None
    
    # Status
    experience_status: ExperienceStatus = ExperienceStatus.CONFIRMED
    
    # Real-time location sharing
    owner_location: Optional[CardLocation] = None
    group_locations: List[CardLocation] = Field(default_factory=list)
    
    # Settings
    settings: CardSettings = Field(default_factory=CardSettings)
    
    # Statistics
    stats: CardStats = Field(default_factory=CardStats)
    
    # Interactions log (recent)
    recent_interactions: List[CardInteraction] = Field(default_factory=list)
    
    # Cloning info
    cloned_cards: List[str] = Field(default_factory=list)  # IDs of cards cloned from this
    original_card_id: Optional[str] = None  # If this is a clone
    is_clone: bool = False
    
    # Social features
    liked_by: List[str] = Field(default_factory=list)
    saved_by: List[str] = Field(default_factory=list)
    comments_count: int = 0
    
    # Tags and categories
    tags: List[str] = Field(default_factory=list)
    categories: List[str] = Field(default_factory=list)
    
    # AI-generated content
    ai_description: Optional[str] = None
    ai_recommendations: List[str] = Field(default_factory=list)
    ai_travel_tips: List[str] = Field(default_factory=list)
    
    # Meta
    language: str = "en"
    currency: str = "NGN"
    
    class Settings:
        name = "experience_cards"
        indexes = [
            "experience_id",
            "owner.user_id",
            "card_code",
            "destination.city",
            "dates.start_date",
            "settings.is_public",
        ]
    
    # === Class Methods ===
    
    @classmethod
    def generate_card_code(cls) -> str:
        """Generate unique 8-character card code"""
        chars = string.ascii_uppercase + string.digits
        # Remove confusing characters
        chars = chars.replace('O', '').replace('0', '').replace('I', '').replace('1', '')
        code = ''.join(secrets.choice(chars) for _ in range(8))
        return f"QE-{code[:4]}-{code[4:]}"
    
    @classmethod
    async def create_from_experience(cls, experience) -> "ExperienceCard":
        """Create a card from a confirmed experience"""
        # Generate highlights from experience items
        highlights = []
        for item in experience.items[:6]:  # Max 6 highlights
            highlights.append(CardHighlight(
                type=item.type,
                name=item.name,
                description=item.description,
                image_url=item.image_url,
            ))
        
        card = cls(
            experience_id=str(experience.id),
            owner=CardOwner(
                user_id=experience.user_id,
                name=experience.user_name or "Traveler",
            ),
            card_code=cls.generate_card_code(),
            title=experience.title,
            description=experience.description,
            cover_image=experience.cover_image,
            images=experience.images,
            destination=experience.destination,
            origin=experience.origin,
            dates=experience.dates,
            travelers=experience.travelers,
            highlights=highlights,
            tags=experience.tags,
            categories=experience.categories,
        )
        
        return card
    
    # === Instance Methods ===
    
    def record_view(
        self,
        user_id: Optional[str] = None,
        user_email: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        location: Optional[Dict[str, float]] = None
    ) -> None:
        """Record a card view"""
        self.stats.view_count += 1
        
        interaction = CardInteraction(
            user_id=user_id,
            user_email=user_email,
            action="viewed",
            ip_address=ip_address,
            user_agent=user_agent,
            location=location,
        )
        
        # Keep only last 100 interactions
        self.recent_interactions = [interaction] + self.recent_interactions[:99]
        
        # Track unique viewers
        viewer_key = user_id or ip_address
        # Note: Full unique tracking would need a separate collection
    
    def record_share(self, user_id: Optional[str] = None) -> None:
        """Record a share action"""
        self.stats.share_count += 1
        self.recent_interactions.insert(0, CardInteraction(
            user_id=user_id,
            action="shared",
        ))
    
    def record_clone(self, cloned_card_id: str, user_id: str) -> None:
        """Record when someone clones this card"""
        self.stats.clone_count += 1
        self.cloned_cards.append(cloned_card_id)
        self.recent_interactions.insert(0, CardInteraction(
            user_id=user_id,
            action="cloned",
        ))
    
    def update_owner_location(
        self,
        latitude: float,
        longitude: float,
        accuracy: Optional[float] = None
    ) -> None:
        """Update owner's real-time location"""
        if not self.settings.show_real_time_location:
            return
        
        self.owner_location = CardLocation(
            user_id=self.owner.user_id,
            name=self.owner.name,
            latitude=latitude,
            longitude=longitude,
            accuracy=accuracy,
            is_sharing=True,
        )
    
    def calculate_distance_from(
        self,
        viewer_lat: float,
        viewer_lng: float
    ) -> Optional[TravelTimeEstimate]:
        """Calculate distance/time from viewer's location to destination"""
        from math import radians, sin, cos, sqrt, atan2
        
        if not self.destination.latitude or not self.destination.longitude:
            return None
        
        # Haversine formula for distance
        R = 6371  # Earth's radius in km
        
        lat1, lon1 = radians(viewer_lat), radians(viewer_lng)
        lat2 = radians(self.destination.latitude)
        lon2 = radians(self.destination.longitude)
        
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))
        distance = R * c
        
        # Rough time estimates
        driving_time = int((distance / 60) * 60)  # 60 km/h average
        flight_time = int((distance / 800) * 60) if distance > 200 else None  # 800 km/h
        
        return TravelTimeEstimate(
            from_location=TravelLocation(
                name="Your Location",
                city="",
                country="",
                latitude=viewer_lat,
                longitude=viewer_lng,
            ),
            to_destination=self.destination,
            driving_time_minutes=driving_time,
            driving_distance_km=round(distance, 1),
            flight_time_minutes=flight_time,
        )
    
    def get_public_data(self) -> Dict[str, Any]:
        """Get card data safe for public viewing"""
        data = {
            "card_code": self.card_code,
            "title": self.title,
            "description": self.description,
            "tagline": self.tagline,
            "cover_image": self.cover_image,
            "images": self.images[:4],
            "destination": self.destination.model_dump() if self.destination else None,
            "dates": {
                "start_date": self.dates.start_date.isoformat(),
                "end_date": self.dates.end_date.isoformat(),
            },
            "travelers": {
                "total": self.travelers.total_passengers,
            },
            "highlights": [h.model_dump() for h in self.highlights],
            "tags": self.tags,
            "stats": {
                "views": self.stats.view_count,
                "shares": self.stats.share_count,
            },
        }
        
        if self.settings.show_owner_name:
            data["owner"] = {
                "name": self.owner.name,
            }
            if self.settings.show_owner_avatar:
                data["owner"]["avatar_url"] = self.owner.avatar_url
        
        if self.settings.show_prices and self.pricing:
            data["pricing"] = {
                "total": self.pricing.grand_total,
                "currency": self.pricing.currency,
                "per_person": self.pricing.price_per_person,
            }
        
        if self.include_full_itinerary:
            data["itinerary"] = [
                {
                    "day": day.day_number,
                    "date": day.date.isoformat(),
                    "title": day.title,
                    "items_count": len(day.items),
                }
                for day in self.itinerary
            ]
        
        if self.settings.show_real_time_location and self.owner_location:
            data["owner_location"] = {
                "latitude": self.owner_location.latitude,
                "longitude": self.owner_location.longitude,
                "updated_at": self.owner_location.updated_at.isoformat(),
            }
        
        return data
    
    @property
    def share_url(self) -> str:
        """Generate shareable URL"""
        return f"https://queska.app/experience/{self.card_code}"
    
    @property
    def is_active(self) -> bool:
        """Check if card is still active"""
        if not self.settings.is_active:
            return False
        if self.settings.expires_at and self.settings.expires_at < datetime.utcnow():
            return False
        return True
    
    @property
    def days_until_trip(self) -> int:
        """Days until the trip starts"""
        return (self.dates.start_date - date.today()).days
    
    @property
    def is_trip_ongoing(self) -> bool:
        """Check if trip is currently happening"""
        today = date.today()
        return self.dates.start_date <= today <= self.dates.end_date

