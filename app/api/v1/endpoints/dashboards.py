"""
Queska Backend - Dashboard API Endpoints
Comprehensive dashboard endpoints for all user types
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from loguru import logger

from app.api.deps import (
    get_current_user,
    get_current_active_user,
    get_current_vendor,
    get_current_active_vendor,
    get_current_agent,
    get_current_active_agent,
    get_current_admin,
)
from app.models.user import User
from app.models.vendor import Vendor
from app.models.agent import Agent
from app.models.admin import Admin
from app.services.user_service import user_service
from app.services.vendor_service import vendor_service
from app.services.agent_service import agent_service
from app.repositories.user_repository import user_repository
from app.repositories.vendor_repository import vendor_repository
from app.repositories.agent_repository import agent_repository


router = APIRouter()


# ==========================================
# USER DASHBOARD
# ==========================================

@router.get(
    "/user",
    response_model=Dict[str, Any],
    summary="User Dashboard",
    description="Get comprehensive user dashboard data"
)
async def get_user_dashboard(user: User = Depends(get_current_active_user)):
    """
    Get the complete user dashboard including:
    - Profile statistics
    - Upcoming experiences
    - Recent bookings
    - Notifications
    - Recommendations
    - Agent info
    """
    return await user_service.get_dashboard(str(user.id))


@router.get(
    "/user/stats",
    response_model=Dict[str, Any],
    summary="User Stats",
    description="Get user statistics summary"
)
async def get_user_dashboard_stats(user: User = Depends(get_current_active_user)):
    """Get detailed user statistics."""
    return await user_repository.get_dashboard_stats(str(user.id))


@router.get(
    "/user/overview",
    response_model=Dict[str, Any],
    summary="User Overview",
    description="Quick overview for user dashboard"
)
async def get_user_overview(user: User = Depends(get_current_active_user)):
    """Get quick overview data for dashboard cards."""
    stats = user.stats
    
    return {
        "profile": {
            "name": user.full_name,
            "email": user.email,
            "profile_photo": user.profile_photo,
            "profile_completion": user.profile_completion_percentage,
            "is_verified": user.is_email_verified,
            "member_since": user.created_at.isoformat(),
        },
        "quick_stats": {
            "experiences": stats.total_experiences if stats else 0,
            "upcoming": stats.upcoming_experiences if stats else 0,
            "bookings": stats.total_bookings if stats else 0,
            "reviews": stats.total_reviews if stats else 0,
            "favorites": len(user.favorite_vendors) + len(user.favorite_destinations),
            "followers": user.followers_count,
            "following": user.following_count,
        },
        "spending": {
            "total_spent": stats.total_spent if stats else 0,
            "total_saved": stats.total_saved if stats else 0,
            "currency": "NGN",
        },
        "travel_stats": {
            "countries_visited": stats.countries_visited if stats else 0,
            "cities_visited": stats.cities_visited if stats else 0,
        },
        "subscription": {
            "plan": user.subscription.plan.value if user.subscription else "free",
            "is_active": user.subscription.is_active if user.subscription else True,
            "expires_at": user.subscription.expires_at.isoformat() if user.subscription and user.subscription.expires_at else None,
        },
        "agent": {
            "has_agent": user.assigned_agent_id is not None,
            "agent_id": str(user.assigned_agent_id) if user.assigned_agent_id else None,
        }
    }


@router.get(
    "/user/experiences",
    response_model=Dict[str, Any],
    summary="User Experiences",
    description="Get user's experiences for dashboard"
)
async def get_user_experiences_dashboard(
    status: Optional[str] = None,
    limit: int = Query(10, ge=1, le=50),
    user: User = Depends(get_current_active_user)
):
    """Get user's experiences filtered by status."""
    # TODO: Implement when Experience model is complete
    return {
        "experiences": [],
        "stats": {
            "total": 0,
            "upcoming": 0,
            "completed": 0,
            "cancelled": 0,
        }
    }


