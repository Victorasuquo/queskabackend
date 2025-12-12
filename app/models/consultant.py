"""
Queska Backend - Consultant Document Model
Travel consultants providing advisory services
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from beanie import Document, Indexed, PydanticObjectId
from pydantic import EmailStr, Field, field_validator

from app.core.constants import (
    AccountStatus,
    VerificationStatus,
    SubscriptionPlan,
)


class ConsultantAddress(Document):
    """Consultant address"""
    street: Optional[str] = None
    city: str
    state: str
    country: str = "Nigeria"
    postal_code: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    
    class Settings:
        name = "consultant_addresses"


class ConsultantSpecialization(Document):
    """Consultant specialization areas"""
    expertise_areas: List[str] = Field(default_factory=list)  # visa, corporate, luxury, etc.
    destinations: List[str] = Field(default_factory=list)
    languages: List[str] = Field(default_factory=lambda: ["English"])
    services: List[str] = Field(default_factory=list)
    
    class Settings:
        name = "consultant_specializations"


class ConsultantRating(Document):
    """Consultant rating summary"""
    average: float = 0.0
    count: int = 0
    breakdown: Dict[str, int] = Field(default_factory=lambda: {
        "5": 0, "4": 0, "3": 0, "2": 0, "1": 0
    })
    
    class Settings:
        name = "consultant_ratings"


class ConsultantVerification(Document):
    """Consultant verification status"""
    status: VerificationStatus = VerificationStatus.PENDING
    identity_document: Optional[str] = None
    certification: Optional[str] = None
    submitted_at: Optional[datetime] = None
    reviewed_at: Optional[datetime] = None
    reviewed_by: Optional[PydanticObjectId] = None
    rejection_reason: Optional[str] = None
    
    class Settings:
        name = "consultant_verifications"


class ConsultantAnalytics(Document):
    """Consultant performance analytics"""
    total_consultations: int = 0
    total_clients: int = 0
    total_revenue: float = 0.0
    total_reviews: int = 0
    average_session_duration: float = 0.0  # minutes
    
    class Settings:
        name = "consultant_analytics"


class Consultant(Document):
    """
    Consultant Document Model
    Travel consultants providing advisory services
    """
    
    # Basic Information
    email: Indexed(EmailStr, unique=True)
    password_hash: str
    first_name: str
    last_name: str
    display_name: Optional[str] = None
    slug: Indexed(str, unique=True)
    phone: str
    
    # Profile
    bio: Optional[str] = None
    tagline: Optional[str] = None
    profile_photo: Optional[str] = None
    cover_photo: Optional[str] = None
    
    # Status
    status: AccountStatus = AccountStatus.PENDING
    is_verified: bool = False
    is_featured: bool = False
    is_active: bool = True
    is_available: bool = True
    
    # Location
    address: Optional[ConsultantAddress] = None
    location: Optional[Dict[str, Any]] = None  # GeoJSON
    
    # Specialization
    specialization: Optional[ConsultantSpecialization] = None
    
    # Pricing
    hourly_rate: float = 0.0
    currency: str = "NGN"
    consultation_types: List[Dict[str, Any]] = Field(default_factory=list)  # video, phone, chat
    
    # Verification
    verification: Optional[ConsultantVerification] = None
    
    # Rating
    rating: Optional[ConsultantRating] = None
    
    # Analytics
    analytics: Optional[ConsultantAnalytics] = None
    
    # Subscription
    subscription_plan: SubscriptionPlan = SubscriptionPlan.FREE
    
    # Availability
    availability_schedule: Optional[Dict[str, Any]] = None
    response_time: Optional[str] = None
    
    # Experience
    years_of_experience: int = 0
    certifications: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Bank Account
    bank_accounts: List[Dict[str, Any]] = Field(default_factory=list)
    stripe_account_id: Optional[str] = None
    payout_enabled: bool = False
    
    # Settings
    notification_preferences: Dict[str, bool] = Field(default_factory=lambda: {
        "email_bookings": True,
        "email_messages": True,
        "push_bookings": True,
    })
    
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
        name = "consultants"
        indexes = [
            "email",
            "slug",
            "status",
            "is_verified",
            "is_featured",
            "is_active",
            [("location", "2dsphere")],
        ]
    
    @field_validator("email", mode="before")
    @classmethod
    def lowercase_email(cls, v: str) -> str:
        return v.lower() if v else v
    
    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"
    
    @property
    def public_name(self) -> str:
        return self.display_name or self.full_name

