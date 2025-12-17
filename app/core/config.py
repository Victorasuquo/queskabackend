"""
Queska Backend - Configuration Management
Centralized settings using Pydantic Settings
"""

from functools import lru_cache
from typing import Any, List, Optional, Union

from pydantic import AnyHttpUrl, EmailStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )
    
    # === Application Settings ===
    APP_NAME: str = "Queska"
    APP_VERSION: str = "1.0.0"
    APP_DESCRIPTION: str = "AI-Powered All-in-One Travel Experience Platform"
    DEBUG: bool = False
    ENVIRONMENT: str = "production"  # development, staging, production
    
    # === API Settings ===
    API_V1_PREFIX: str = "/api/v1"
    PROJECT_NAME: str = "Queska API"
    
    # === Server Settings ===
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    WORKERS: int = 4
    RELOAD: bool = False
    
    # === Security Settings ===
    SECRET_KEY: str
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    PASSWORD_RESET_TOKEN_EXPIRE_HOURS: int = 24
    VERIFICATION_TOKEN_EXPIRE_HOURS: int = 48
    
    # === CORS Settings ===
    BACKEND_CORS_ORIGINS: List[str] = ["*"]
    
    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)
    
    # === MongoDB Settings ===
    MONGODB_URI: str
    MONGODB_DATABASE: str = "queska"
    MONGODB_MAX_POOL_SIZE: int = 100
    MONGODB_MIN_POOL_SIZE: int = 10
    
    # === Redis Settings ===
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_PASSWORD: Optional[str] = None
    REDIS_DB: int = 0
    CACHE_TTL: int = 3600  # 1 hour default cache TTL
    
    # === Celery Settings ===
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"
    
    # === Stripe Payment Settings ===
    STRIPE_SECRET_KEY: str
    STRIPE_PUBLISHABLE_KEY: str
    STRIPE_WEBHOOK_SECRET: str
    STRIPE_CURRENCY: str = "usd"
    
    # === Mapbox Settings ===
    MAPBOX_ACCESS_TOKEN: str
    MAPBOX_GEOCODING_API: str = "https://api.mapbox.com/geocoding/v5"
    MAPBOX_DIRECTIONS_API: str = "https://api.mapbox.com/directions/v5"
    
    # === Google Maps (Fallback) ===
    GOOGLE_MAPS_API_KEY: Optional[str] = None
    
    # === Google OAuth Settings ===
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    GOOGLE_REDIRECT_URI: str = "https://queska.com/auth/google/callback"
    
    # === Travel API Settings ===
    # Booking.com
    BOOKING_COM_API_KEY: Optional[str] = None
    BOOKING_COM_API_SECRET: Optional[str] = None
    
    # RapidAPI Hotels (FREE - https://rapidapi.com/tipsters/api/booking-com)
    # 500 requests/month free tier
    RAPIDAPI_KEY: Optional[str] = None
    
    # Expedia Rapid API & XAP API
    # Get credentials: https://partner.expediagroup.com/en-us/solutions/build-your-travel-experience/rapid-api
    EXPEDIA_API_KEY: Optional[str] = None
    EXPEDIA_API_SECRET: Optional[str] = None
    EXPEDIA_USE_PRODUCTION: bool = False  # Set to True for production API
    
    # Amadeus
    AMADEUS_API_KEY: Optional[str] = None
    AMADEUS_API_SECRET: Optional[str] = None
    AMADEUS_ENVIRONMENT: str = "test"  # test or production
    
    # === AI Settings ===
    AI_PROVIDER: str = "gemini"  # gemini, perplexity, openai
    GEMINI_API_KEY: Optional[str] = None
    PERPLEXITY_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None
    AI_MODEL_NAME: str = "gemini-pro"
    AI_MAX_TOKENS: int = 4096
    AI_TEMPERATURE: float = 0.7
    
    # === Search Engine Settings ===
    SEARCH_ENGINE: str = "meilisearch"  # meilisearch, elasticsearch
    ELASTICSEARCH_URL: str = "http://localhost:9200"
    MEILISEARCH_URL: str = "http://localhost:7700"
    MEILISEARCH_API_KEY: Optional[str] = None
    
    # === Vector Database Settings ===
    VECTOR_DB: str = "qdrant"  # qdrant, chromadb, weaviate
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_API_KEY: Optional[str] = None
    CHROMADB_PATH: str = "./data/chromadb"
    WEAVIATE_URL: str = "http://localhost:8080"
    
    # === Media Storage Settings ===
    MEDIA_STORAGE: str = "cloudinary"  # cloudinary, minio, s3
    CLOUDINARY_CLOUD_NAME: Optional[str] = None
    CLOUDINARY_API_KEY: Optional[str] = None
    CLOUDINARY_API_SECRET: Optional[str] = None
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: Optional[str] = None
    MINIO_SECRET_KEY: Optional[str] = None
    MINIO_BUCKET: str = "queska-media"
    MINIO_SECURE: bool = False
    AWS_S3_BUCKET: Optional[str] = None
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_REGION: str = "us-east-1"
    
    # === Email Settings (SendGrid) ===
    # Get your API key from: https://app.sendgrid.com/settings/api_keys
    SENDGRID_API_KEY: Optional[str] = None
    
    # Sender Configuration
    EMAIL_FROM_NAME: str = "Queska"
    EMAIL_FROM_ADDRESS: str = "noreply@queska.com"
    EMAIL_REPLY_TO: str = "support@queska.com"
    
    # SendGrid Dynamic Template IDs (optional - create in SendGrid dashboard)
    SENDGRID_TEMPLATE_WELCOME: Optional[str] = None
    SENDGRID_TEMPLATE_PASSWORD_RESET: Optional[str] = None
    SENDGRID_TEMPLATE_EMAIL_VERIFICATION: Optional[str] = None
    SENDGRID_TEMPLATE_BOOKING_CONFIRMATION: Optional[str] = None
    SENDGRID_TEMPLATE_EXPERIENCE_SHARED: Optional[str] = None
    SENDGRID_TEMPLATE_PAYMENT_RECEIPT: Optional[str] = None
    SENDGRID_TEMPLATE_NOTIFICATION: Optional[str] = None
    
    # SMTP Fallback Settings (optional backup)
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_TLS: bool = True
    
    # === SMS Settings ===
    SMS_PROVIDER: str = "twilio"  # twilio, termii
    TWILIO_ACCOUNT_SID: Optional[str] = None
    TWILIO_AUTH_TOKEN: Optional[str] = None
    TWILIO_PHONE_NUMBER: Optional[str] = None
    TWILIO_MESSAGING_SERVICE_SID: Optional[str] = None  # Optional for high volume
    TERMII_API_KEY: Optional[str] = None
    TERMII_SENDER_ID: Optional[str] = None
    
    # === Push Notification Settings ===
    FIREBASE_CREDENTIALS_PATH: Optional[str] = None
    FIREBASE_PROJECT_ID: Optional[str] = None
    
    # === Notification Settings ===
    NOTIFICATION_BATCH_SIZE: int = 100
    NOTIFICATION_RETRY_ATTEMPTS: int = 3
    NOTIFICATION_RETRY_DELAY: int = 60  # seconds
    
    # === Weather API Settings ===
    OPENWEATHER_API_KEY: Optional[str] = None
    
    # === Transportation API Settings ===
    UBER_CLIENT_ID: Optional[str] = None
    UBER_CLIENT_SECRET: Optional[str] = None
    BOLT_API_KEY: Optional[str] = None
    
    # === Frontend URL ===
    FRONTEND_URL: str = "https://queska.com"  # For email verification/reset links
    
    # === Rate Limiting ===
    RATE_LIMIT_PER_MINUTE: int = 60
    RATE_LIMIT_PER_HOUR: int = 1000
    
    # === Pagination ===
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100
    
    # === File Upload Settings ===
    MAX_UPLOAD_SIZE_MB: int = 10
    ALLOWED_IMAGE_TYPES: List[str] = ["image/jpeg", "image/png", "image/gif", "image/webp"]
    ALLOWED_DOCUMENT_TYPES: List[str] = ["application/pdf", "application/msword"]
    
    # === Logging ===
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"  # json, text
    SENTRY_DSN: Optional[str] = None
    
    # === Feature Flags ===
    ENABLE_AI_AGENTS: bool = True
    ENABLE_WEB_CRAWLER: bool = True
    ENABLE_REAL_TIME_TRACKING: bool = True
    ENABLE_PUSH_NOTIFICATIONS: bool = True
    
    # === Documentation ===
    SHOW_DOCS: bool = True
    
    # === Allowed Hosts (Production) ===
    ALLOWED_HOSTS: List[str] = ["*"]
    
    @property
    def mongodb_connection_string(self) -> str:
        """Get MongoDB connection string with database"""
        return self.MONGODB_URI
    
    @property
    def MONGO_URI(self) -> str:
        """Alias for MONGODB_URI"""
        return self.MONGODB_URI
    
    @property
    def MONGO_DATABASE(self) -> str:
        """Alias for MONGODB_DATABASE"""
        return self.MONGODB_DATABASE
    
    @property
    def CORS_ORIGINS(self) -> List[str]:
        """Alias for BACKEND_CORS_ORIGINS"""
        return self.BACKEND_CORS_ORIGINS
    
    @property
    def APP_ENV(self) -> str:
        """Alias for ENVIRONMENT"""
        return self.ENVIRONMENT
    
    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT == "development"
    
    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


# Global settings instance
settings = get_settings()

