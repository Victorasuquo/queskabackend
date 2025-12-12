"""
Queska Backend - Base Document Model
Base class for all MongoDB document models using Beanie ODM
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from beanie import Document, PydanticObjectId
from pydantic import Field


class BaseDocument(Document):
    """
    Base document model with common fields for all collections
    """
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Soft delete
    is_deleted: bool = Field(default=False)
    deleted_at: Optional[datetime] = None
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    class Settings:
        use_state_management = True
        validate_on_save = True
    
    async def soft_delete(self) -> None:
        """Soft delete the document"""
        self.is_deleted = True
        self.deleted_at = datetime.utcnow()
        await self.save()
    
    async def restore(self) -> None:
        """Restore a soft-deleted document"""
        self.is_deleted = False
        self.deleted_at = None
        await self.save()
    
    def update_timestamp(self) -> None:
        """Update the updated_at timestamp"""
        self.updated_at = datetime.utcnow()
    
    async def save_with_timestamp(self, *args, **kwargs) -> None:
        """Save document with updated timestamp"""
        self.update_timestamp()
        await self.save(*args, **kwargs)


class Address(Document):
    """Embedded address model"""
    street: Optional[str] = None
    city: str
    state: str
    country: str
    postal_code: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    formatted_address: Optional[str] = None
    
    class Settings:
        name = "addresses"


class ContactInfo(Document):
    """Embedded contact information model"""
    phone: Optional[str] = None
    phone_secondary: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    whatsapp: Optional[str] = None
    telegram: Optional[str] = None
    
    class Settings:
        name = "contact_info"


class SocialLinks(Document):
    """Social media links"""
    facebook: Optional[str] = None
    instagram: Optional[str] = None
    twitter: Optional[str] = None
    linkedin: Optional[str] = None
    youtube: Optional[str] = None
    tiktok: Optional[str] = None
    
    class Settings:
        name = "social_links"


class OperatingHours(Document):
    """Operating hours for a business"""
    monday: Optional[Dict[str, str]] = None  # {"open": "09:00", "close": "17:00"}
    tuesday: Optional[Dict[str, str]] = None
    wednesday: Optional[Dict[str, str]] = None
    thursday: Optional[Dict[str, str]] = None
    friday: Optional[Dict[str, str]] = None
    saturday: Optional[Dict[str, str]] = None
    sunday: Optional[Dict[str, str]] = None
    timezone: str = "Africa/Lagos"
    is_24_hours: bool = False
    
    class Settings:
        name = "operating_hours"


class GeoLocation(Document):
    """GeoJSON location for spatial queries"""
    type: str = "Point"
    coordinates: List[float] = Field(default_factory=lambda: [0.0, 0.0])  # [longitude, latitude]
    
    class Settings:
        name = "geo_locations"


class PriceRange(Document):
    """Price range model"""
    min_price: float = 0.0
    max_price: float = 0.0
    currency: str = "NGN"
    
    class Settings:
        name = "price_ranges"


class Rating(Document):
    """Rating summary model"""
    average: float = 0.0
    count: int = 0
    breakdown: Dict[str, int] = Field(default_factory=lambda: {
        "5": 0, "4": 0, "3": 0, "2": 0, "1": 0
    })
    
    class Settings:
        name = "ratings"


class MediaItem(Document):
    """Media item model for images, videos, etc."""
    url: str
    type: str = "image"  # image, video, document
    filename: Optional[str] = None
    size: Optional[int] = None
    mime_type: Optional[str] = None
    alt_text: Optional[str] = None
    is_primary: bool = False
    order: int = 0
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Settings:
        name = "media_items"


class BankAccount(Document):
    """Bank account information for payouts"""
    bank_name: str
    account_name: str
    account_number: str
    bank_code: Optional[str] = None
    routing_number: Optional[str] = None
    swift_code: Optional[str] = None
    currency: str = "NGN"
    is_verified: bool = False
    is_primary: bool = False
    
    class Settings:
        name = "bank_accounts"


class Commission(Document):
    """Commission structure model"""
    type: str = "percentage"  # percentage, fixed, tiered
    rate: float = 0.0
    fixed_amount: Optional[float] = None
    tiers: Optional[List[Dict[str, Any]]] = None
    currency: str = "NGN"
    
    class Settings:
        name = "commissions"