@router.get(
    "/user/bookings",
    response_model=Dict[str, Any],
    summary="User Bookings",
    description="Get user's recent bookings for dashboard"
)
async def get_user_bookings_dashboard(
    status: Optional[str] = None,
    booking_type: Optional[str] = None,
    limit: int = Query(10, ge=1, le=50),
    user: User = Depends(get_current_active_user)
):
    """Get user's recent bookings."""
    # TODO: Implement when Booking model is complete
    return {
        "bookings": [],
        "stats": {
            "total": 0,
            "pending": 0,
            "confirmed": 0,
            "completed": 0,
        }
    }


@router.get(
    "/user/recommendations",
    response_model=Dict[str, Any],
    summary="User Recommendations",
    description="Get personalized recommendations"
)
async def get_user_recommendations(
    user: User = Depends(get_current_active_user)
):
    """Get AI-powered recommendations based on user preferences."""
    # TODO: Implement AI recommendations
    preferences = user.preferences
    
    return {
        "destinations": [],  # AI-recommended destinations
        "experiences": [],   # Recommended experiences
        "events": [],       # Upcoming events based on interests
        "vendors": [],      # Recommended vendors
        "based_on": {
            "interests": preferences.interests if preferences else [],
            "travel_style": preferences.travel_style if preferences else None,
            "favorite_destinations": user.favorite_destinations,
        }
    }


# ==========================================
# VENDOR DASHBOARD
# ==========================================

@router.get(
    "/vendor",
    response_model=Dict[str, Any],
    summary="Vendor Dashboard",
    description="Get comprehensive vendor dashboard data"
)
async def get_vendor_dashboard(vendor: Vendor = Depends(get_current_active_vendor)):
    """
    Get the complete vendor dashboard including:
    - Business statistics
    - Booking analytics
    - Revenue data
    - Reviews summary
    - Recent activity
    """
    analytics = vendor.analytics
    rating = vendor.rating
    
    return {
        "profile": {
            "business_name": vendor.business_name,
            "category": vendor.category.value if vendor.category else None,
            "logo": vendor.media.logo if vendor.media else None,
            "is_verified": vendor.is_verified,
            "is_featured": vendor.is_featured,
            "status": vendor.status.value if vendor.status else None,
        },
        "stats": {
            "total_bookings": analytics.total_bookings if analytics else 0,
            "total_revenue": analytics.total_revenue if analytics else 0,
            "total_views": analytics.total_views if analytics else 0,
            "total_favorites": analytics.total_favorites if analytics else 0,
            "conversion_rate": analytics.conversion_rate if analytics else 0,
            "average_booking_value": analytics.average_booking_value if analytics else 0,
        },
        "rating": {
            "average": rating.average if rating else 0,
            "count": rating.count if rating else 0,
            "breakdown": rating.breakdown if rating else {},
        },
        "subscription": {
            "plan": vendor.subscription.plan.value if vendor.subscription else "free",
            "is_active": vendor.subscription.is_active if vendor.subscription else True,
        },
        "verification": {
            "status": vendor.verification.status.value if vendor.verification else "pending",
            "submitted_at": vendor.verification.submitted_at.isoformat() if vendor.verification and vendor.verification.submitted_at else None,
        },
        "payout": {
            "enabled": vendor.payout_enabled,
            "stripe_connected": vendor.stripe_connected,
            "bank_accounts": len(vendor.bank_accounts),
        }
    }


