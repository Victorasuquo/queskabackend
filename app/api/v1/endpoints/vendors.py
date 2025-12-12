"""
Queska Backend - Vendor API Endpoints
RESTful API routes for Vendor operations
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from loguru import logger

from app.api.deps import (
    get_current_vendor,
    get_current_active_vendor,
    get_current_verified_vendor,
    get_current_admin,
    get_pagination_params,
)
from app.core.constants import AccountStatus, VendorCategory, VerificationStatus
from app.core.exceptions import (
    AlreadyExistsError,
    AuthenticationError,
    InvalidCredentialsError,
    NotFoundError,
    ValidationError,
    VendorError,
)
from app.models.vendor import Vendor
from app.models.admin import Admin
from app.schemas.vendor import (
    VendorRegister,
    VendorLogin,
    VendorCreate,
    VendorUpdate,
    VendorResponse,
    VendorPublicResponse,
    VendorMinimalResponse,
    VendorTokenResponse,
    VendorListParams,
    VendorPasswordChange,
    VendorPasswordResetRequest,
    VendorPasswordReset,
    VendorVerificationCreate,
    VendorVerificationReview,
    VendorStatusUpdate,
    VendorFeatureToggle,
    VendorBankAccountAdd,
    VendorMediaCreate,
)
from app.schemas.base import (
    SuccessResponse,
    ErrorResponse,
    DeleteResponse,
    PaginatedResponse,
)
from app.services.vendor_service import vendor_service


router = APIRouter()


# ==========================================
# PUBLIC ENDPOINTS (No Authentication)
# ==========================================

@router.post(
    "/register",
    response_model=Dict[str, Any],
    status_code=status.HTTP_201_CREATED,
    summary="Register new vendor",
    description="Create a new vendor account with business details"
)
async def register_vendor(data: VendorRegister):
    """
    Register a new vendor account.
    
    - **email**: Unique email address
    - **password**: Strong password (min 8 chars, uppercase, lowercase, digit)
    - **business_name**: Name of the business
    - **category**: Type of business (hotel, restaurant, etc.)
    - **owner_first_name**: Owner's first name
    - **owner_last_name**: Owner's last name
    - **owner_phone**: Owner's phone number
    - **city**: City location
    - **state**: State/province
    - **country**: Country (default: Nigeria)
    """
    try:
        vendor = await vendor_service.register(data)
        return {
            "success": True,
            "message": "Vendor registered successfully. Please verify your email.",
            "vendor_id": str(vendor.id),
            "email": vendor.email
        }
    except AlreadyExistsError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        logger.error(f"Vendor registration error: {e}")
        raise HTTPException(status_code=500, detail="Registration failed")


@router.post(
    "/login",
    response_model=VendorTokenResponse,
    summary="Vendor login",
    description="Authenticate vendor and get access tokens"
)
async def login_vendor(data: VendorLogin):
    """
    Authenticate vendor with email and password.
    
    Returns access token, refresh token, and vendor profile.
    """
    try:
        result = await vendor_service.login(data)
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
        result = await vendor_service.refresh_token(refresh_token)
        return result
    except AuthenticationError as e:
        raise HTTPException(status_code=401, detail=str(e))


@router.post(
    "/forgot-password",
    response_model=SuccessResponse,
    summary="Request password reset",
    description="Send password reset email to vendor"
)
async def forgot_password(data: VendorPasswordResetRequest):
    """Request a password reset link via email."""
    try:
        await vendor_service.request_password_reset(data.email)
        return SuccessResponse(
            message="Password reset instructions sent to your email"
        )
    except NotFoundError:
        # Don't reveal if email exists
        return SuccessResponse(
            message="If this email exists, you will receive reset instructions"
        )


@router.post(
    "/reset-password",
    response_model=SuccessResponse,
    summary="Reset password",
    description="Reset password using token from email"
)
async def reset_password(data: VendorPasswordReset):
    """Reset password using the token received via email."""
    try:
        await vendor_service.reset_password(data.token, data.new_password)
        return SuccessResponse(message="Password reset successfully")
    except AuthenticationError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==========================================
# PUBLIC VENDOR DISCOVERY
# ==========================================

@router.get(
    "/",
    response_model=Dict[str, Any],
    summary="List vendors",
    description="Get paginated list of vendors with filters"
)
async def list_vendors(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    category: Optional[VendorCategory] = None,
    city: Optional[str] = None,
    state: Optional[str] = None,
    country: Optional[str] = None,
    is_verified: Optional[bool] = None,
    is_featured: Optional[bool] = None,
    min_rating: Optional[float] = None,
    max_price: Optional[float] = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    radius_km: Optional[float] = None,
):
    """
    List vendors with filters and pagination.
    
    - **page**: Page number (default: 1)
    - **limit**: Items per page (default: 20, max: 100)
    - **search**: Search in business name and description
    - **category**: Filter by vendor category
    - **city/state/country**: Location filters
    - **is_verified**: Filter verified vendors
    - **is_featured**: Filter featured vendors
    - **min_rating**: Minimum rating filter
    - **latitude/longitude/radius_km**: Geo search
    """
    params = VendorListParams(
        page=page,
        limit=limit,
        search=search,
        category=category,
        city=city,
        state=state,
        country=country,
        is_verified=is_verified,
        is_featured=is_featured,
        min_rating=min_rating,
        max_price=max_price,
        sort_by=sort_by,
        sort_order=sort_order,
        latitude=latitude,
        longitude=longitude,
        radius_km=radius_km,
    )
    
    vendors, total, pages = await vendor_service.list_vendors(params)
    
    return {
        "items": vendors,
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
    summary="Get featured vendors",
    description="Get list of featured vendors"
)
async def get_featured_vendors(limit: int = Query(10, ge=1, le=50)):
    """Get featured vendors for homepage display."""
    return await vendor_service.get_featured_vendors(limit)


@router.get(
    "/category/{category}",
    response_model=List[Dict[str, Any]],
    summary="Get vendors by category",
    description="Get vendors filtered by category"
)
async def get_vendors_by_category(
    category: VendorCategory,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100)
):
    """Get vendors by category."""
    return await vendor_service.get_vendors_by_category(category, skip, limit)


@router.get(
    "/nearby",
    response_model=List[Dict[str, Any]],
    summary="Get nearby vendors",
    description="Get vendors near a location"
)
async def get_nearby_vendors(
    latitude: float,
    longitude: float,
    radius_km: float = Query(10, ge=1, le=100),
    category: Optional[VendorCategory] = None,
    limit: int = Query(20, ge=1, le=100)
):
    """Find vendors near a specific location."""
    return await vendor_service.get_nearby_vendors(
        longitude, latitude, radius_km, category, limit
    )


@router.get(
    "/slug/{slug}",
    response_model=Dict[str, Any],
    summary="Get vendor by slug",
    description="Get vendor public profile by slug"
)
async def get_vendor_by_slug(slug: str):
    """Get vendor public profile by URL slug."""
    try:
        vendor = await vendor_service.get_vendor_by_slug(slug)
        # Increment views
        await vendor_service.increment_vendor_views(str(vendor.id))
        return vendor.to_public_dict()
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Vendor not found")


@router.get(
    "/{vendor_id}/public",
    response_model=Dict[str, Any],
    summary="Get vendor public profile",
    description="Get vendor public profile by ID"
)
async def get_vendor_public(vendor_id: str):
    """Get vendor public profile by ID."""
    try:
        vendor = await vendor_service.get_vendor(vendor_id)
        await vendor_service.increment_vendor_views(vendor_id)
        return vendor.to_public_dict()
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Vendor not found")


# ==========================================
# AUTHENTICATED VENDOR ENDPOINTS
# ==========================================

@router.get(
    "/me",
    response_model=Dict[str, Any],
    summary="Get current vendor profile",
    description="Get authenticated vendor's own profile"
)
async def get_current_vendor_profile(
    vendor: Vendor = Depends(get_current_vendor)
):
    """Get the currently authenticated vendor's profile."""
    return vendor_service._to_response(vendor)


