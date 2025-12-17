"""
Queska Backend - Activity Endpoints
API routes for activities, tours, and experiences
"""

from datetime import date
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import get_current_active_user, get_current_verified_vendor, get_current_user_optional
from app.core.exceptions import NotFoundError, ValidationError, ForbiddenError
from app.models.user import User
from app.models.vendor import Vendor
from app.schemas.base import SuccessResponse
from app.schemas.activity import (
    # Create/Update
    ActivityCreate,
    ActivityUpdate,
    # Responses
    ActivityResponse,
    ActivityListResponse,
    PaginatedActivitiesResponse,
    # Availability
    AvailabilitySlot,
    AvailabilityResponse,
    # Booking
    ActivityBookingCreate,
    ActivityBookingResponse,
    PaginatedBookingsResponse,
    BookingCancelRequest,
    # Review
    ActivityReviewCreate,
    ActivityReviewResponse,
    PaginatedReviewsResponse,
    # Search
    ActivitySearchRequest,
    ActivitySearchResponse,
    # Wishlist
    WishlistAddRequest,
    WishlistResponse,
    PaginatedWishlistResponse,
    # Schemas
    ActivityLocationSchema,
    ActivityDurationSchema,
    ActivityPricingSchema,
    ActivityCapacitySchema,
    ActivityInclusionsSchema,
    ActivityRequirementsSchema,
    ActivityPoliciesSchema,
    ActivityRatingSchema,
    ActivityProviderSchema,
)
from app.services.activity_service import activity_service

router = APIRouter()


# ================================================================
# DISCOVERY / LISTING
# ================================================================

