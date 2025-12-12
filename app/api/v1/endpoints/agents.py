"""
Queska Backend - Agent API Endpoints
RESTful API routes for Agent operations
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from loguru import logger

from app.api.deps import (
    get_current_agent,
    get_current_active_agent,
    get_current_verified_agent,
    get_current_admin,
    get_pagination_params,
)
from app.core.constants import AccountStatus, AgentType, VerificationStatus
from app.core.exceptions import (
    AgentError,
    AlreadyExistsError,
    AuthenticationError,
    InvalidCredentialsError,
    NotFoundError,
    ValidationError,
)
from app.models.agent import Agent
from app.models.admin import Admin
from app.schemas.agent import (
    AgentRegister,
    AgentLogin,
    AgentCreate,
    AgentUpdate,
    AgentResponse,
    AgentPublicResponse,
    AgentMinimalResponse,
    AgentTokenResponse,
    AgentListParams,
    AgentPasswordChange,
    AgentPasswordResetRequest,
    AgentPasswordReset,
    AgentVerificationCreate,
    AgentVerificationReview,
    AgentStatusUpdate,
    AgentFeatureToggle,
    AgentBankAccountAdd,
    AgentMediaCreate,
    AgentSpecializationCreate,
    AgentClientAdd,
    AgentClientRemove,
)
from app.schemas.base import (
    SuccessResponse,
    ErrorResponse,
    DeleteResponse,
    PaginatedResponse,
)
from app.services.agent_service import agent_service


router = APIRouter()


# ==========================================
# PUBLIC ENDPOINTS (No Authentication)
# ==========================================

@router.post(
    "/register",
    response_model=Dict[str, Any],
    status_code=status.HTTP_201_CREATED,
    summary="Register new agent",
    description="Create a new travel agent account"
)
async def register_agent(data: AgentRegister):
    """
    Register a new agent account.
    
    - **email**: Unique email address
    - **password**: Strong password (min 8 chars, uppercase, lowercase, digit)
    - **first_name**: Agent's first name
    - **last_name**: Agent's last name
    - **phone**: Phone number
    - **agent_type**: Type of agent (independent, agency, etc.)
    - **city**: City location
    - **state**: State/province
    - **country**: Country (default: Nigeria)
    - **referral_code**: Optional referral code from another agent
    """
    try:
        agent = await agent_service.register(data)
        return {
            "success": True,
            "message": "Agent registered successfully. Please verify your email.",
            "agent_id": str(agent.id),
            "email": agent.email,
            "referral_code": agent.referral_code
        }
    except AlreadyExistsError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        logger.error(f"Agent registration error: {e}")
        raise HTTPException(status_code=500, detail="Registration failed")


@router.post(
    "/login",
    response_model=AgentTokenResponse,
    summary="Agent login",
    description="Authenticate agent and get access tokens"
)
async def login_agent(data: AgentLogin):
    """
    Authenticate agent with email and password.
    
    Returns access token, refresh token, and agent profile.
    """
    try:
        result = await agent_service.login(data)
        return result
    except InvalidCredentialsError:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )
    except AuthenticationError as e:
        raise HTTPException(status_code=401, detail=str(e))


@router.post(
    "/refresh-token",
    response_model=Dict[str, Any],
    summary="Refresh access token",
    description="Get new access token using refresh token"
)
async def refresh_token(refresh_token: str):
    """Refresh the access token using a valid refresh token."""
    try:
        result = await agent_service.refresh_token(refresh_token)
        return result
    except AuthenticationError as e:
        raise HTTPException(status_code=401, detail=str(e))


@router.post(
    "/forgot-password",
    response_model=SuccessResponse,
    summary="Request password reset",
    description="Send password reset email to agent"
)
async def forgot_password(data: AgentPasswordResetRequest):
    """Request a password reset link via email."""
    try:
        await agent_service.request_password_reset(data.email)
        return SuccessResponse(
            message="Password reset instructions sent to your email"
        )
    except NotFoundError:
        return SuccessResponse(
            message="If this email exists, you will receive reset instructions"
        )


@router.post(
    "/reset-password",
    response_model=SuccessResponse,
    summary="Reset password",
    description="Reset password using token from email"
)
async def reset_password(data: AgentPasswordReset):
    """Reset password using the token received via email."""
    try:
        await agent_service.reset_password(data.token, data.new_password)
        return SuccessResponse(message="Password reset successfully")
    except AuthenticationError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==========================================
# PUBLIC AGENT DISCOVERY
# ==========================================

@router.get(
    "/",
    response_model=Dict[str, Any],
    summary="List agents",
    description="Get paginated list of agents with filters"
)
async def list_agents(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    agent_type: Optional[AgentType] = None,
    city: Optional[str] = None,
    state: Optional[str] = None,
    country: Optional[str] = None,
    is_verified: Optional[bool] = None,
    is_featured: Optional[bool] = None,
    is_available: Optional[bool] = None,
    min_rating: Optional[float] = None,
    min_experience: Optional[int] = None,
    destinations: Optional[str] = None,
    travel_types: Optional[str] = None,
    languages: Optional[str] = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    radius_km: Optional[float] = None,
):
    """
    List agents with filters and pagination.
    
    - **page**: Page number (default: 1)
    - **limit**: Items per page (default: 20, max: 100)
    - **search**: Search in name and bio
    - **agent_type**: Filter by agent type
    - **is_verified**: Filter verified agents
    - **is_featured**: Filter featured agents
    - **is_available**: Filter by availability
    - **min_rating**: Minimum rating filter
    - **min_experience**: Minimum years of experience
    - **destinations**: Comma-separated destination filters
    - **travel_types**: Comma-separated travel type filters
    - **languages**: Comma-separated language filters
    """
    params = AgentListParams(
        page=page,
        limit=limit,
        search=search,
        agent_type=agent_type,
        city=city,
        state=state,
        country=country,
        is_verified=is_verified,
        is_featured=is_featured,
        is_available=is_available,
        min_rating=min_rating,
        min_experience=min_experience,
        destinations=destinations.split(",") if destinations else None,
        travel_types=travel_types.split(",") if travel_types else None,
        languages=languages.split(",") if languages else None,
        sort_by=sort_by,
        sort_order=sort_order,
        latitude=latitude,
        longitude=longitude,
        radius_km=radius_km,
    )
    
    agents, total, pages = await agent_service.list_agents(params)
    
    return {
        "items": agents,
        "total": total,
        "page": page,
        "limit": limit,
        "pages": pages,
        "has_next": page < pages,
        "has_prev": page > 1
    }


@router.get(
    "/featured",
    response_model=List[Dict[str, Any]],
    summary="Get featured agents",
    description="Get list of featured agents"
)
async def get_featured_agents(limit: int = Query(10, ge=1, le=50)):
    """Get featured agents for homepage display."""
    return await agent_service.get_featured_agents(limit)


@router.get(
    "/available",
    response_model=List[Dict[str, Any]],
    summary="Get available agents",
    description="Get agents accepting new clients"
)
async def get_available_agents(
    limit: int = Query(20, ge=1, le=100),
    specialization: Optional[str] = None
):
    """Get agents who are available and accepting new clients."""
    specs = specialization.split(",") if specialization else None
    return await agent_service.get_available_agents(limit, specs)


@router.get(
    "/type/{agent_type}",
    response_model=List[Dict[str, Any]],
    summary="Get agents by type",
    description="Get agents filtered by type"
)
async def get_agents_by_type(
    agent_type: AgentType,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100)
):
    """Get agents by type."""
    return await agent_service.get_agents_by_type(agent_type, skip, limit)


@router.get(
    "/slug/{slug}",
    response_model=Dict[str, Any],
    summary="Get agent by slug",
    description="Get agent public profile by slug"
)
async def get_agent_by_slug(slug: str):
    """Get agent public profile by URL slug."""
    try:
        agent = await agent_service.get_agent_by_slug(slug)
        return agent.to_public_dict()
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Agent not found")


@router.get(
    "/{agent_id}/public",
    response_model=Dict[str, Any],
    summary="Get agent public profile",
    description="Get agent public profile by ID"
)
async def get_agent_public(agent_id: str):
    """Get agent public profile by ID."""
    try:
        agent = await agent_service.get_agent(agent_id)
        return agent.to_public_dict()
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Agent not found")


# ==========================================
# AUTHENTICATED AGENT ENDPOINTS
# ==========================================

@router.get(
    "/me",
    response_model=Dict[str, Any],
    summary="Get current agent profile",
    description="Get authenticated agent's own profile"
)
async def get_current_agent_profile(
    agent: Agent = Depends(get_current_agent)
):
    """Get the currently authenticated agent's profile."""
    return agent_service._to_response(agent)