@router.get(
    "/vendor/stats",
    response_model=Dict[str, Any],
    summary="Vendor Stats",
    description="Get detailed vendor statistics"
)
async def get_vendor_dashboard_stats(vendor: Vendor = Depends(get_current_active_vendor)):
    """Get detailed vendor statistics."""
    analytics = vendor.analytics
    
    return {
        "overview": {
            "total_bookings": analytics.total_bookings if analytics else 0,
            "total_revenue": analytics.total_revenue if analytics else 0,
            "total_reviews": analytics.total_reviews if analytics else 0,
            "total_views": analytics.total_views if analytics else 0,
            "total_favorites": analytics.total_favorites if analytics else 0,
        },
        "performance": {
            "conversion_rate": analytics.conversion_rate if analytics else 0,
            "average_booking_value": analytics.average_booking_value if analytics else 0,
            "last_booking_at": analytics.last_booking_at.isoformat() if analytics and analytics.last_booking_at else None,
        },
        "monthly_stats": analytics.monthly_stats if analytics else {},
        "rating": {
            "average": vendor.rating.average if vendor.rating else 0,
            "count": vendor.rating.count if vendor.rating else 0,
            "breakdown": vendor.rating.breakdown if vendor.rating else {},
        }
    }


@router.get(
    "/vendor/bookings",
    response_model=Dict[str, Any],
    summary="Vendor Bookings",
    description="Get vendor's bookings for dashboard"
)
async def get_vendor_bookings_dashboard(
    status: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    limit: int = Query(20, ge=1, le=100),
    vendor: Vendor = Depends(get_current_active_vendor)
):
    """Get vendor's bookings."""
    # TODO: Implement when Booking model is complete
    return {
        "bookings": [],
        "stats": {
            "today": 0,
            "this_week": 0,
            "this_month": 0,
            "pending": 0,
        }
    }


@router.get(
    "/vendor/revenue",
    response_model=Dict[str, Any],
    summary="Vendor Revenue",
    description="Get vendor's revenue analytics"
)
async def get_vendor_revenue_dashboard(
    period: str = Query("month", enum=["week", "month", "quarter", "year"]),
    vendor: Vendor = Depends(get_current_active_vendor)
):
    """Get vendor's revenue analytics."""
    analytics = vendor.analytics
    
    return {
        "total_revenue": analytics.total_revenue if analytics else 0,
        "currency": vendor.currency,
        "period": period,
        "breakdown": [],  # TODO: Implement revenue breakdown by period
        "trends": [],    # TODO: Implement revenue trends
    }


@router.get(
    "/vendor/reviews",
    response_model=Dict[str, Any],
    summary="Vendor Reviews",
    description="Get vendor's reviews summary"
)
async def get_vendor_reviews_dashboard(
    limit: int = Query(10, ge=1, le=50),
    vendor: Vendor = Depends(get_current_active_vendor)
):
    """Get vendor's reviews summary."""
    rating = vendor.rating
    
    return {
        "rating": {
            "average": rating.average if rating else 0,
            "count": rating.count if rating else 0,
            "breakdown": rating.breakdown if rating else {},
        },
        "recent_reviews": [],  # TODO: Get from Review model
        "response_rate": 0,    # TODO: Calculate response rate
    }


# ==========================================
# AGENT DASHBOARD
# ==========================================

@router.get(
    "/agent",
    response_model=Dict[str, Any],
    summary="Agent Dashboard",
    description="Get comprehensive agent dashboard data"
)
async def get_agent_dashboard(agent: Agent = Depends(get_current_active_agent)):
    """
    Get the complete agent dashboard including:
    - Client statistics
    - Booking analytics
    - Commission data
    - Performance metrics
    """
    analytics = agent.analytics
    rating = agent.rating
    
    return {
        "profile": {
            "name": agent.full_name,
            "agent_type": agent.agent_type.value if agent.agent_type else None,
            "profile_photo": agent.media.profile_photo if agent.media else None,
            "is_verified": agent.is_verified,
            "is_featured": agent.is_featured,
            "is_available": agent.is_available,
            "status": agent.status.value if agent.status else None,
        },
        "clients": {
            "total": agent.client_count,
            "max": agent.max_clients,
            "available_slots": agent.max_clients - agent.client_count,
            "can_accept": agent.can_accept_clients,
        },
        "stats": {
            "total_bookings": analytics.total_bookings if analytics else 0,
            "total_clients": analytics.total_clients if analytics else 0,
            "total_revenue": analytics.total_revenue if analytics else 0,
            "total_commission": analytics.total_commission_earned if analytics else 0,
            "conversion_rate": analytics.conversion_rate if analytics else 0,
            "average_booking_value": analytics.average_booking_value if analytics else 0,
        },
        "rating": {
            "average": rating.average if rating else 0,
            "count": rating.count if rating else 0,
            "breakdown": rating.breakdown if rating else {},
        },
        "referrals": {
            "code": agent.referral_code,
            "count": agent.referral_count,
            "earnings": agent.referral_earnings,
        },
        "verification": {
            "status": agent.verification.status.value if agent.verification else "pending",
        },
        "payout": {
            "enabled": agent.payout_enabled,
            "stripe_connected": agent.stripe_connected,
        }
    }