@router.put(
    "/me",
    response_model=Dict[str, Any],
    summary="Update vendor profile",
    description="Update authenticated vendor's profile"
)
async def update_vendor_profile(
    data: VendorUpdate,
    vendor: Vendor = Depends(get_current_vendor)
):
    """Update the currently authenticated vendor's profile."""
    try:
        updated_vendor = await vendor_service.update_vendor(str(vendor.id), data)
        return vendor_service._to_response(updated_vendor)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Vendor not found")


@router.post(
    "/me/change-password",
    response_model=SuccessResponse,
    summary="Change password",
    description="Change vendor password"
)
async def change_password(
    data: VendorPasswordChange,
    vendor: Vendor = Depends(get_current_vendor)
):
    """Change the current vendor's password."""
    try:
        await vendor_service.change_password(
            str(vendor.id),
            data.current_password,
            data.new_password
        )
        return SuccessResponse(message="Password changed successfully")
    except InvalidCredentialsError as e:
        raise HTTPException(status_code=400, detail=str(e))


# === Verification ===

@router.post(
    "/me/verification",
    response_model=Dict[str, Any],
    summary="Submit verification documents",
    description="Submit documents for vendor verification"
)
async def submit_verification(
    data: VendorVerificationCreate,
    vendor: Vendor = Depends(get_current_vendor)
):
    """Submit verification documents for review."""
    updated_vendor = await vendor_service.submit_verification(str(vendor.id), data)
    return {
        "success": True,
        "message": "Verification documents submitted for review",
        "verification_status": updated_vendor.verification.status.value
    }


