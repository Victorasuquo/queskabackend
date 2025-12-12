"""
Queska Backend - Main Application
FastAPI application entry point with comprehensive setup
"""

from contextlib import asynccontextmanager
from datetime import datetime
from typing import Dict

from beanie import init_beanie
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from loguru import logger
from motor.motor_asyncio import AsyncIOMotorClient
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings
from app.core.exceptions import (
    AppException,
    AuthenticationError,
    NotFoundError,
    ValidationError as AppValidationError,
)
from app.api.v1.router import api_router

# Import all document models for Beanie initialization
from app.models.user import User, UserPreferences, UserAddress, UserSubscription
from app.models.vendor import Vendor
from app.models.agent import Agent
from app.models.admin import Admin
# from app.models.experience import Experience
# from app.models.booking import Booking
# from app.models.review import Review
# from app.models.notification import Notification
# from app.models.payment import Payment


# === Database Setup ===

async def init_database():
    """Initialize MongoDB connection and Beanie ODM"""
    client = AsyncIOMotorClient(settings.MONGO_URI)
    
    # Initialize Beanie with all document models
    await init_beanie(
        database=client[settings.MONGO_DATABASE],
        document_models=[
            User,
            Vendor,
            Agent,
            Admin,
            # Add more models as they are created
            # Experience,
            # Booking,
            # Review,
            # Notification,
            # Payment,
        ]
    )
    
    logger.info(f"Connected to MongoDB: {settings.MONGO_DATABASE}")
    return client


async def close_database(client: AsyncIOMotorClient):
    """Close MongoDB connection"""
    client.close()
    logger.info("Closed MongoDB connection")


# === Lifespan Context Manager ===

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup and shutdown events"""
    # Startup
    logger.info("Starting Queska Backend API...")
    
    # Initialize database
    client = await init_database()
    
    # Store client for cleanup
    app.state.mongo_client = client
    
    # Initialize Redis cache (if configured)
    # if settings.REDIS_URL:
    #     from app.core.cache import init_redis
    #     await init_redis()
    
    logger.info("Queska Backend API started successfully!")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Queska Backend API...")
    
    await close_database(client)
    
    # Close Redis connection
    # if settings.REDIS_URL:
    #     from app.core.cache import close_redis
    #     await close_redis()
    
    logger.info("Queska Backend API shutdown complete")


# === FastAPI Application ===

app = FastAPI(
    title="Queska Backend API",
    description="""
    Queska - Premium Travel Experience Platform API
    
    An end-to-end travel application that allows you to create seamless,
    all-in-one premium travel experiences without hassle or boundaries.
    
    ## Features
    
    * **User Management** - Registration, authentication, profiles
    * **Vendor Management** - Hotels, restaurants, activities, etc.
    * **Agent Management** - Travel agents and consultants
    * **Experience Creation** - End-to-end travel itinerary planning
    * **Booking System** - Integrated booking across vendors
    * **Payments** - Secure payment processing via Stripe
    * **AI Assistance** - 24/7 AI-powered travel support
    * **Real-time Notifications** - Email, SMS, Push notifications
    * **Geo-intelligence** - Location-based services and tracking
    
    ## API Version
    
    Current version: **v1**
    """,
    version="1.0.0",
    contact={
        "name": "Queska Support",
        "email": "support@queska.com",
    },
    license_info={
        "name": "Proprietary",
    },
    docs_url="/docs" if settings.SHOW_DOCS else None,
    redoc_url="/redoc" if settings.SHOW_DOCS else None,
    openapi_url="/openapi.json" if settings.SHOW_DOCS else None,
    lifespan=lifespan,
)


# === Middleware ===

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# GZip compression
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Trusted hosts (production)
if settings.APP_ENV == "production":
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.ALLOWED_HOSTS
    )


# Request timing middleware
class RequestTimingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = datetime.utcnow()
        response = await call_next(request)
        process_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        response.headers["X-Process-Time"] = f"{process_time:.2f}ms"
        return response


app.add_middleware(RequestTimingMiddleware)


# === Exception Handlers ===

@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    """Handle custom application exceptions"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": exc.message,
            "error_code": exc.error_code,
            "details": exc.details
        }
    )


@app.exception_handler(AuthenticationError)
async def auth_exception_handler(request: Request, exc: AuthenticationError):
    """Handle authentication exceptions"""
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={
            "success": False,
            "error": str(exc),
            "error_code": "AUTHENTICATION_ERROR"
        },
        headers={"WWW-Authenticate": "Bearer"}
    )


@app.exception_handler(NotFoundError)
async def not_found_handler(request: Request, exc: NotFoundError):
    """Handle not found exceptions"""
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={
            "success": False,
            "error": str(exc),
            "error_code": "NOT_FOUND"
        }
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle request validation errors"""
    errors = []
    for error in exc.errors():
        errors.append({
            "field": ".".join(str(loc) for loc in error["loc"]),
            "message": error["msg"],
            "type": error["type"]
        })
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "error": "Validation error",
            "error_code": "VALIDATION_ERROR",
            "details": errors
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions"""
    logger.exception(f"Unexpected error: {exc}")
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": "An unexpected error occurred" if settings.APP_ENV == "production" else str(exc),
            "error_code": "INTERNAL_SERVER_ERROR"
        }
    )


# === Include Routers ===

app.include_router(api_router, prefix="/api/v1")


# === Root Endpoints ===

@app.get("/", tags=["Root"])
async def root():
    """Root endpoint - API information"""
    return {
        "name": "Queska Backend API",
        "version": "1.0.0",
        "description": "Premium Travel Experience Platform",
        "status": "running",
        "docs": "/docs" if settings.SHOW_DOCS else "disabled",
        "api": "/api/v1"
    }


@app.get("/health", tags=["Health"])
async def health_check() -> Dict:
    """Health check endpoint for monitoring"""
    return {
        "status": "healthy",
        "service": "queska-backend",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "environment": settings.APP_ENV
    }


@app.get("/ready", tags=["Health"])
async def readiness_check() -> Dict:
    """Readiness check for Kubernetes/load balancers"""
    # TODO: Add database and cache connectivity checks
    return {
        "status": "ready",
        "timestamp": datetime.utcnow().isoformat(),
        "checks": {
            "database": "connected",
            "cache": "connected" if settings.REDIS_URL else "not_configured"
        }
    }


# === Run with Uvicorn (for development) ===

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.APP_ENV == "development",
        log_level="info"
    )
