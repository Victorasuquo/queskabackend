"""
Queska Backend - Application Constants
Centralized constants used throughout the application
"""

from enum import Enum
from typing import Dict, List


# === User Types ===
class UserType(str, Enum):
    """Types of users in the system"""
    USER = "user"
    ADMIN = "admin"
    VENDOR = "vendor"
    AGENT = "agent"
    CONSULTANT = "consultant"


# === Account Status ===
class AccountStatus(str, Enum):
    """Account status states"""
    PENDING = "pending"  # Awaiting verification
    ACTIVE = "active"  # Fully active
    SUSPENDED = "suspended"  # Temporarily suspended
    DISABLED = "disabled"  # Permanently disabled
    DEACTIVATED = "deactivated"  # User-initiated deactivation


# === Verification Status ===
class VerificationStatus(str, Enum):
    """Vendor/Agent verification status"""
    PENDING = "pending"
    UNDER_REVIEW = "under_review"
    VERIFIED = "verified"
    REJECTED = "rejected"


# === Vendor Categories ===
class VendorCategory(str, Enum):
    """Types of vendors"""
    HOTEL = "hotel"
    RESTAURANT = "restaurant"
    TOUR_OPERATOR = "tour_operator"
    TRANSPORTATION = "transportation"
    EVENT_ORGANIZER = "event_organizer"
    ACTIVITY_PROVIDER = "activity_provider"
    CAR_RENTAL = "car_rental"
    TRAVEL_AGENCY = "travel_agency"
    LOCAL_GUIDE = "local_guide"
    ATTRACTION = "attraction"
    SPA_WELLNESS = "spa_wellness"
    SHOPPING = "shopping"
    ENTERTAINMENT = "entertainment"
    OTHER = "other"


# === Agent Types ===
class AgentType(str, Enum):
    """Types of travel agents"""
    INDEPENDENT = "independent"
    AGENCY = "agency"
    CORPORATE = "corporate"
    LUXURY = "luxury"
    BUDGET = "budget"
    ADVENTURE = "adventure"
    FAMILY = "family"
    HONEYMOON = "honeymoon"
    GROUP = "group"


# === Experience Status ===
class ExperienceStatus(str, Enum):
    """Status of an experience"""
    DRAFT = "draft"
    PENDING = "pending"
    CONFIRMED = "confirmed"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


# === Booking Status ===
class BookingStatus(str, Enum):
    """Status of a booking"""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    PAID = "paid"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    REFUNDED = "refunded"
    FAILED = "failed"
    NO_SHOW = "no_show"