@router.get(
    "/agent/stats",
    response_model=Dict[str, Any],
    summary="Agent Stats",
    description="Get detailed agent statistics"
)
async def get_agent_dashboard_stats(agent: Agent = Depends(get_current_active_agent)):
    """Get detailed agent statistics."""
    analytics = agent.analytics
    
    return {
        "overview": {
            "total_bookings": analytics.total_bookings if analytics else 0,
            "total_clients": analytics.total_clients if analytics else 0,
            "total_revenue": analytics.total_revenue if analytics else 0,
            "total_commission": analytics.total_commission_earned if analytics else 0,
            "total_reviews": analytics.total_reviews if analytics else 0,
        },
        "performance": {
            "conversion_rate": analytics.conversion_rate if analytics else 0,
            "average_booking_value": analytics.average_booking_value if analytics else 0,
            "last_booking_at": analytics.last_booking_at.isoformat() if analytics and analytics.last_booking_at else None,
        },
        "monthly_stats": analytics.monthly_stats if analytics else {},
        "top_destinations": analytics.top_destinations if analytics else [],
    }


@router.get(
    "/agent/clients",
    response_model=Dict[str, Any],
    summary="Agent Clients",
    description="Get agent's client list for dashboard"
)
async def get_agent_clients_dashboard(
    limit: int = Query(20, ge=1, le=100),
    agent: Agent = Depends(get_current_active_agent)
):
    """Get agent's client list with details."""
    client_ids = await agent_repository.get_agent_clients(str(agent.id))
    
    # Get client details
    clients = []
    for client_id in client_ids[:limit]:
        user = await user_repository.get_by_id(str(client_id))
        if user:
            clients.append({
                "id": str(user.id),
                "name": user.full_name,
                "email": user.email,
                "profile_photo": user.profile_photo,
                "member_since": user.created_at.isoformat(),
            })
    
    return {
        "clients": clients,
        "total": len(client_ids),
        "max_clients": agent.max_clients,
        "available_slots": agent.max_clients - len(client_ids),
    }


@router.get(
    "/agent/commissions",
    response_model=Dict[str, Any],
    summary="Agent Commissions",
    description="Get agent's commission data"
)
async def get_agent_commissions_dashboard(
    period: str = Query("month", enum=["week", "month", "quarter", "year"]),
    agent: Agent = Depends(get_current_active_agent)
):
    """Get agent's commission analytics."""
    analytics = agent.analytics
    
    return {
        "total_earned": analytics.total_commission_earned if analytics else 0,
        "currency": "NGN",
        "period": period,
        "commission_rate": agent.commission.rate if agent.commission else 10,
        "breakdown": [],  # TODO: Implement commission breakdown
        "pending_payout": 0,  # TODO: Calculate pending payouts
    }


# ==========================================
# ADMIN DASHBOARD
# ==========================================