@router.get(
    "",
    response_model=PaginatedActivitiesResponse,
    summary="List activities",
)
async def list_activities(
    category: Optional[str] = Query(None, description="Filter by category"),
    city: Optional[str] = Query(None, description="Filter by city"),
    is_featured: Optional[bool] = Query(None, description="Featured only"),
    sort_by: str = Query("recommended", description="Sort order"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    """List activities with optional filters."""
    activities, total = await activity_service.list_activities(
        category=category,
        city=city,
        is_featured=is_featured,
        skip=skip,
        limit=limit,
        sort_by=sort_by,
    )
    
    return PaginatedActivitiesResponse(
        data=[_to_list_response(a) for a in activities],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/featured",
    response_model=List[ActivityListResponse],
    summary="Get featured activities",
)
async def get_featured_activities(
    city: Optional[str] = Query(None),
    limit: int = Query(10, ge=1, le=50),
):
    """Get featured activities."""
    activities = await activity_service.get_featured_activities(city=city, limit=limit)
    return [_to_list_response(a) for a in activities]


@router.get(
    "/popular",
    response_model=List[ActivityListResponse],
    summary="Get popular activities",
)
async def get_popular_activities(
    city: Optional[str] = Query(None),
    limit: int = Query(10, ge=1, le=50),
):
    """Get popular activities."""
    activities = await activity_service.get_popular_activities(city=city, limit=limit)
    return [_to_list_response(a) for a in activities]


@router.get(
    "/categories",
    response_model=List[Dict[str, Any]],
    summary="Get activity categories",
)
async def get_categories():
    """Get activity categories with counts."""
    return await activity_service.get_categories()


@router.post(
    "/search",
    response_model=ActivitySearchResponse,
    summary="Search activities",
)
async def search_activities(
    request: ActivitySearchRequest,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    """Search activities with advanced filters."""
    activities, total, filters = await activity_service.search_activities(
        request=request,
        skip=skip,
        limit=limit,
    )
    
    return ActivitySearchResponse(
        success=True,
        activities=[_to_list_response(a) for a in activities],
        total=total,
        filters_applied=filters,
        providers_used=["internal"],
    )


# ================================================================
# ACTIVITY DETAILS
# ================================================================

@router.get(
    "/{activity_id}",
    response_model=ActivityResponse,
    summary="Get activity by ID",
)
async def get_activity(activity_id: str):
    """Get activity details by ID."""
    try:
        activity = await activity_service.get_activity_by_id(activity_id)
        return _to_response(activity)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get(
    "/slug/{slug}",
    response_model=ActivityResponse,
    summary="Get activity by slug",
)
async def get_activity_by_slug(slug: str):
    """Get activity details by slug."""
    try:
        activity = await activity_service.get_activity_by_slug(slug)
        return _to_response(activity)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# ================================================================
# VENDOR ACTIVITY MANAGEMENT
# ================================================================

@router.post(
    "",
    response_model=ActivityResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create activity (Vendor)",
)
async def create_activity(
    data: ActivityCreate,
    current_vendor: Vendor = Depends(get_current_verified_vendor),
):
    """Create a new activity (vendors only)."""
    try:
        activity = await activity_service.create_activity(
            data=data,
            vendor_id=str(current_vendor.id),
            created_by=str(current_vendor.id),
        )
        return _to_response(activity)
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))


@router.put(
    "/{activity_id}",
    response_model=ActivityResponse,
    summary="Update activity (Vendor)",
)
async def update_activity(
    activity_id: str,
    data: ActivityUpdate,
    current_vendor: Vendor = Depends(get_current_verified_vendor),
):
    """Update an activity (owner vendors only)."""
    try:
        activity = await activity_service.update_activity(
            activity_id=activity_id,
            data=data,
            vendor_id=str(current_vendor.id),
        )
        return _to_response(activity)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ForbiddenError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.delete(
    "/{activity_id}",
    response_model=SuccessResponse,
    summary="Delete activity (Vendor)",
)
async def delete_activity(
    activity_id: str,
    current_vendor: Vendor = Depends(get_current_verified_vendor),
):
    """Delete an activity (owner vendors only)."""
    try:
        await activity_service.delete_activity(
            activity_id=activity_id,
            vendor_id=str(current_vendor.id),
        )
        return SuccessResponse(message="Activity deleted successfully")
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ForbiddenError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.get(
    "/vendor/my-activities",
    response_model=PaginatedActivitiesResponse,
    summary="Get vendor's activities",
)
async def get_vendor_activities(
    current_vendor: Vendor = Depends(get_current_verified_vendor),
    is_active: Optional[bool] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    """Get all activities for the current vendor."""
    activities, total = await activity_service.list_activities(
        vendor_id=str(current_vendor.id),
        is_active=is_active,
        skip=skip,
        limit=limit,
    )
    
    return PaginatedActivitiesResponse(
        data=[_to_list_response(a) for a in activities],
        total=total,
        skip=skip,
        limit=limit,
    )


# ================================================================
# AVAILABILITY
# ================================================================

@router.get(
    "/{activity_id}/availability",
    response_model=AvailabilityResponse,
    summary="Check availability",
)
async def get_availability(
    activity_id: str,
    start_date: date = Query(..., description="Start date"),
    end_date: date = Query(..., description="End date"),
    participants: int = Query(1, ge=1, le=100, description="Number of participants"),
):
    """Get availability slots for an activity."""
    try:
        slots = await activity_service.get_availability(
            activity_id=activity_id,
            start_date=start_date,
            end_date=end_date,
            participants=participants,
        )
        
        return AvailabilityResponse(
            activity_id=activity_id,
            slots=[
                AvailabilitySlot(
                    id=str(s.id),
                    date=s.date,
                    start_time=s.start_time,
                    end_time=s.end_time,
                    total_spots=s.total_spots,
                    remaining_spots=s.remaining_spots,
                    price=s.price_override,
                    is_available=s.is_available,
                )
                for s in slots
            ]
        )
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post(
    "/{activity_id}/availability",
    response_model=List[AvailabilitySlot],
    summary="Create availability slots (Vendor)",
)
async def create_availability(
    activity_id: str,
    dates: List[date],
    start_times: List[str],
    spots_per_slot: int = Query(20, ge=1, le=1000),
    current_vendor: Vendor = Depends(get_current_verified_vendor),
):
    """Create availability slots for an activity."""
    try:
        slots = await activity_service.create_availability_slots(
            activity_id=activity_id,
            dates=dates,
            start_times=start_times,
            spots_per_slot=spots_per_slot,
            vendor_id=str(current_vendor.id),
        )
        
        return [
            AvailabilitySlot(
                id=str(s.id),
                date=s.date,
                start_time=s.start_time,
                total_spots=s.total_spots,
                remaining_spots=s.remaining_spots,
                is_available=True,
            )
            for s in slots
        ]
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ForbiddenError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


# ================================================================
# BOOKINGS
# ================================================================

@router.post(
    "/bookings",
    response_model=ActivityBookingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create booking",
)
async def create_booking(
    data: ActivityBookingCreate,
    current_user: User = Depends(get_current_active_user),
):
    """Book an activity."""
    try:
        booking = await activity_service.create_booking(
            data=data,
            user_id=str(current_user.id),
        )
        
        activity = await activity_service.get_activity_by_id(data.activity_id)
        
        return ActivityBookingResponse(
            id=str(booking.id),
            booking_reference=booking.booking_reference,
            activity_id=booking.activity_id,
            activity_name=activity.name,
            activity_date=booking.activity_date,
            start_time=booking.start_time,
            adults=booking.adults,
            children=booking.children,
            infants=booking.infants,
            total_participants=booking.total_participants,
            unit_price=booking.unit_price,
            subtotal=booking.subtotal,
            fees=booking.fees,
            taxes=booking.taxes,
            discount=booking.discount,
            total_price=booking.total_price,
            currency=booking.currency,
            status=booking.status,
            payment_status=booking.payment_status,
            confirmation_code=booking.confirmation_code,
            contact_name=booking.contact_name,
            contact_email=booking.contact_email,
            contact_phone=booking.contact_phone,
            created_at=booking.created_at,
        )
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))