@router.put(
    "/me",
    response_model=Dict[str, Any],
    summary="Update agent profile",
    description="Update authenticated agent's profile"
)
async def update_agent_profile(
    data: AgentUpdate,
    agent: Agent = Depends(get_current_agent)
):
    """Update the currently authenticated agent's profile."""
    try:
        updated_agent = await agent_service.update_agent(str(agent.id), data)
        return agent_service._to_response(updated_agent)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Agent not found")


@router.post(
    "/me/change-password",
    response_model=SuccessResponse,
    summary="Change password",
    description="Change agent password"
)
async def change_password(
    data: AgentPasswordChange,
    agent: Agent = Depends(get_current_agent)
):
    """Change the current agent's password."""
    try:
        await agent_service.change_password(
            str(agent.id),
            data.current_password,
            data.new_password
        )
        return SuccessResponse(message="Password changed successfully")
    except InvalidCredentialsError as e:
        raise HTTPException(status_code=400, detail=str(e))


# === Availability ===

@router.put(
    "/me/availability",
    response_model=Dict[str, Any],
    summary="Toggle availability",
    description="Toggle agent availability status"
)
async def toggle_availability(
    is_available: bool,
    agent: Agent = Depends(get_current_active_agent)
):
    """Toggle availability to accept new clients."""
    updated_agent = await agent_service.toggle_availability(
        str(agent.id),
        is_available
    )
    return {
        "success": True,
        "is_available": updated_agent.is_available
    }