@router.get(
    "/me/verification",
    response_model=Dict[str, Any],
    summary="Get verification status",
    description="Get vendor verification status"
)
async def get_verification_status(
    vendor: Vendor = Depends(get_current_vendor)
):
    """Get the current verification status."""
    if not vendor.verification:
        return {"status": "not_submitted"}
    
    return {
        "status": vendor.verification.status.value,
        "submitted_at": vendor.verification.submitted_at,
        "reviewed_at": vendor.verification.reviewed_at,
        "rejection_reason": vendor.verification.rejection_reason
    }


# === Media ===

@router.put(
    "/me/media",
    response_model=Dict[str, Any],
    summary="Update vendor media",
    description="Update vendor logo, cover image, and gallery"
)
async def update_vendor_media(
    data: VendorMediaCreate,
    vendor: Vendor = Depends(get_current_vendor)
):
    """Update vendor media (logo, cover, gallery)."""
    updated_vendor = await vendor_service.update_media(
        str(vendor.id),
        data.model_dump(exclude_unset=True)
    )
    return {
        "success": True,
        "media": updated_vendor.media.model_dump() if updated_vendor.media else None
    }


# === Bank Accounts ===

@router.post(
    "/me/bank-accounts",
    response_model=Dict[str, Any],
    summary="Add bank account",
    description="Add a bank account for payouts"
)
async def add_bank_account(
    data: VendorBankAccountAdd,
    vendor: Vendor = Depends(get_current_active_vendor)
):
    """Add a bank account for receiving payouts."""
    updated_vendor = await vendor_service.add_bank_account(
        str(vendor.id),
        data.model_dump()
    )
    return {
        "success": True,
        "message": "Bank account added successfully",
        "bank_accounts_count": len(updated_vendor.bank_accounts)
    }


@router.get(
    "/me/bank-accounts",
    response_model=List[Dict[str, Any]],
    summary="Get bank accounts",
    description="Get vendor's bank accounts"
)
async def get_bank_accounts(
    vendor: Vendor = Depends(get_current_vendor)
):
    """Get list of vendor's bank accounts."""
    return [
        {
            "bank_name": acc.bank_name,
            "account_name": acc.account_name,
            "account_number": acc.account_number[-4:].rjust(len(acc.account_number), '*'),
            "is_primary": acc.is_primary,
            "is_verified": acc.is_verified
        }
        for acc in vendor.bank_accounts
    ]


# === Analytics ===