@router.get(
    "/bookings/my-bookings",
    response_model=PaginatedBookingsResponse,
    summary="Get my bookings",
)
async def get_my_bookings(
    current_user: User = Depends(get_current_active_user),
    status_filter: Optional[str] = Query(None, alias="status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    """Get current user's activity bookings."""
    bookings, total = await activity_service.get_user_bookings(
        user_id=str(current_user.id),
        status=status_filter,
        skip=skip,
        limit=limit,
    )
    
    # Get activity names
    booking_responses = []
    for booking in bookings:
        try:
            activity = await activity_service.get_activity_by_id(booking.activity_id)
            activity_name = activity.name
        except:
            activity_name = "Unknown Activity"
        
        booking_responses.append(ActivityBookingResponse(
            id=str(booking.id),
            booking_reference=booking.booking_reference,
            activity_id=booking.activity_id,
            activity_name=activity_name,
            activity_date=booking.activity_date,
            start_time=booking.start_time,
            adults=booking.adults,
            children=booking.children,
            infants=booking.infants,
            total_participants=booking.total_participants,
            unit_price=booking.unit_price,
            subtotal=booking.subtotal,
            fees=booking.fees,
            taxes=booking.taxes,
            discount=booking.discount,
            total_price=booking.total_price,
            currency=booking.currency,
            status=booking.status,
            payment_status=booking.payment_status,
            confirmation_code=booking.confirmation_code,
            voucher_url=booking.voucher_url,
            qr_code_url=booking.qr_code_url,
            contact_name=booking.contact_name,
            contact_email=booking.contact_email,
            contact_phone=booking.contact_phone,
            created_at=booking.created_at,
            confirmed_at=booking.confirmed_at,
        ))
    
    return PaginatedBookingsResponse(
        data=booking_responses,
        total=total,
        skip=skip,
        limit=limit,
    )


@router.post(
    "/bookings/{booking_id}/cancel",
    response_model=ActivityBookingResponse,
    summary="Cancel booking",
)
async def cancel_booking(
    booking_id: str,
    data: BookingCancelRequest,
    current_user: User = Depends(get_current_active_user),
):
    """Cancel an activity booking."""
    try:
        booking = await activity_service.cancel_booking(
            booking_id=booking_id,
            user_id=str(current_user.id),
            reason=data.reason,
        )
        
        activity = await activity_service.get_activity_by_id(booking.activity_id)
        
        return ActivityBookingResponse(
            id=str(booking.id),
            booking_reference=booking.booking_reference,
            activity_id=booking.activity_id,
            activity_name=activity.name,
            activity_date=booking.activity_date,
            start_time=booking.start_time,
            adults=booking.adults,
            children=booking.children,
            infants=booking.infants,
            total_participants=booking.total_participants,
            unit_price=booking.unit_price,
            subtotal=booking.subtotal,
            fees=booking.fees,
            taxes=booking.taxes,
            discount=booking.discount,
            total_price=booking.total_price,
            currency=booking.currency,
            status=booking.status,
            payment_status=booking.payment_status,
            contact_name=booking.contact_name,
            contact_email=booking.contact_email,
            contact_phone=booking.contact_phone,
            created_at=booking.created_at,
        )
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))