# === Client Management ===

@router.get(
    "/me/clients",
    response_model=Dict[str, Any],
    summary="Get agent's clients",
    description="Get list of agent's client IDs"
)
async def get_my_clients(
    agent: Agent = Depends(get_current_active_agent)
):
    """Get list of agent's clients."""
    client_ids = await agent_service.get_agent_clients(str(agent.id))
    return {
        "clients": client_ids,
        "total": len(client_ids),
        "max_clients": agent.max_clients,
        "available_slots": agent.max_clients - len(client_ids)
    }


@router.post(
    "/me/clients",
    response_model=Dict[str, Any],
    summary="Add client",
    description="Add a client to agent's roster"
)
async def add_client(
    data: AgentClientAdd,
    agent: Agent = Depends(get_current_active_agent)
):
    """Add a client to the agent's roster."""
    try:
        updated_agent = await agent_service.add_client(
            str(agent.id),
            data.client_id
        )
        return {
            "success": True,
            "message": "Client added successfully",
            "client_count": updated_agent.client_count
        }
    except AgentError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete(
    "/me/clients/{client_id}",
    response_model=SuccessResponse,
    summary="Remove client",
    description="Remove a client from agent's roster"
)
async def remove_client(
    client_id: str,
    agent: Agent = Depends(get_current_active_agent)
):
    """Remove a client from the agent's roster."""
    await agent_service.remove_client(str(agent.id), client_id)
    return SuccessResponse(message="Client removed successfully")


# === Verification ===

