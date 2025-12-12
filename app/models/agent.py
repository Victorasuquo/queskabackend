"""
Queska Backend - Agent Document Model
Travel Agent model for independent agents and agencies
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from beanie import Document, Indexed, PydanticObjectId
from pydantic import EmailStr, Field, field_validator

from app.core.constants import (
    AccountStatus,
    AgentType,
    VerificationStatus,
    SubscriptionPlan,
    CommissionType,
)


class AgentAddress(Document):
    """Agent address embedded document"""
    street: Optional[str] = None
    city: str
    state: str
    country: str = "Nigeria"
    postal_code: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    formatted_address: Optional[str] = None
    
    class Settings:
        name = "agent_addresses"


class AgentContact(Document):
    """Agent contact information"""
    phone: str
    phone_secondary: Optional[str] = None
    email: EmailStr
    website: Optional[str] = None
    whatsapp: Optional[str] = None
    
    class Settings:
        name = "agent_contacts"


class AgentSocialLinks(Document):
    """Agent social media links"""
    facebook: Optional[str] = None
    instagram: Optional[str] = None
    twitter: Optional[str] = None
    linkedin: Optional[str] = None
    youtube: Optional[str] = None
    
    class Settings:
        name = "agent_social_links"


class AgentBankAccount(Document):
    """Agent bank account for commission payouts"""
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
    
    class Settings:
        name = "agent_bank_accounts"


class AgentCommission(Document):
    """Agent commission structure"""
    type: str = "percentage"
    rate: float = 10.0  # Default 10% commission on bookings
    fixed_amount: Optional[float] = None
    tiers: Optional[List[Dict[str, Any]]] = None
    currency: str = "NGN"
    effective_from: datetime = Field(default_factory=datetime.utcnow)
    
    class Settings:
        name = "agent_commissions"


class AgentRating(Document):
    """Agent rating summary"""
    average: float = 0.0
    count: int = 0
    breakdown: Dict[str, int] = Field(default_factory=lambda: {
        "5": 0, "4": 0, "3": 0, "2": 0, "1": 0
    })
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    
    class Settings:
        name = "agent_ratings"


class AgentMedia(Document):
    """Agent media items"""
    profile_photo: Optional[str] = None
    cover_image: Optional[str] = None
    gallery: List[Dict[str, Any]] = Field(default_factory=list)
    portfolio: List[Dict[str, Any]] = Field(default_factory=list)
    
    class Settings:
        name = "agent_media"


class AgentVerification(Document):
    """Agent verification documents and status"""
    status: VerificationStatus = VerificationStatus.PENDING
    identity_document: Optional[str] = None  # Document URL
    license_document: Optional[str] = None  # Travel agent license
    certification: Optional[str] = None  # Professional certification
    proof_of_address: Optional[str] = None
    agency_registration: Optional[str] = None  # If agency
    submitted_at: Optional[datetime] = None
    reviewed_at: Optional[datetime] = None
    reviewed_by: Optional[PydanticObjectId] = None
    rejection_reason: Optional[str] = None
    notes: Optional[str] = None
    
    class Settings:
        name = "agent_verifications"


class AgentSubscription(Document):
    """Agent subscription details"""
    plan: SubscriptionPlan = SubscriptionPlan.FREE
    started_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    is_active: bool = True
    auto_renew: bool = True
    payment_method: Optional[str] = None
    stripe_subscription_id: Optional[str] = None
    features: List[str] = Field(default_factory=list)
    
    class Settings:
        name = "agent_subscriptions"


class AgentAnalytics(Document):
    """Agent performance analytics"""
    total_bookings: int = 0
    total_clients: int = 0
    total_revenue: float = 0.0
    total_commission_earned: float = 0.0
    total_reviews: int = 0
    conversion_rate: float = 0.0
    average_booking_value: float = 0.0
    monthly_stats: Dict[str, Any] = Field(default_factory=dict)
    top_destinations: List[Dict[str, Any]] = Field(default_factory=list)
    last_booking_at: Optional[datetime] = None
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    
    class Settings:
        name = "agent_analytics"


class AgentAgency(Document):
    """Agency information if agent belongs to an agency"""
    agency_id: Optional[PydanticObjectId] = None
    agency_name: Optional[str] = None
    role: Optional[str] = None  # senior_agent, junior_agent, manager
    joined_at: Optional[datetime] = None
    
    class Settings:
        name = "agent_agencies"


class AgentSpecialization(Document):
    """Agent specialization areas"""
    destinations: List[str] = Field(default_factory=list)  # Countries/regions
    travel_types: List[str] = Field(default_factory=list)  # luxury, adventure, family
    services: List[str] = Field(default_factory=list)  # flights, hotels, tours
    languages: List[str] = Field(default_factory=lambda: ["English"])
    
    class Settings:
        name = "agent_specializations"


class Agent(Document):
    """
    Agent Document Model
    Represents travel agents who can book experiences for clients
    """
    
    # Basic Information
    email: Indexed(EmailStr, unique=True)
    password_hash: str
    first_name: str
    last_name: str
    display_name: Optional[str] = None
    slug: Indexed(str, unique=True)
    agent_type: AgentType = AgentType.INDEPENDENT
    bio: Optional[str] = None
    tagline: Optional[str] = None
    
    # Status
    status: AccountStatus = AccountStatus.PENDING
    is_verified: bool = False
    is_featured: bool = False
    is_premium: bool = False
    is_active: bool = True
    is_available: bool = True  # Available to take new clients
    
    # Contact & Location
    phone: str
    address: Optional[AgentAddress] = None
    contact: Optional[AgentContact] = None
    social_links: Optional[AgentSocialLinks] = None
    
    # GeoJSON for spatial queries
    location: Optional[Dict[str, Any]] = None
    
    # Agency Association
    agency: Optional[AgentAgency] = None
    
    # Specialization
    specialization: Optional[AgentSpecialization] = None
    
    # Financial
    bank_accounts: List[AgentBankAccount] = Field(default_factory=list)
    commission: Optional[AgentCommission] = None
    stripe_account_id: Optional[str] = None
    stripe_connected: bool = False
    payout_enabled: bool = False
    
    # Referral System
    referral_code: Optional[str] = None
    referred_by: Optional[PydanticObjectId] = None
    referral_count: int = 0
    referral_earnings: float = 0.0
    
    # Media
    media: Optional[AgentMedia] = None
    
    # Verification
    verification: Optional[AgentVerification] = None
    
    # Subscription
    subscription: Optional[AgentSubscription] = None
    
    # Rating & Reviews
    rating: Optional[AgentRating] = None
    
    # Analytics
    analytics: Optional[AgentAnalytics] = None
    
    # Clients
    client_ids: List[PydanticObjectId] = Field(default_factory=list)
    max_clients: int = 50  # Max concurrent clients
    
    # Settings & Preferences
    settings: Dict[str, Any] = Field(default_factory=dict)
    notification_preferences: Dict[str, bool] = Field(default_factory=lambda: {
        "email_bookings": True,
        "email_client_messages": True,
        "email_reviews": True,
        "email_marketing": False,
        "push_bookings": True,
        "push_messages": True,
        "sms_bookings": False,
    })
    
    # Availability
    availability_schedule: Optional[Dict[str, Any]] = None
    response_time: Optional[str] = None  # "within_1_hour", "within_24_hours"
    
    # Certifications & Awards
    certifications: List[Dict[str, Any]] = Field(default_factory=list)
    awards: List[Dict[str, Any]] = Field(default_factory=list)
    years_of_experience: int = 0
    
    # White-label booking links
    booking_link: Optional[str] = None
    custom_domain: Optional[str] = None
    
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
        name = "agents"
        indexes = [
            "email",
            "slug",
            "agent_type",
            "status",
            "is_verified",
            "is_featured",
            "is_active",
            "referral_code",
            [("location", "2dsphere")],
            [("first_name", "text"), ("last_name", "text"), ("bio", "text")],
        ]
    
    @field_validator("email", mode="before")
    @classmethod
    def lowercase_email(cls, v: str) -> str:
        return v.lower() if v else v
    
    @property
    def full_name(self) -> str:
        """Get agent's full name"""
        return f"{self.first_name} {self.last_name}"
    
    @property
    def public_name(self) -> str:
        """Get display name or full name"""
        return self.display_name or self.full_name
    
    @property
    def is_complete(self) -> bool:
        """Check if agent profile is complete"""
        required = [
            self.first_name,
            self.last_name,
            self.phone,
            self.bio,
            self.media and self.media.profile_photo,
        ]
        return all(required)
    
    @property
    def client_count(self) -> int:
        """Get current client count"""
        return len(self.client_ids)
    
    @property
    def can_accept_clients(self) -> bool:
        """Check if agent can accept more clients"""
        return self.is_available and self.client_count < self.max_clients
    
    async def soft_delete(self) -> None:
        """Soft delete the agent"""
        self.is_deleted = True
        self.deleted_at = datetime.utcnow()
        self.is_active = False
        await self.save()
    
    async def activate(self) -> None:
        """Activate agent account"""
        self.status = AccountStatus.ACTIVE
        self.is_active = True
        self.updated_at = datetime.utcnow()
        await self.save()
    
    async def suspend(self, reason: Optional[str] = None) -> None:
        """Suspend agent account"""
        self.status = AccountStatus.SUSPENDED
        self.is_active = False
        if reason:
            self.metadata["suspension_reason"] = reason
        self.updated_at = datetime.utcnow()
        await self.save()
    
    async def verify(self, admin_id: PydanticObjectId) -> None:
        """Mark agent as verified"""
        self.is_verified = True
        self.verified_at = datetime.utcnow()
        if self.verification:
            self.verification.status = VerificationStatus.VERIFIED
            self.verification.reviewed_at = datetime.utcnow()
            self.verification.reviewed_by = admin_id
        await self.save()
    
    async def add_client(self, client_id: PydanticObjectId) -> bool:
        """Add a client to the agent"""
        if not self.can_accept_clients:
            return False
        if client_id not in self.client_ids:
            self.client_ids.append(client_id)
            await self.save()
        return True
    
    async def remove_client(self, client_id: PydanticObjectId) -> None:
        """Remove a client from the agent"""
        if client_id in self.client_ids:
            self.client_ids.remove(client_id)
            await self.save()
    
    async def update_rating(self, new_rating: int) -> None:
        """Update agent rating with new review"""
        if not self.rating:
            self.rating = AgentRating()
        
        self.rating.breakdown[str(new_rating)] += 1
        self.rating.count += 1
        
        total = sum(
            int(k) * v for k, v in self.rating.breakdown.items()
        )
        self.rating.average = round(total / self.rating.count, 2)
        self.rating.last_updated = datetime.utcnow()
        
        await self.save()
    
    async def add_commission_earning(self, amount: float) -> None:
        """Add commission earning to analytics"""
        if not self.analytics:
            self.analytics = AgentAnalytics()
        
        self.analytics.total_commission_earned += amount
        self.analytics.last_updated = datetime.utcnow()
        await self.save()
    
    def to_public_dict(self) -> Dict[str, Any]:
        """Return agent data safe for public consumption"""
        return {
            "id": str(self.id),
            "first_name": self.first_name,
            "last_name": self.last_name,
            "display_name": self.display_name,
            "full_name": self.full_name,
            "slug": self.slug,
            "agent_type": self.agent_type.value,
            "bio": self.bio,
            "tagline": self.tagline,
            "is_verified": self.is_verified,
            "is_featured": self.is_featured,
            "is_premium": self.is_premium,
            "is_available": self.is_available,
            "address": {
                "city": self.address.city if self.address else None,
                "state": self.address.state if self.address else None,
                "country": self.address.country if self.address else None,
            } if self.address else None,
            "contact": {
                "phone": self.contact.phone if self.contact else self.phone,
                "email": self.contact.email if self.contact else self.email,
                "website": self.contact.website if self.contact else None,
            },
            "social_links": self.social_links.model_dump() if self.social_links else None,
            "specialization": self.specialization.model_dump() if self.specialization else None,
            "media": {
                "profile_photo": self.media.profile_photo if self.media else None,
                "cover_image": self.media.cover_image if self.media else None,
            } if self.media else None,
            "rating": self.rating.model_dump() if self.rating else None,
            "certifications": self.certifications,
            "years_of_experience": self.years_of_experience,
            "response_time": self.response_time,
            "booking_link": self.booking_link,
            "client_count": self.client_count,
            "can_accept_clients": self.can_accept_clients,
            "created_at": self.created_at.isoformat(),
        }

