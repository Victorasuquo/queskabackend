"""
Queska Backend - User Document Model
Regular user/traveler model with comprehensive features
"""

from datetime import datetime, date
from typing import Any, Dict, List, Optional

from beanie import Document, Indexed, PydanticObjectId
from pydantic import EmailStr, Field, field_validator

from app.core.constants import (
    AccountStatus,
    TravelInterest,
    SubscriptionPlan,
)


class UserPreferences(Document):
    """User travel preferences"""
    interests: List[str] = Field(default_factory=list)
    travel_style: Optional[str] = None  # budget, mid-range, luxury
    dietary_restrictions: List[str] = Field(default_factory=list)
    allergies: List[str] = Field(default_factory=list)
    accessibility_needs: List[str] = Field(default_factory=list)
    languages: List[str] = Field(default_factory=lambda: ["English"])
    currency: str = "NGN"
    preferred_airlines: List[str] = Field(default_factory=list)
    preferred_hotel_chains: List[str] = Field(default_factory=list)
    seat_preference: Optional[str] = None  # window, aisle, middle
    meal_preference: Optional[str] = None  # vegetarian, vegan, halal, kosher
    travel_companions: Optional[str] = None  # solo, couple, family, group
    
    class Settings:
        name = "user_preferences"


class UserAddress(Document):
    """User address"""
    label: str = "Home"  # Home, Work, Other
    street: Optional[str] = None
    city: str
    state: str
    country: str = "Nigeria"
    postal_code: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    is_primary: bool = True
    
    class Settings:
        name = "user_addresses"


class UserSubscription(Document):
    """User subscription details"""
    plan: SubscriptionPlan = SubscriptionPlan.FREE
    started_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    is_active: bool = True
    auto_renew: bool = True
    stripe_subscription_id: Optional[str] = None
    features: List[str] = Field(default_factory=list)
    
    class Settings:
        name = "user_subscriptions"


class UserStats(Document):
    """User statistics"""
    total_experiences: int = 0
    completed_experiences: int = 0
    upcoming_experiences: int = 0
    cancelled_experiences: int = 0
    total_bookings: int = 0
    total_spent: float = 0.0
    total_reviews: int = 0
    average_rating_given: float = 0.0
    total_saved: float = 0.0  # Savings from deals
    countries_visited: int = 0
    cities_visited: int = 0
    last_experience_at: Optional[datetime] = None
    last_booking_at: Optional[datetime] = None
    
    class Settings:
        name = "user_stats"


class UserSocialConnections(Document):
    """User social connections"""
    follower_ids: List[PydanticObjectId] = Field(default_factory=list)
    following_ids: List[PydanticObjectId] = Field(default_factory=list)
    blocked_ids: List[PydanticObjectId] = Field(default_factory=list)
    
    class Settings:
        name = "user_social_connections"


class UserActivityLog(Document):
    """User activity log entry"""
    action: str
    description: str
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    device_info: Optional[Dict[str, Any]] = None
    location: Optional[Dict[str, Any]] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Settings:
        name = "user_activity_logs"


class UserDevice(Document):
    """User registered device"""
    device_id: str
    device_type: str  # ios, android, web
    device_name: Optional[str] = None
    push_token: Optional[str] = None
    is_active: bool = True
    last_used_at: datetime = Field(default_factory=datetime.utcnow)
    registered_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Settings:
        name = "user_devices"


class UserPaymentMethod(Document):
    """User saved payment method"""
    type: str  # card, bank_account
    provider: str  # stripe, paystack
    last_four: Optional[str] = None
    brand: Optional[str] = None  # visa, mastercard
    exp_month: Optional[int] = None
    exp_year: Optional[int] = None
    is_default: bool = False
    stripe_payment_method_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Settings:
        name = "user_payment_methods"


