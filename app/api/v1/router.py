"""
Queska Backend - API V1 Router
Main router for API version 1 endpoints
"""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    users,
    vendors,
    agents,
    dashboards,
    # admins,  # TODO: Implement
    # experiences,  # TODO: Implement
    # bookings,  # TODO: Implement
    # reviews,  # TODO: Implement
    # payments,  # TODO: Implement
    # notifications,  # TODO: Implement
    # search,  # TODO: Implement
    # chat,  # TODO: Implement
    # ai,  # TODO: Implement
)


api_router = APIRouter()


# === User Routes ===
api_router.include_router(
    users.router,
    prefix="/users",
    tags=["Users"]
)


# === Vendor Routes ===
api_router.include_router(
    vendors.router,
    prefix="/vendors",
    tags=["Vendors"]
)


# === Agent Routes ===
api_router.include_router(
    agents.router,
    prefix="/agents",
    tags=["Agents"]
)


# === Dashboard Routes ===
api_router.include_router(
    dashboards.router,
    prefix="/dashboards",
    tags=["Dashboards"]
)


# === Health Check ===
@api_router.get("/health", tags=["Health"])
async def health_check():
    """API health check endpoint."""
    return {
        "status": "healthy",
        "service": "queska-backend",
        "version": "1.0.0"
    }


# TODO: Add more routers as they are implemented
# api_router.include_router(
#     admins.router,
#     prefix="/admins",
#     tags=["Admins"]
# )

# api_router.include_router(
#     experiences.router,
#     prefix="/experiences",
#     tags=["Experiences"]
# )

# api_router.include_router(
#     bookings.router,
#     prefix="/bookings",
#     tags=["Bookings"]
# )

# api_router.include_router(
#     reviews.router,
#     prefix="/reviews",
#     tags=["Reviews"]
# )

# api_router.include_router(
#     payments.router,
#     prefix="/payments",
#     tags=["Payments"]
# )

# api_router.include_router(
#     notifications.router,
#     prefix="/notifications",
#     tags=["Notifications"]
# )

# api_router.include_router(
#     search.router,
#     prefix="/search",
#     tags=["Search"]
# )

# api_router.include_router(
#     chat.router,
#     prefix="/chat",
#     tags=["Chat"]
# )

# api_router.include_router(
#     ai.router,
#     prefix="/ai",
#     tags=["AI"]
# )