@router.get(
    "/admin",
    response_model=Dict[str, Any],
    summary="Admin Dashboard",
    description="Get comprehensive admin dashboard data"
)
async def get_admin_dashboard(admin: Admin = Depends(get_current_admin)):
    """
    Get the complete admin dashboard including:
    - Platform statistics
    - User metrics
    - Revenue data
    - Recent activity
    """
    # Get all stats
    user_stats = await user_repository.get_stats()
    vendor_stats = await vendor_repository.get_stats()
    agent_stats = await agent_repository.get_stats()
    
    return {
        "users": {
            "total": user_stats.get("total", 0),
            "active": user_stats.get("active", 0),
            "verified": user_stats.get("verified", 0),
            "premium": user_stats.get("premium", 0),
            "pending": user_stats.get("pending", 0),
            "with_agent": user_stats.get("with_agent", 0),
        },
        "vendors": {
            "total": vendor_stats.get("total", 0),
            "active": vendor_stats.get("active", 0),
            "verified": vendor_stats.get("verified", 0),
            "featured": vendor_stats.get("featured", 0),
            "pending": vendor_stats.get("pending", 0),
        },
        "agents": {
            "total": agent_stats.get("total", 0),
            "active": agent_stats.get("active", 0),
            "verified": agent_stats.get("verified", 0),
            "featured": agent_stats.get("featured", 0),
            "available": agent_stats.get("available", 0),
            "total_clients": agent_stats.get("total_clients", 0),
        },
        "platform": {
            "total_bookings": 0,  # TODO: Get from booking stats
            "total_revenue": 0,   # TODO: Get from payment stats
            "total_experiences": 0,
            "total_reviews": 0,
        }
    }


@router.get(
    "/admin/users/overview",
    response_model=Dict[str, Any],
    summary="Users Overview",
    description="Admin: Get users overview"
)
async def get_admin_users_overview(admin: Admin = Depends(get_current_admin)):
    """Get detailed users overview for admin."""
    stats = await user_repository.get_stats()
    
    # Get registration stats for last 30 days
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=30)
    registrations = await user_repository.get_registration_stats(start_date, end_date)
    
    return {
        "stats": stats,
        "registrations": registrations,
        "growth_rate": 0,  # TODO: Calculate growth rate
    }


@router.get(
    "/admin/vendors/overview",
    response_model=Dict[str, Any],
    summary="Vendors Overview",
    description="Admin: Get vendors overview"
)
async def get_admin_vendors_overview(admin: Admin = Depends(get_current_admin)):
    """Get detailed vendors overview for admin."""
    stats = await vendor_repository.get_stats()
    categories = await vendor_repository.get_category_distribution()
    
    return {
        "stats": stats,
        "categories": categories,
        "pending_verification": stats.get("pending", 0),
    }


@router.get(
    "/admin/agents/overview",
    response_model=Dict[str, Any],
    summary="Agents Overview",
    description="Admin: Get agents overview"
)
async def get_admin_agents_overview(admin: Admin = Depends(get_current_admin)):
    """Get detailed agents overview for admin."""
    stats = await agent_repository.get_stats()
    types = await agent_repository.get_type_distribution()
    
    return {
        "stats": stats,
        "types": types,
        "pending_verification": stats.get("pending", 0),
    }


@router.get(
    "/admin/revenue",
    response_model=Dict[str, Any],
    summary="Revenue Dashboard",
    description="Admin: Get revenue analytics"
)
async def get_admin_revenue_dashboard(
    period: str = Query("month", enum=["week", "month", "quarter", "year"]),
    admin: Admin = Depends(get_current_admin)
):
    """Get platform revenue analytics for admin."""
    # TODO: Implement when Payment model is complete
    return {
        "total_revenue": 0,
        "commission_revenue": 0,
        "subscription_revenue": 0,
        "period": period,
        "breakdown": [],
        "trends": [],
    }


@router.get(
    "/admin/activity",
    response_model=Dict[str, Any],
    summary="Platform Activity",
    description="Admin: Get recent platform activity"
)
async def get_admin_activity_dashboard(
    limit: int = Query(50, ge=1, le=100),
    admin: Admin = Depends(get_current_admin)
):
    """Get recent platform activity for admin."""
    # TODO: Implement activity feed
    return {
        "activities": [],
        "new_users_today": 0,
        "new_vendors_today": 0,
        "new_bookings_today": 0,
    }