class User(Document):
    """
    User Document Model
    Regular users/travelers on the platform
    """
    
    # Basic Information
    email: Indexed(EmailStr, unique=True)
    password_hash: str
    first_name: str
    last_name: str
    display_name: Optional[str] = None
    phone: Optional[str] = None
    phone_country_code: Optional[str] = None
    
    # Profile
    bio: Optional[str] = None
    profile_photo: Optional[str] = None
    cover_photo: Optional[str] = None
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    nationality: Optional[str] = None
    
    # Status
    status: AccountStatus = AccountStatus.PENDING
    is_email_verified: bool = False
    is_phone_verified: bool = False
    is_active: bool = True
    is_premium: bool = False
    
    # Location
    addresses: List[UserAddress] = Field(default_factory=list)
    current_location: Optional[Dict[str, Any]] = None  # GeoJSON Point
    home_location: Optional[Dict[str, Any]] = None  # GeoJSON Point
    timezone: str = "Africa/Lagos"
    
    # Preferences
    preferences: Optional[UserPreferences] = None
    notification_preferences: Dict[str, bool] = Field(default_factory=lambda: {
        "email_bookings": True,
        "email_promotions": False,
        "email_newsletter": False,
        "email_experience_updates": True,
        "email_agent_messages": True,
        "push_bookings": True,
        "push_messages": True,
        "push_promotions": False,
        "push_experience_updates": True,
        "sms_bookings": False,
        "sms_verification": True,
    })
    
    # Subscription
    subscription: Optional[UserSubscription] = None
    
    # Statistics
    stats: Optional[UserStats] = None
    
    # Social
    social_connections: Optional[UserSocialConnections] = None
    followers_count: int = 0
    following_count: int = 0
    experiences_count: int = 0
    reviews_count: int = 0
    
    # Agent Assignment
    assigned_agent_id: Optional[PydanticObjectId] = None
    
    # Favorites
    favorite_vendors: List[PydanticObjectId] = Field(default_factory=list)
    favorite_destinations: List[str] = Field(default_factory=list)
    favorite_experiences: List[PydanticObjectId] = Field(default_factory=list)
    wishlist: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Payment
    stripe_customer_id: Optional[str] = None
    payment_methods: List[UserPaymentMethod] = Field(default_factory=list)
    default_payment_method_id: Optional[str] = None
    
    # Devices
    devices: List[UserDevice] = Field(default_factory=list)
    
    # OAuth
    google_id: Optional[str] = None
    facebook_id: Optional[str] = None
    apple_id: Optional[str] = None
    
    # Security
    two_factor_enabled: bool = False
    two_factor_secret: Optional[str] = None
    backup_codes: List[str] = Field(default_factory=list)
    security_questions: List[Dict[str, str]] = Field(default_factory=list)
    
    # Referral
    referral_code: Optional[str] = None
    referred_by: Optional[PydanticObjectId] = None
    referral_count: int = 0
    referral_credits: float = 0.0
    
    # Activity
    activity_logs: List[UserActivityLog] = Field(default_factory=list)
    login_count: int = 0
    last_active_at: Optional[datetime] = None
    
    # Marketing
    marketing_consent: bool = False
    marketing_consent_at: Optional[datetime] = None
    acquisition_source: Optional[str] = None  # organic, referral, ads, etc.
    acquisition_campaign: Optional[str] = None
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_login_at: Optional[datetime] = None
    email_verified_at: Optional[datetime] = None
    phone_verified_at: Optional[datetime] = None
    
    # Soft delete
    is_deleted: bool = False
    deleted_at: Optional[datetime] = None
    deletion_reason: Optional[str] = None
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    class Settings:
        name = "users"
        indexes = [
            "email",
            "phone",
            "status",
            "is_active",
            "is_email_verified",
            "assigned_agent_id",
            "google_id",
            "facebook_id",
            "apple_id",
            "referral_code",
            [("first_name", "text"), ("last_name", "text"), ("bio", "text")],
            [("current_location", "2dsphere")],
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
    
    @property
    def primary_address(self) -> Optional[UserAddress]:
        """Get primary address"""
        for addr in self.addresses:
            if addr.is_primary:
                return addr
        return self.addresses[0] if self.addresses else None
    
    @property
    def default_payment_method(self) -> Optional[UserPaymentMethod]:
        """Get default payment method"""
        for pm in self.payment_methods:
            if pm.is_default:
                return pm
        return self.payment_methods[0] if self.payment_methods else None
    
    @property
    def is_profile_complete(self) -> bool:
        """Check if user profile is complete"""
        required = [
            self.first_name,
            self.last_name,
            self.phone,
            self.profile_photo,
            self.is_email_verified,
        ]
        return all(required)
    
    @property
    def profile_completion_percentage(self) -> int:
        """Calculate profile completion percentage"""
        fields = [
            self.first_name,
            self.last_name,
            self.phone,
            self.profile_photo,
            self.bio,
            self.date_of_birth,
            self.is_email_verified,
            self.primary_address,
            self.preferences,
        ]
        completed = sum(1 for f in fields if f)
        return int((completed / len(fields)) * 100)
    
    async def soft_delete(self, reason: Optional[str] = None) -> None:
        """Soft delete the user"""
        self.is_deleted = True
        self.deleted_at = datetime.utcnow()
        self.deletion_reason = reason
        self.is_active = False
        await self.save()
    
    async def add_activity_log(
        self,
        action: str,
        description: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> None:
        """Add activity log entry"""
        log = UserActivityLog(
            action=action,
            description=description,
            ip_address=ip_address,
            user_agent=user_agent
        )
        # Keep only last 100 activity logs
        if len(self.activity_logs) >= 100:
            self.activity_logs = self.activity_logs[-99:]
        self.activity_logs.append(log)
        await self.save()
    
    async def add_follower(self, follower_id: PydanticObjectId) -> None:
        """Add a follower"""
        if not self.social_connections:
            self.social_connections = UserSocialConnections()
        if follower_id not in self.social_connections.follower_ids:
            self.social_connections.follower_ids.append(follower_id)
            self.followers_count += 1
            await self.save()
    
    async def remove_follower(self, follower_id: PydanticObjectId) -> None:
        """Remove a follower"""
        if self.social_connections and follower_id in self.social_connections.follower_ids:
            self.social_connections.follower_ids.remove(follower_id)
            self.followers_count = max(0, self.followers_count - 1)
            await self.save()
    
    async def follow_user(self, user_id: PydanticObjectId) -> None:
        """Follow another user"""
        if not self.social_connections:
            self.social_connections = UserSocialConnections()
        if user_id not in self.social_connections.following_ids:
            self.social_connections.following_ids.append(user_id)
            self.following_count += 1
            await self.save()
    
    async def unfollow_user(self, user_id: PydanticObjectId) -> None:
        """Unfollow a user"""
        if self.social_connections and user_id in self.social_connections.following_ids:
            self.social_connections.following_ids.remove(user_id)
            self.following_count = max(0, self.following_count - 1)
            await self.save()
    
    async def add_favorite_vendor(self, vendor_id: PydanticObjectId) -> None:
        """Add vendor to favorites"""
        if vendor_id not in self.favorite_vendors:
            self.favorite_vendors.append(vendor_id)
            await self.save()
    
    async def remove_favorite_vendor(self, vendor_id: PydanticObjectId) -> None:
        """Remove vendor from favorites"""
        if vendor_id in self.favorite_vendors:
            self.favorite_vendors.remove(vendor_id)
            await self.save()
    
    async def add_favorite_destination(self, destination: str) -> None:
        """Add destination to favorites"""
        if destination not in self.favorite_destinations:
            self.favorite_destinations.append(destination)
            await self.save()
    
    async def remove_favorite_destination(self, destination: str) -> None:
        """Remove destination from favorites"""
        if destination in self.favorite_destinations:
            self.favorite_destinations.remove(destination)
            await self.save()
    
    async def update_stats(self, updates: Dict[str, Any]) -> None:
        """Update user statistics"""
        if not self.stats:
            self.stats = UserStats()
        for key, value in updates.items():
            if hasattr(self.stats, key):
                setattr(self.stats, key, value)
        await self.save()
    
    async def increment_stat(self, stat_name: str, value: float = 1) -> None:
        """Increment a stat value"""
        if not self.stats:
            self.stats = UserStats()
        if hasattr(self.stats, stat_name):
            current = getattr(self.stats, stat_name)
            setattr(self.stats, stat_name, current + value)
            await self.save()
    
    def to_public_dict(self) -> Dict[str, Any]:
        """Return user data safe for public consumption"""
        return {
            "id": str(self.id),
            "first_name": self.first_name,
            "last_name": self.last_name,
            "display_name": self.display_name,
            "full_name": self.full_name,
            "bio": self.bio,
            "profile_photo": self.profile_photo,
            "cover_photo": self.cover_photo,
            "followers_count": self.followers_count,
            "following_count": self.following_count,
            "experiences_count": self.experiences_count,
            "reviews_count": self.reviews_count,
            "favorite_destinations": self.favorite_destinations,
            "created_at": self.created_at.isoformat(),
        }