# ================================================================
# REVIEWS
# ================================================================

@router.get(
    "/{activity_id}/reviews",
    response_model=PaginatedReviewsResponse,
    summary="Get activity reviews",
)
async def get_activity_reviews(
    activity_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    """Get reviews for an activity."""
    try:
        reviews, total = await activity_service.get_activity_reviews(
            activity_id=activity_id,
            skip=skip,
            limit=limit,
        )
        
        return PaginatedReviewsResponse(
            data=[
                ActivityReviewResponse(
                    id=str(r.id),
                    activity_id=r.activity_id,
                    user_id=r.user_id,
                    user_name="User",  # Would fetch from user service
                    overall_rating=r.overall_rating,
                    ratings=r.ratings,
                    title=r.title,
                    content=r.content,
                    activity_date=r.activity_date,
                    travel_type=r.travel_type,
                    photos=r.photos,
                    vendor_response=r.vendor_response,
                    vendor_response_at=r.vendor_response_at,
                    helpful_count=r.helpful_count,
                    created_at=r.created_at,
                )
                for r in reviews
            ],
            total=total,
            skip=skip,
            limit=limit,
        )
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post(
    "/{activity_id}/reviews",
    response_model=ActivityReviewResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create review",
)
async def create_review(
    activity_id: str,
    data: ActivityReviewCreate,
    current_user: User = Depends(get_current_active_user),
):
    """Create a review for an activity."""
    try:
        data.activity_id = activity_id
        review = await activity_service.create_review(
            data=data,
            user_id=str(current_user.id),
        )
        
        return ActivityReviewResponse(
            id=str(review.id),
            activity_id=review.activity_id,
            user_id=review.user_id,
            user_name=f"{current_user.first_name} {current_user.last_name}".strip() or "User",
            user_avatar=current_user.avatar,
            overall_rating=review.overall_rating,
            ratings=review.ratings,
            title=review.title,
            content=review.content,
            activity_date=review.activity_date,
            travel_type=review.travel_type,
            photos=review.photos,
            helpful_count=0,
            created_at=review.created_at,
        )
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))


# ================================================================
# WISHLIST
# ================================================================

@router.post(
    "/wishlist",
    response_model=SuccessResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add to wishlist",
)
async def add_to_wishlist(
    data: WishlistAddRequest,
    current_user: User = Depends(get_current_active_user),
):
    """Add an activity to wishlist."""
    try:
        await activity_service.add_to_wishlist(
            user_id=str(current_user.id),
            activity_id=data.activity_id,
            notes=data.notes,
            planned_date=data.planned_date,
        )
        return SuccessResponse(message="Added to wishlist")
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))


@router.delete(
    "/wishlist/{activity_id}",
    response_model=SuccessResponse,
    summary="Remove from wishlist",
)
async def remove_from_wishlist(
    activity_id: str,
    current_user: User = Depends(get_current_active_user),
):
    """Remove an activity from wishlist."""
    removed = await activity_service.remove_from_wishlist(
        user_id=str(current_user.id),
        activity_id=activity_id,
    )
    
    if removed:
        return SuccessResponse(message="Removed from wishlist")
    else:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Activity not in wishlist")