@router.post(
    "/me/verification",
    response_model=Dict[str, Any],
    summary="Submit verification documents",
    description="Submit documents for agent verification"
)
async def submit_verification(
    data: AgentVerificationCreate,
    agent: Agent = Depends(get_current_agent)
):
    """Submit verification documents for review."""
    updated_agent = await agent_service.submit_verification(str(agent.id), data)
    return {
        "success": True,
        "message": "Verification documents submitted for review",
        "verification_status": updated_agent.verification.status.value
    }


@router.get(
    "/me/verification",
    response_model=Dict[str, Any],
    summary="Get verification status",
    description="Get agent verification status"
)
async def get_verification_status(
    agent: Agent = Depends(get_current_agent)
):
    """Get the current verification status."""
    if not agent.verification:
        return {"status": "not_submitted"}
    
    return {
        "status": agent.verification.status.value,
        "submitted_at": agent.verification.submitted_at,
        "reviewed_at": agent.verification.reviewed_at,
        "rejection_reason": agent.verification.rejection_reason
    }


# === Specialization ===

@router.put(
    "/me/specialization",
    response_model=Dict[str, Any],
    summary="Update specialization",
    description="Update agent specialization areas"
)
async def update_specialization(
    data: AgentSpecializationCreate,
    agent: Agent = Depends(get_current_agent)
):
    """Update agent specialization (destinations, travel types, languages)."""
    from app.models.agent import AgentSpecialization
    
    agent.specialization = AgentSpecialization(**data.model_dump())
    await agent.save()
    
    return {
        "success": True,
        "specialization": agent.specialization.model_dump()
    }


# === Media ===

@router.put(
    "/me/media",
    response_model=Dict[str, Any],
    summary="Update agent media",
    description="Update agent profile photo and gallery"
)
async def update_agent_media(
    data: AgentMediaCreate,
    agent: Agent = Depends(get_current_agent)
):
    """Update agent media (profile photo, cover, gallery)."""
    updated_agent = await agent_service.update_media(
        str(agent.id),
        data.model_dump(exclude_unset=True)
    )
    return {
        "success": True,
        "media": updated_agent.media.model_dump() if updated_agent.media else None
    }


# === Bank Accounts ===

@router.post(
    "/me/bank-accounts",
    response_model=Dict[str, Any],
    summary="Add bank account",
    description="Add a bank account for commission payouts"
)
async def add_bank_account(
    data: AgentBankAccountAdd,
    agent: Agent = Depends(get_current_active_agent)
):
    """Add a bank account for receiving commission payouts."""
    updated_agent = await agent_service.add_bank_account(
        str(agent.id),
        data.model_dump()
    )
    return {
        "success": True,
        "message": "Bank account added successfully",
        "bank_accounts_count": len(updated_agent.bank_accounts)
    }


@router.get(
    "/me/bank-accounts",
    response_model=List[Dict[str, Any]],
    summary="Get bank accounts",
    description="Get agent's bank accounts"
)
async def get_bank_accounts(
    agent: Agent = Depends(get_current_agent)
):
    """Get list of agent's bank accounts."""
    return [
        {
            "bank_name": acc.bank_name,
            "account_name": acc.account_name,
            "account_number": acc.account_number[-4:].rjust(len(acc.account_number), '*'),
            "is_primary": acc.is_primary,
            "is_verified": acc.is_verified
        }
        for acc in agent.bank_accounts
    ]


# === Analytics & Referrals ===

@router.get(
    "/me/analytics",
    response_model=Dict[str, Any],
    summary="Get agent analytics",
    description="Get agent's performance analytics"
)
async def get_agent_analytics(
    agent: Agent = Depends(get_current_active_agent)
):
    """Get agent analytics and statistics."""
    return agent.analytics.model_dump() if agent.analytics else {}