# === Payment Status ===
class PaymentStatus(str, Enum):
    """Status of a payment"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"
    PARTIALLY_REFUNDED = "partially_refunded"
    DISPUTED = "disputed"
    CANCELLED = "cancelled"


# === Payment Methods ===
class PaymentMethod(str, Enum):
    """Available payment methods"""
    CARD = "card"
    BANK_TRANSFER = "bank_transfer"
    WALLET = "wallet"
    STRIPE = "stripe"
    PAYSTACK = "paystack"
    FLUTTERWAVE = "flutterwave"


# === Currency ===
class Currency(str, Enum):
    """Supported currencies"""
    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"
    NGN = "NGN"
    KES = "KES"
    GHS = "GHS"
    ZAR = "ZAR"


# === Notification Types ===
class NotificationType(str, Enum):
    """Types of notifications"""
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"
    IN_APP = "in_app"
    WEBHOOK = "webhook"


# === Notification Status ===
class NotificationStatus(str, Enum):
    """Status of a notification"""
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    FAILED = "failed"


# === Message Types ===
class MessageType(str, Enum):
    """Types of messages"""
    TEXT = "text"
    IMAGE = "image"
    FILE = "file"
    LOCATION = "location"
    SYSTEM = "system"


# === Review Rating ===
class ReviewRating(int, Enum):
    """Review rating values"""
    ONE = 1
    TWO = 2
    THREE = 3
    FOUR = 4
    FIVE = 5


# === Travel Interests ===
class TravelInterest(str, Enum):
    """Travel interest categories"""
    ADVENTURE = "adventure"
    BEACHES = "beaches"
    CULTURE = "culture"
    FOOD = "food"
    HISTORY = "history"
    NATURE = "nature"
    NIGHTLIFE = "nightlife"
    RELAXATION = "relaxation"
    SHOPPING = "shopping"
    SPORTS = "sports"
    WILDLIFE = "wildlife"
    PHOTOGRAPHY = "photography"
    ART = "art"
    MUSIC = "music"
    WELLNESS = "wellness"
    FAMILY = "family"
    ROMANTIC = "romantic"
    SOLO = "solo"
    BUDGET = "budget"
    LUXURY = "luxury"


# === Transportation Types ===
class TransportationType(str, Enum):
    """Types of transportation"""
    FLIGHT = "flight"
    TRAIN = "train"
    BUS = "bus"
    CAR = "car"
    TAXI = "taxi"
    UBER = "uber"
    BOLT = "bolt"
    FERRY = "ferry"
    WALKING = "walking"
    BICYCLE = "bicycle"


# === Accommodation Types ===
class AccommodationType(str, Enum):
    """Types of accommodations"""
    HOTEL = "hotel"
    HOSTEL = "hostel"
    RESORT = "resort"
    APARTMENT = "apartment"
    VILLA = "villa"
    GUESTHOUSE = "guesthouse"
    BNB = "bnb"
    BOUTIQUE = "boutique"
    MOTEL = "motel"
    CAMPING = "camping"


# === Event Types ===
class EventType(str, Enum):
    """Types of events"""
    CONCERT = "concert"
    FESTIVAL = "festival"
    CONFERENCE = "conference"
    EXHIBITION = "exhibition"
    SPORTS = "sports"
    THEATER = "theater"
    TOUR = "tour"
    WORKSHOP = "workshop"
    PARTY = "party"
    CULTURAL = "cultural"
    FOOD_FESTIVAL = "food_festival"
    RELIGIOUS = "religious"
    OTHER = "other"


# === Dining Types ===
class DiningType(str, Enum):
    """Types of dining establishments"""
    RESTAURANT = "restaurant"
    CAFE = "cafe"
    BAR = "bar"
    FAST_FOOD = "fast_food"
    FINE_DINING = "fine_dining"
    STREET_FOOD = "street_food"
    FOOD_COURT = "food_court"
    BAKERY = "bakery"
    FOOD_TRUCK = "food_truck"


# === Cuisine Types ===
class CuisineType(str, Enum):
    """Types of cuisines"""
    LOCAL = "local"
    AFRICAN = "african"
    AMERICAN = "american"
    ASIAN = "asian"
    CHINESE = "chinese"
    FRENCH = "french"
    INDIAN = "indian"
    ITALIAN = "italian"
    JAPANESE = "japanese"
    KOREAN = "korean"
    MEDITERRANEAN = "mediterranean"
    MEXICAN = "mexican"
    MIDDLE_EASTERN = "middle_eastern"
    THAI = "thai"
    VEGETARIAN = "vegetarian"
    VEGAN = "vegan"
    SEAFOOD = "seafood"
    BBQ = "bbq"
    FUSION = "fusion"
    OTHER = "other"


# === Activity Categories ===
class ActivityCategory(str, Enum):
    """Categories of activities"""
    OUTDOOR = "outdoor"
    INDOOR = "indoor"
    WATER = "water"
    ADVENTURE = "adventure"
    CULTURAL = "cultural"
    RELAXATION = "relaxation"
    SPORTS = "sports"
    ENTERTAINMENT = "entertainment"
    EDUCATIONAL = "educational"
    NIGHTLIFE = "nightlife"


# === Days of Week ===
class DayOfWeek(str, Enum):
    """Days of the week"""
    MONDAY = "monday"
    TUESDAY = "tuesday"
    WEDNESDAY = "wednesday"
    THURSDAY = "thursday"
    FRIDAY = "friday"
    SATURDAY = "saturday"
    SUNDAY = "sunday"


# === Content Types for Media ===
class MediaType(str, Enum):
    """Types of media content"""
    IMAGE = "image"
    VIDEO = "video"
    DOCUMENT = "document"
    AUDIO = "audio"


# === Story/Feed Types ===
class StoryType(str, Enum):
    """Types of stories/feeds"""
    EXPERIENCE = "experience"
    REVIEW = "review"
    TIP = "tip"
    PHOTO = "photo"
    VIDEO = "video"
    ANNOUNCEMENT = "announcement"


# === Commission Types ===
class CommissionType(str, Enum):
    """Types of commission"""
    PERCENTAGE = "percentage"
    FIXED = "fixed"
    TIERED = "tiered"


# === Subscription Plans ===
class SubscriptionPlan(str, Enum):
    """Subscription plan types"""
    FREE = "free"
    BASIC = "basic"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"
    VIP = "vip"


# === Geographic Regions ===
SUPPORTED_COUNTRIES: List[str] = [
    "Nigeria",
    "Ghana",
    "Kenya",
    "South Africa",
    "Egypt",
    "Morocco",
    "Tanzania",
    "Rwanda",
    "United Kingdom",
    "United States",
    "Canada",
    "France",
    "Germany",
    "UAE",
    "Saudi Arabia",
]

# Nigerian States
NIGERIAN_STATES: List[str] = [
    "Abia", "Adamawa", "Akwa Ibom", "Anambra", "Bauchi", "Bayelsa",
    "Benue", "Borno", "Cross River", "Delta", "Ebonyi", "Edo",
    "Ekiti", "Enugu", "FCT", "Gombe", "Imo", "Jigawa",
    "Kaduna", "Kano", "Katsina", "Kebbi", "Kogi", "Kwara",
    "Lagos", "Nasarawa", "Niger", "Ogun", "Ondo", "Osun",
    "Oyo", "Plateau", "Rivers", "Sokoto", "Taraba", "Yobe", "Zamfara"
]


# === Default Commission Rates ===
DEFAULT_COMMISSION_RATES: Dict[str, float] = {
    "hotel": 0.15,  # 15%
    "restaurant": 0.10,  # 10%
    "activity": 0.12,  # 12%
    "event": 0.08,  # 8%
    "transportation": 0.05,  # 5%
    "tour": 0.15,  # 15%
}


# === Cancellation Policies ===
class CancellationPolicy(str, Enum):
    """Cancellation policy types"""
    FLEXIBLE = "flexible"  # Full refund up to 24h before
    MODERATE = "moderate"  # Full refund up to 5 days before
    STRICT = "strict"  # 50% refund up to 7 days before
    NON_REFUNDABLE = "non_refundable"  # No refund


# === Age Groups ===
class AgeGroup(str, Enum):
    """Age group categories"""
    INFANT = "infant"  # 0-2
    CHILD = "child"  # 3-12
    TEEN = "teen"  # 13-17
    ADULT = "adult"  # 18-64
    SENIOR = "senior"  # 65+


# === API Rate Limits ===
API_RATE_LIMITS: Dict[str, int] = {
    "default": 60,  # 60 requests per minute
    "auth": 10,  # 10 requests per minute
    "search": 30,  # 30 requests per minute
    "booking": 20,  # 20 requests per minute
    "payment": 10,  # 10 requests per minute
}


# === File Size Limits ===
FILE_SIZE_LIMITS: Dict[str, int] = {
    "image": 5 * 1024 * 1024,  # 5MB
    "video": 100 * 1024 * 1024,  # 100MB
    "document": 10 * 1024 * 1024,  # 10MB
    "audio": 20 * 1024 * 1024,  # 20MB
}


# === Cache TTL (seconds) ===
CACHE_TTL: Dict[str, int] = {
    "default": 3600,  # 1 hour
    "user_session": 86400,  # 24 hours
    "search_results": 300,  # 5 minutes
    "weather": 1800,  # 30 minutes
    "exchange_rates": 3600,  # 1 hour
    "static_data": 86400,  # 24 hours
}