@router.get(
    "/wishlist/my-wishlist",
    response_model=PaginatedWishlistResponse,
    summary="Get my wishlist",
)
async def get_my_wishlist(
    current_user: User = Depends(get_current_active_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    """Get current user's activity wishlist."""
    items, total = await activity_service.get_user_wishlist(
        user_id=str(current_user.id),
        skip=skip,
        limit=limit,
    )
    
    wishlist_responses = []
    for item in items:
        try:
            activity = await activity_service.get_activity_by_id(item.activity_id)
            wishlist_responses.append(WishlistResponse(
                id=str(item.id),
                activity=_to_list_response(activity),
                notes=item.notes,
                planned_date=item.planned_date,
                added_at=item.created_at,
            ))
        except:
            pass  # Skip if activity not found
    
    return PaginatedWishlistResponse(
        data=wishlist_responses,
        total=total,
        skip=skip,
        limit=limit,
    )


# ================================================================
# HELPER FUNCTIONS
# ================================================================

def _to_list_response(activity) -> ActivityListResponse:
    """Convert activity to list response."""
    return ActivityListResponse(
        id=str(activity.id),
        name=activity.name,
        slug=activity.slug,
        short_description=activity.short_description,
        category=activity.category,
        city=activity.location.city,
        country=activity.location.country,
        duration_text=activity.duration.display_text,
        from_price=activity.pricing.from_price,
        currency=activity.pricing.currency,
        cover_image=activity.cover_image,
        rating=activity.rating.average if activity.rating else 0.0,
        review_count=activity.rating.count if activity.rating else 0,
        is_featured=activity.is_featured,
        instant_confirmation=activity.policies.instant_confirmation if activity.policies else True,
        free_cancellation=activity.policies.cancellation_policy in ["free", "flexible"] if activity.policies else False,
        provider_name=activity.provider.name if activity.provider else None,
        source=activity.source,
    )


def _to_response(activity) -> ActivityResponse:
    """Convert activity to full response."""
    return ActivityResponse(
        id=str(activity.id),
        name=activity.name,
        slug=activity.slug,
        short_description=activity.short_description,
        description=activity.description,
        category=activity.category,
        subcategory=activity.subcategory,
        activity_type=activity.activity_type,
        tags=activity.tags,
        location=ActivityLocationSchema(
            name=activity.location.name,
            address=activity.location.address,
            city=activity.location.city,
            state=activity.location.state,
            country=activity.location.country,
            latitude=activity.location.latitude,
            longitude=activity.location.longitude,
            meeting_point=activity.location.meeting_point,
            meeting_point_details=activity.location.meeting_point_details,
        ),
        duration=ActivityDurationSchema(
            minutes=activity.duration.minutes,
            hours=activity.duration.hours,
            days=activity.duration.days,
            display_text=activity.duration.display_text,
            is_flexible=activity.duration.is_flexible,
        ),
        pricing=ActivityPricingSchema(
            currency=activity.pricing.currency,
            adult_price=activity.pricing.adult_price,
            child_price=activity.pricing.child_price,
            infant_price=activity.pricing.infant_price,
            group_price=activity.pricing.group_price,
            private_price=activity.pricing.private_price,
            pricing_type=activity.pricing.pricing_type,
            from_price=activity.pricing.from_price,
            original_price=activity.pricing.original_price,
            discount_percentage=activity.pricing.discount_percentage,
        ),
        capacity=ActivityCapacitySchema(
            min_participants=activity.capacity.min_participants,
            max_participants=activity.capacity.max_participants,
            max_per_booking=activity.capacity.max_per_booking,
        ),
        inclusions=ActivityInclusionsSchema(
            included=activity.inclusions.included,
            excluded=activity.inclusions.excluded,
            bring_items=activity.inclusions.bring_items,
            provided_items=activity.inclusions.provided_items,
        ),
        requirements=ActivityRequirementsSchema(
            min_age=activity.requirements.min_age,
            max_age=activity.requirements.max_age,
            fitness_level=activity.requirements.fitness_level,
            skill_level=activity.requirements.skill_level,
            health_restrictions=activity.requirements.health_restrictions,
            not_suitable_for=activity.requirements.not_suitable_for,
        ),
        policies=ActivityPoliciesSchema(
            cancellation_policy=activity.policies.cancellation_policy,
            cancellation_deadline_hours=activity.policies.cancellation_deadline_hours,
            instant_confirmation=activity.policies.instant_confirmation,
            mobile_ticket=activity.policies.mobile_ticket,
            booking_cutoff_hours=activity.policies.booking_cutoff_hours,
        ),
        highlights=activity.highlights,
        cover_image=activity.cover_image,
        images=activity.images,
        video_url=activity.video_url,
        provider=ActivityProviderSchema(
            vendor_id=activity.provider.vendor_id,
            name=activity.provider.name,
            logo=activity.provider.logo,
            languages=activity.provider.languages,
            is_verified=activity.provider.is_verified,
        ) if activity.provider else None,
        rating=ActivityRatingSchema(
            average=activity.rating.average,
            count=activity.rating.count,
        ),
        source=activity.source,
        external_url=activity.external_url,
        available_languages=activity.available_languages,
        wheelchair_accessible=activity.wheelchair_accessible,
        is_featured=activity.is_featured,
        is_popular=activity.is_popular,
        vendor_id=activity.vendor_id,
        booking_count=activity.booking_count,
        created_at=activity.created_at,
    )