@router.get(
    "/me/referrals",
    response_model=Dict[str, Any],
    summary="Get referral stats",
    description="Get agent's referral statistics"
)
async def get_referral_stats(
    agent: Agent = Depends(get_current_agent)
):
    """Get agent referral statistics."""
    return {
        "referral_code": agent.referral_code,
        "referral_count": agent.referral_count,
        "referral_earnings": agent.referral_earnings
    }


# ==========================================
# ADMIN AGENT MANAGEMENT ENDPOINTS
# ==========================================

@router.get(
    "/admin/stats",
    response_model=Dict[str, Any],
    summary="Get agent statistics",
    description="Admin: Get overall agent statistics"
)
async def get_agent_stats(admin: Admin = Depends(get_current_admin)):
    """Get agent statistics for admin dashboard."""
    return await agent_service.get_agent_stats()


@router.get(
    "/admin/types",
    response_model=List[Dict[str, Any]],
    summary="Get type distribution",
    description="Admin: Get agent distribution by type"
)
async def get_type_distribution(admin: Admin = Depends(get_current_admin)):
    """Get agent distribution by type."""
    return await agent_service.get_type_distribution()


@router.get(
    "/admin/{agent_id}",
    response_model=Dict[str, Any],
    summary="Get agent details",
    description="Admin: Get full agent details"
)
async def admin_get_agent(
    agent_id: str,
    admin: Admin = Depends(get_current_admin)
):
    """Admin: Get full agent details including sensitive info."""
    try:
        agent = await agent_service.get_agent(agent_id)
        return agent_service._to_response(agent)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Agent not found")


@router.put(
    "/admin/{agent_id}/status",
    response_model=Dict[str, Any],
    summary="Update agent status",
    description="Admin: Update agent account status"
)
async def admin_update_agent_status(
    agent_id: str,
    data: AgentStatusUpdate,
    admin: Admin = Depends(get_current_admin)
):
    """Admin: Update agent account status (activate, suspend, disable)."""
    try:
        updated_agent = await agent_service.update_status(
            agent_id,
            data.status,
            data.reason
        )
        return {
            "success": True,
            "message": f"Agent status updated to {data.status.value}",
            "agent_id": agent_id
        }
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Agent not found")


@router.put(
    "/admin/{agent_id}/verify",
    response_model=Dict[str, Any],
    summary="Review agent verification",
    description="Admin: Review and update agent verification"
)
async def admin_verify_agent(
    agent_id: str,
    data: AgentVerificationReview,
    admin: Admin = Depends(get_current_admin)
):
    """Admin: Review agent verification documents and approve/reject."""
    try:
        updated_agent = await agent_service.review_verification(
            agent_id,
            str(admin.id),
            data
        )
        return {
            "success": True,
            "message": f"Verification {data.status.value}",
            "is_verified": updated_agent.is_verified
        }
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Agent not found")


@router.put(
    "/admin/{agent_id}/features",
    response_model=Dict[str, Any],
    summary="Toggle agent features",
    description="Admin: Toggle featured/premium status"
)
async def admin_toggle_features(
    agent_id: str,
    data: AgentFeatureToggle,
    admin: Admin = Depends(get_current_admin)
):
    """Admin: Toggle agent featured or premium status."""
    try:
        if data.is_featured is not None:
            await agent_service.toggle_featured(agent_id, data.is_featured)
        if data.is_premium is not None:
            await agent_service.toggle_premium(agent_id, data.is_premium)
        if data.is_verified is not None:
            agent = await agent_service.get_agent(agent_id)
            agent.is_verified = data.is_verified
            await agent.save()
        
        return {"success": True, "message": "Agent features updated"}
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Agent not found")


@router.delete(
    "/admin/{agent_id}",
    response_model=DeleteResponse,
    summary="Delete agent",
    description="Admin: Soft delete agent account"
)
async def admin_delete_agent(
    agent_id: str,
    admin: Admin = Depends(get_current_admin)
):
    """Admin: Soft delete an agent account."""
    try:
        await agent_service.delete_agent(agent_id, soft=True)
        return DeleteResponse(id=agent_id)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Agent not found")

