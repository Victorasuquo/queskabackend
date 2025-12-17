"""
Queska Backend - Vendor Document Model
Vendor model for hotels, restaurants, tour operators, etc.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from beanie import Document, Indexed, PydanticObjectId
from pydantic import BaseModel, EmailStr, Field, field_validator

from app.core.constants import (
    AccountStatus,
    VendorCategory,
    VerificationStatus,
    CancellationPolicy,
    SubscriptionPlan,
)


# === Embedded Models (use BaseModel, NOT Document) ===

class VendorAddress(BaseModel):
    """Vendor address embedded document"""
    street: Optional[str] = None
    city: str = ""
    state: str = ""
    country: str = "Nigeria"
    postal_code: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    formatted_address: Optional[str] = None


class VendorContact(BaseModel):
    """Vendor contact information"""
    phone: Optional[str] = None
    phone_secondary: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    whatsapp: Optional[str] = None


class VendorSocialLinks(BaseModel):
    """Vendor social media links"""
    facebook: Optional[str] = None
    instagram: Optional[str] = None
    twitter: Optional[str] = None
    linkedin: Optional[str] = None
    youtube: Optional[str] = None
    tiktok: Optional[str] = None
    tripadvisor: Optional[str] = None
    google_business: Optional[str] = None


class DayHours(BaseModel):
    """Operating hours for a single day"""
    is_open: bool = True
    open_time: Optional[str] = "09:00"
    close_time: Optional[str] = "17:00"


class VendorOperatingHours(BaseModel):
    """Vendor operating hours"""
    monday: Optional[DayHours] = None
    tuesday: Optional[DayHours] = None
    wednesday: Optional[DayHours] = None
    thursday: Optional[DayHours] = None
    friday: Optional[DayHours] = None
    saturday: Optional[DayHours] = None
    sunday: Optional[DayHours] = None
    timezone: str = "Africa/Lagos"
    is_24_hours: bool = False
    special_hours: Optional[List[Dict[str, Any]]] = Field(default_factory=list)


class VendorBankAccount(BaseModel):
    """Vendor bank account for payouts"""
    bank_name: str
    account_name: str
    account_number: str
    bank_code: Optional[str] = None
    routing_number: Optional[str] = None
    swift_code: Optional[str] = None
    currency: str = "NGN"
    is_verified: bool = False
    is_primary: bool = True
    verified_at: Optional[datetime] = None


class VendorCommission(BaseModel):
    """Vendor commission structure"""
    type: str = "percentage"
    rate: float = 15.0
    fixed_amount: Optional[float] = None
    tiers: Optional[List[Dict[str, Any]]] = None
    currency: str = "NGN"
    effective_from: datetime = Field(default_factory=datetime.utcnow)


class VendorRating(BaseModel):
    """Vendor rating summary"""
    average: float = 0.0
    count: int = 0
    breakdown: Dict[str, int] = Field(default_factory=lambda: {
        "5": 0, "4": 0, "3": 0, "2": 0, "1": 0
    })
    last_updated: datetime = Field(default_factory=datetime.utcnow)


class VendorMedia(BaseModel):
    """Vendor media items"""
    logo: Optional[str] = None
    cover_image: Optional[str] = None
    gallery: List[Dict[str, Any]] = Field(default_factory=list)
    videos: List[Dict[str, Any]] = Field(default_factory=list)
    documents: List[Dict[str, Any]] = Field(default_factory=list)


class VendorVerification(BaseModel):
    """Vendor verification documents and status"""
    status: VerificationStatus = VerificationStatus.PENDING
    business_registration: Optional[str] = None
    tax_certificate: Optional[str] = None
    license_document: Optional[str] = None
    identity_document: Optional[str] = None
    proof_of_address: Optional[str] = None
    submitted_at: Optional[datetime] = None
    reviewed_at: Optional[datetime] = None
    reviewed_by: Optional[str] = None
    rejection_reason: Optional[str] = None
    notes: Optional[str] = None


class VendorSubscription(BaseModel):
    """Vendor subscription details"""
    plan: SubscriptionPlan = SubscriptionPlan.FREE
    started_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    is_active: bool = True
    auto_renew: bool = True
    payment_method: Optional[str] = None
    stripe_subscription_id: Optional[str] = None
    features: List[str] = Field(default_factory=list)


class VendorPriceRange(BaseModel):
    """Vendor price range"""
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    currency: str = "NGN"


class VendorAnalytics(BaseModel):
    """Vendor analytics summary"""
    total_bookings: int = 0
    total_revenue: float = 0.0
    total_reviews: int = 0
    total_views: int = 0
    total_favorites: int = 0
    conversion_rate: float = 0.0
    average_booking_value: float = 0.0
    monthly_stats: Dict[str, Any] = Field(default_factory=dict)
    last_booking_at: Optional[datetime] = None
    last_updated: datetime = Field(default_factory=datetime.utcnow)


# === Main Vendor Document ===

class Vendor(Document):
    """
    Vendor Document Model
    Represents businesses that provide services on the platform
    """
    
    # Basic Information
    email: Indexed(EmailStr, unique=True)
    password_hash: str
    business_name: Indexed(str)
    slug: Indexed(str, unique=True)
    category: VendorCategory
    subcategories: List[str] = Field(default_factory=list)
    description: Optional[str] = None
    short_description: Optional[str] = None
    tagline: Optional[str] = None
    
    # Owner Information
    owner_first_name: str
    owner_last_name: str
    owner_phone: str
    owner_email: Optional[EmailStr] = None
    
    # Status
    status: AccountStatus = AccountStatus.PENDING
    is_verified: bool = False
    is_featured: bool = False
    is_premium: bool = False
    is_active: bool = True
    
    # Location & Contact (Embedded documents)
    address: Optional[VendorAddress] = None
    contact: Optional[VendorContact] = None
    social_links: Optional[VendorSocialLinks] = None
    operating_hours: Optional[VendorOperatingHours] = None
    
    # GeoJSON for spatial queries
    location: Optional[Dict[str, Any]] = None
    
    # Financial
    bank_accounts: List[VendorBankAccount] = Field(default_factory=list)
    commission: Optional[VendorCommission] = None
    stripe_account_id: Optional[str] = None
    stripe_connected: bool = False
    payout_enabled: bool = False
    
    # Media
    media: Optional[VendorMedia] = None
    
    # Verification
    verification: Optional[VendorVerification] = None
    
    # Subscription
    subscription: Optional[VendorSubscription] = None
    
    # Rating & Reviews
    rating: Optional[VendorRating] = None
    
    # Analytics
    analytics: Optional[VendorAnalytics] = None
    
    # Settings & Preferences
    settings: Dict[str, Any] = Field(default_factory=dict)
    notification_preferences: Dict[str, bool] = Field(default_factory=lambda: {
        "email_bookings": True,
        "email_reviews": True,
        "email_marketing": False,
        "push_bookings": True,
        "push_messages": True,
        "sms_bookings": False,
    })
    
    # Policies
    cancellation_policy: CancellationPolicy = CancellationPolicy.MODERATE
    refund_policy: Optional[str] = None
    terms_and_conditions: Optional[str] = None
    
    # Services & Amenities
    amenities: List[str] = Field(default_factory=list)
    services: List[str] = Field(default_factory=list)
    features: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    
    # Pricing
    price_range: Optional[VendorPriceRange] = None
    currency: str = "NGN"
    
    # Languages
    languages_spoken: List[str] = Field(default_factory=lambda: ["English"])
    
    # Certifications & Awards
    certifications: List[Dict[str, Any]] = Field(default_factory=list)
    awards: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Integration IDs
    external_ids: Dict[str, str] = Field(default_factory=dict)
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_login_at: Optional[datetime] = None
    verified_at: Optional[datetime] = None
    
    # Soft delete
    is_deleted: bool = False
    deleted_at: Optional[datetime] = None
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    class Settings:
        name = "vendors"
        indexes = [
            "email",
            "slug",
            "category",
            "status",
            "is_verified",
            "is_featured",
            "is_active",
            [("location", "2dsphere")],
            [("business_name", "text"), ("description", "text")],
        ]
    
    @field_validator("email", mode="before")
    @classmethod
    def lowercase_email(cls, v: str) -> str:
        return v.lower() if v else v
    
    @property
    def full_owner_name(self) -> str:
        """Get owner's full name"""
        return f"{self.owner_first_name} {self.owner_last_name}"
    
    @property
    def is_complete(self) -> bool:
        """Check if vendor profile is complete"""
        required = [
            self.business_name,
            self.description,
            self.category,
            self.address,
            self.contact,
        ]
        return all(required)
    
    async def soft_delete(self) -> None:
        """Soft delete the vendor"""
        self.is_deleted = True
        self.deleted_at = datetime.utcnow()
        self.is_active = False
        await self.save()
    
    async def activate(self) -> None:
        """Activate vendor account"""
        self.status = AccountStatus.ACTIVE
        self.is_active = True
        self.updated_at = datetime.utcnow()
        await self.save()
    
    async def suspend(self, reason: Optional[str] = None) -> None:
        """Suspend vendor account"""
        self.status = AccountStatus.SUSPENDED
        self.is_active = False
        if reason:
            self.metadata["suspension_reason"] = reason
        self.updated_at = datetime.utcnow()
        await self.save()
    
    async def verify(self, admin_id: PydanticObjectId) -> None:
        """Mark vendor as verified"""
        self.is_verified = True
        self.verified_at = datetime.utcnow()
        if self.verification:
            self.verification.status = VerificationStatus.VERIFIED
            self.verification.reviewed_at = datetime.utcnow()
            self.verification.reviewed_by = str(admin_id)
        await self.save()
    
    async def update_rating(self, new_rating: int) -> None:
        """Update vendor rating with new review"""
        if not self.rating:
            self.rating = VendorRating()
        
        self.rating.breakdown[str(new_rating)] += 1
        self.rating.count += 1
        
        total = sum(
            int(k) * v for k, v in self.rating.breakdown.items()
        )
        self.rating.average = round(total / self.rating.count, 2)
        self.rating.last_updated = datetime.utcnow()
        
        await self.save()
    
    def to_public_dict(self) -> Dict[str, Any]:
        """Return vendor data safe for public consumption"""
        return {
            "id": str(self.id),
            "business_name": self.business_name,
            "slug": self.slug,
            "category": self.category.value,
            "subcategories": self.subcategories,
            "description": self.description,
            "short_description": self.short_description,
            "tagline": self.tagline,
            "is_verified": self.is_verified,
            "is_featured": self.is_featured,
            "is_premium": self.is_premium,
            "address": self.address.model_dump() if self.address else None,
            "contact": {
                "phone": self.contact.phone if self.contact else None,
                "email": self.contact.email if self.contact else None,
                "website": self.contact.website if self.contact else None,
            } if self.contact else None,
            "social_links": self.social_links.model_dump() if self.social_links else None,
            "operating_hours": self.operating_hours.model_dump() if self.operating_hours else None,
            "media": self.media.model_dump() if self.media else None,
            "rating": self.rating.model_dump() if self.rating else None,
            "amenities": self.amenities,
            "services": self.services,
            "features": self.features,
            "tags": self.tags,
            "price_range": self.price_range,
            "currency": self.currency,
            "languages_spoken": self.languages_spoken,
            "cancellation_policy": self.cancellation_policy.value,
            "created_at": self.created_at.isoformat(),
        }