@router.get(
    "/me/analytics",
    response_model=Dict[str, Any],
    summary="Get vendor analytics",
    description="Get vendor's analytics dashboard"
)
async def get_vendor_analytics(
    vendor: Vendor = Depends(get_current_active_vendor)
):
    """Get vendor analytics and statistics."""
    return vendor.analytics.model_dump() if vendor.analytics else {}


# ==========================================
# ADMIN VENDOR MANAGEMENT ENDPOINTS
# ==========================================

@router.get(
    "/admin/stats",
    response_model=Dict[str, Any],
    summary="Get vendor statistics",
    description="Admin: Get overall vendor statistics"
)
async def get_vendor_stats(admin: Admin = Depends(get_current_admin)):
    """Get vendor statistics for admin dashboard."""
    return await vendor_service.get_vendor_stats()


@router.get(
    "/admin/categories",
    response_model=List[Dict[str, Any]],
    summary="Get category distribution",
    description="Admin: Get vendor distribution by category"
)
async def get_category_distribution(admin: Admin = Depends(get_current_admin)):
    """Get vendor distribution by category."""
    return await vendor_service.get_category_distribution()


@router.get(
    "/admin/{vendor_id}",
    response_model=Dict[str, Any],
    summary="Get vendor details",
    description="Admin: Get full vendor details"
)
async def admin_get_vendor(
    vendor_id: str,
    admin: Admin = Depends(get_current_admin)
):
    """Admin: Get full vendor details including sensitive info."""
    try:
        vendor = await vendor_service.get_vendor(vendor_id)
        return vendor_service._to_response(vendor)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Vendor not found")


@router.put(
    "/admin/{vendor_id}/status",
    response_model=Dict[str, Any],
    summary="Update vendor status",
    description="Admin: Update vendor account status"
)
async def admin_update_vendor_status(
    vendor_id: str,
    data: VendorStatusUpdate,
    admin: Admin = Depends(get_current_admin)
):
    """Admin: Update vendor account status (activate, suspend, disable)."""
    try:
        updated_vendor = await vendor_service.update_status(
            vendor_id,
            data.status,
            data.reason
        )
        return {
            "success": True,
            "message": f"Vendor status updated to {data.status.value}",
            "vendor_id": vendor_id
        }
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Vendor not found")


@router.put(
    "/admin/{vendor_id}/verify",
    response_model=Dict[str, Any],
    summary="Review vendor verification",
    description="Admin: Review and update vendor verification"
)
async def admin_verify_vendor(
    vendor_id: str,
    data: VendorVerificationReview,
    admin: Admin = Depends(get_current_admin)
):
    """Admin: Review vendor verification documents and approve/reject."""
    try:
        updated_vendor = await vendor_service.review_verification(
            vendor_id,
            str(admin.id),
            data
        )
        return {
            "success": True,
            "message": f"Verification {data.status.value}",
            "is_verified": updated_vendor.is_verified
        }
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Vendor not found")


@router.put(
    "/admin/{vendor_id}/features",
    response_model=Dict[str, Any],
    summary="Toggle vendor features",
    description="Admin: Toggle featured/premium status"
)
async def admin_toggle_features(
    vendor_id: str,
    data: VendorFeatureToggle,
    admin: Admin = Depends(get_current_admin)
):
    """Admin: Toggle vendor featured or premium status."""
    try:
        if data.is_featured is not None:
            await vendor_service.toggle_featured(vendor_id, data.is_featured)
        if data.is_premium is not None:
            await vendor_service.toggle_premium(vendor_id, data.is_premium)
        if data.is_verified is not None:
            vendor = await vendor_service.get_vendor(vendor_id)
            vendor.is_verified = data.is_verified
            await vendor.save()
        
        return {"success": True, "message": "Vendor features updated"}
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Vendor not found")


@router.delete(
    "/admin/{vendor_id}",
    response_model=DeleteResponse,
    summary="Delete vendor",
    description="Admin: Soft delete vendor account"
)
async def admin_delete_vendor(
    vendor_id: str,
    admin: Admin = Depends(get_current_admin)
):
    """Admin: Soft delete a vendor account."""
    try:
        await vendor_service.delete_vendor(vendor_id, soft=True)
        return DeleteResponse(id=vendor_id)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Vendor not found")

