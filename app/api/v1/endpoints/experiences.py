"""
Queska Backend - Experience Endpoints
API routes for experience creation, management, and booking flow
"""

from datetime import date
from typing import Any, Dict, List, Optional

from beanie import PydanticObjectId
from fastapi import APIRouter, Depends, HTTPException, Query, status, Request

from app.api.deps import get_current_active_user, get_current_user_optional
from app.core.constants import ExperienceStatus
from app.core.exceptions import NotFoundError, ValidationError, ForbiddenError
from app.models.user import User
from app.schemas.base import SuccessResponse
from app.schemas.experience import (
    ExperienceCreate,
    ExperienceUpdate,
    ExperienceResponse,
    ExperienceSummaryResponse,
    PaginatedExperiencesResponse,
    ExperienceItemCreate,
    ExperienceItemUpdate,
    ExperienceItemResponse,
    AddAccommodationRequest,
    AddRideRequest,
    AddEventRequest,
    AddActivityRequest,
    AddDiningRequest,
    AddPlaceRequest,
    AddFlightRequest,
    ApplyDiscountRequest,
    CheckoutRequest,
    CheckoutResponse,
    CloneExperienceRequest,
    CloneExperienceResponse,
    ExperienceSharingSettings,
    ExperienceSharingResponse,
    ExperiencePricingResponse,
    ItineraryDayResponse,
    ExperienceFilters,
)
from app.services.experience_service import experience_service

router = APIRouter()


# === Experience CRUD ===

@router.post(
    "/",
    response_model=ExperienceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create new experience",
    description="Create a new travel experience (Step 1 of the experience flow)",
)
async def create_experience(
    data: ExperienceCreate,
    current_user: User = Depends(get_current_active_user),
):
    """
    Create a new experience with:
    - Destination
    - Travel dates
    - Number of travelers
    - Preferences/interests
    """
    try:
        experience = await experience_service.create_experience(
            user_id=str(current_user.id),
            data=data,
            user_name=f"{current_user.first_name} {current_user.last_name}",
            user_email=current_user.email,
        )
        return ExperienceResponse.model_validate(experience.model_dump(by_alias=True))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "/",
    response_model=PaginatedExperiencesResponse,
    summary="Get my experiences",
    description="Get all experiences for the current user",
)
async def get_my_experiences(
    current_user: User = Depends(get_current_active_user),
    status_filter: Optional[ExperienceStatus] = Query(None, alias="status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    """Get all experiences for the logged-in user"""
    experiences, total = await experience_service.get_user_experiences(
        user_id=str(current_user.id),
        status=status_filter,
        skip=skip,
        limit=limit,
    )
    
    return PaginatedExperiencesResponse(
        data=[
            ExperienceSummaryResponse(
                id=str(exp.id),
                title=exp.title,
                cover_image=exp.cover_image,
                destination_city=exp.destination.city,
                destination_country=exp.destination.country,
                start_date=exp.dates.start_date,
                end_date=exp.dates.end_date,
                total_days=exp.total_days,
                travelers_count=exp.travelers.total_passengers,
                items_count=len(exp.items),
                total_price=exp.pricing.grand_total,
                currency=exp.pricing.currency,
                status=exp.status,
                card_generated=exp.card_generated,
                share_code=exp.sharing.share_code,
                created_at=exp.created_at,
            )
            for exp in experiences
        ],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/upcoming",
    response_model=List[ExperienceSummaryResponse],
    summary="Get upcoming experiences",
    description="Get upcoming experiences for the current user",
)
async def get_upcoming_experiences(
    current_user: User = Depends(get_current_active_user),
    limit: int = Query(5, ge=1, le=20),
):
    """Get upcoming confirmed experiences"""
    experiences, _ = await experience_service.get_user_experiences(
        user_id=str(current_user.id),
        status=ExperienceStatus.CONFIRMED,
        limit=limit,
    )
    
    # Filter to upcoming only
    upcoming = [
        exp for exp in experiences 
        if exp.dates.start_date >= date.today()
    ]
    
    return [
        ExperienceSummaryResponse(
            id=str(exp.id),
            title=exp.title,
            cover_image=exp.cover_image,
            destination_city=exp.destination.city,
            destination_country=exp.destination.country,
            start_date=exp.dates.start_date,
            end_date=exp.dates.end_date,
            total_days=exp.total_days,
            travelers_count=exp.travelers.total_passengers,
            items_count=len(exp.items),
            total_price=exp.pricing.grand_total,
            currency=exp.pricing.currency,
            status=exp.status,
            card_generated=exp.card_generated,
            share_code=exp.sharing.share_code,
            created_at=exp.created_at,
        )
        for exp in upcoming[:limit]
    ]


@router.get(
    "/{experience_id}",
    response_model=ExperienceResponse,
    summary="Get experience details",
    description="Get full details of a specific experience",
)
async def get_experience(
    experience_id: str,
    current_user: User = Depends(get_current_active_user),
):
    """Get experience by ID"""
    try:
        experience = await experience_service.get_experience(
            experience_id=experience_id,
            user_id=str(current_user.id),
        )
        
        # Verify ownership
        if experience.user_id != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this experience"
            )
        
        return ExperienceResponse.model_validate(experience.model_dump(by_alias=True))
        
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.put(
    "/{experience_id}",
    response_model=ExperienceResponse,
    summary="Update experience",
    description="Update experience details (only draft/pending experiences)",
)
async def update_experience(
    experience_id: str,
    data: ExperienceUpdate,
    current_user: User = Depends(get_current_active_user),
):
    """Update experience details"""
    try:
        experience = await experience_service.update_experience(
            experience_id=experience_id,
            user_id=str(current_user.id),
            data=data,
        )
        return ExperienceResponse.model_validate(experience.model_dump(by_alias=True))
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except (ValidationError, ForbiddenError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete(
    "/{experience_id}",
    response_model=SuccessResponse,
    summary="Delete experience",
    description="Delete an experience (cannot delete confirmed experiences)",
)
async def delete_experience(
    experience_id: str,
    current_user: User = Depends(get_current_active_user),
):
    """Delete experience"""
    try:
        await experience_service.delete_experience(
            experience_id=experience_id,
            user_id=str(current_user.id),
        )
        return SuccessResponse(message="Experience deleted successfully")
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except (ValidationError, ForbiddenError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# === Add Items to Experience ===

@router.post(
    "/{experience_id}/items",
    response_model=ExperienceResponse,
    summary="Add generic item",
    description="Add a generic item to the experience",
)
async def add_item(
    experience_id: str,
    data: ExperienceItemCreate,
    current_user: User = Depends(get_current_active_user),
):
    """Add any type of item to experience"""
    try:
        experience = await experience_service.add_item(
            experience_id=experience_id,
            user_id=str(current_user.id),
            item_data=data,
        )
        return ExperienceResponse.model_validate(experience.model_dump(by_alias=True))
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except (ValidationError, ForbiddenError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/{experience_id}/items/accommodation",
    response_model=ExperienceResponse,
    summary="Add accommodation",
    description="Add hotel/accommodation to the experience",
)
async def add_accommodation(
    experience_id: str,
    data: AddAccommodationRequest,
    current_user: User = Depends(get_current_active_user),
):
    """Add hotel/accommodation"""
    try:
        experience = await experience_service.add_accommodation(
            experience_id=experience_id,
            user_id=str(current_user.id),
            data=data,
        )
        return ExperienceResponse.model_validate(experience.model_dump(by_alias=True))
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except (ValidationError, ForbiddenError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/{experience_id}/items/ride",
    response_model=ExperienceResponse,
    summary="Add ride",
    description="Add ride/transportation to the experience",
)
async def add_ride(
    experience_id: str,
    data: AddRideRequest,
    current_user: User = Depends(get_current_active_user),
):
    """Add ride/transportation"""
    try:
        experience = await experience_service.add_ride(
            experience_id=experience_id,
            user_id=str(current_user.id),
            data=data,
        )
        return ExperienceResponse.model_validate(experience.model_dump(by_alias=True))
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except (ValidationError, ForbiddenError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/{experience_id}/items/event",
    response_model=ExperienceResponse,
    summary="Add event",
    description="Add event to the experience",
)
async def add_event(
    experience_id: str,
    data: AddEventRequest,
    current_user: User = Depends(get_current_active_user),
):
    """Add event"""
    try:
        experience = await experience_service.add_event(
            experience_id=experience_id,
            user_id=str(current_user.id),
            data=data,
        )
        return ExperienceResponse.model_validate(experience.model_dump(by_alias=True))
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except (ValidationError, ForbiddenError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/{experience_id}/items/activity",
    response_model=ExperienceResponse,
    summary="Add activity",
    description="Add activity to the experience",
)
async def add_activity(
    experience_id: str,
    data: AddActivityRequest,
    current_user: User = Depends(get_current_active_user),
):
    """Add activity"""
    try:
        experience = await experience_service.add_activity(
            experience_id=experience_id,
            user_id=str(current_user.id),
            data=data,
        )
        return ExperienceResponse.model_validate(experience.model_dump(by_alias=True))
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except (ValidationError, ForbiddenError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/{experience_id}/items/dining",
    response_model=ExperienceResponse,
    summary="Add dining",
    description="Add restaurant/dining to the experience",
)
async def add_dining(
    experience_id: str,
    data: AddDiningRequest,
    current_user: User = Depends(get_current_active_user),
):
    """Add dining"""
    try:
        experience = await experience_service.add_dining(
            experience_id=experience_id,
            user_id=str(current_user.id),
            data=data,
        )
        return ExperienceResponse.model_validate(experience.model_dump(by_alias=True))
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except (ValidationError, ForbiddenError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/{experience_id}/items/place",
    response_model=ExperienceResponse,
    summary="Add place",
    description="Add place to visit to the experience",
)
async def add_place(
    experience_id: str,
    data: AddPlaceRequest,
    current_user: User = Depends(get_current_active_user),
):
    """Add place to visit"""
    try:
        experience = await experience_service.add_place(
            experience_id=experience_id,
            user_id=str(current_user.id),
            data=data,
        )
        return ExperienceResponse.model_validate(experience.model_dump(by_alias=True))
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except (ValidationError, ForbiddenError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/{experience_id}/items/flight",
    response_model=ExperienceResponse,
    summary="Add flight",
    description="Add flight to the experience",
)
async def add_flight(
    experience_id: str,
    data: AddFlightRequest,
    current_user: User = Depends(get_current_active_user),
):
    """Add flight"""
    try:
        experience = await experience_service.add_flight(
            experience_id=experience_id,
            user_id=str(current_user.id),
            data=data,
        )
        return ExperienceResponse.model_validate(experience.model_dump(by_alias=True))
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except (ValidationError, ForbiddenError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.put(
    "/{experience_id}/items/{item_id}",
    response_model=ExperienceResponse,
    summary="Update item",
    description="Update an item in the experience",
)
async def update_item(
    experience_id: str,
    item_id: str,
    data: ExperienceItemUpdate,
    current_user: User = Depends(get_current_active_user),
):
    """Update item"""
    try:
        experience = await experience_service.update_item(
            experience_id=experience_id,
            user_id=str(current_user.id),
            item_id=item_id,
            data=data,
        )
        return ExperienceResponse.model_validate(experience.model_dump(by_alias=True))
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except (ValidationError, ForbiddenError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete(
    "/{experience_id}/items/{item_id}",
    response_model=ExperienceResponse,
    summary="Remove item",
    description="Remove an item from the experience",
)
async def remove_item(
    experience_id: str,
    item_id: str,
    current_user: User = Depends(get_current_active_user),
):
    """Remove item"""
    try:
        experience = await experience_service.remove_item(
            experience_id=experience_id,
            user_id=str(current_user.id),
            item_id=item_id,
        )
        return ExperienceResponse.model_validate(experience.model_dump(by_alias=True))
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except (ValidationError, ForbiddenError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.put(
    "/{experience_id}/items/reorder",
    response_model=ExperienceResponse,
    summary="Reorder items",
    description="Reorder items in the experience",
)
async def reorder_items(
    experience_id: str,
    item_order: List[str],
    current_user: User = Depends(get_current_active_user),
):
    """Reorder items in the experience"""
    try:
        experience = await experience_service.reorder_items(
            experience_id=experience_id,
            user_id=str(current_user.id),
            item_order=item_order,
        )
        return ExperienceResponse.model_validate(experience.model_dump(by_alias=True))
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except (ValidationError, ForbiddenError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# === Itinerary ===

@router.get(
    "/{experience_id}/itinerary",
    response_model=List[ItineraryDayResponse],
    summary="Get itinerary",
    description="Get the day-by-day itinerary for an experience",
)
async def get_itinerary(
    experience_id: str,
    current_user: User = Depends(get_current_active_user),
):
    """Get experience itinerary"""
    try:
        experience = await experience_service.get_experience(
            experience_id=experience_id,
            user_id=str(current_user.id),
        )
        
        if experience.user_id != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this experience"
            )
        
        return [
            ItineraryDayResponse.model_validate(day.model_dump())
            for day in experience.itinerary
        ]
        
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# === Pricing ===

@router.get(
    "/{experience_id}/pricing",
    response_model=ExperiencePricingResponse,
    summary="Get pricing",
    description="Get pricing breakdown for an experience",
)
async def get_pricing(
    experience_id: str,
    current_user: User = Depends(get_current_active_user),
):
    """Get experience pricing breakdown"""
    try:
        experience = await experience_service.get_experience(
            experience_id=experience_id,
            user_id=str(current_user.id),
        )
        
        if experience.user_id != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this experience"
            )
        
        return ExperiencePricingResponse.model_validate(experience.pricing.model_dump())
        
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post(
    "/{experience_id}/discount",
    response_model=ExperiencePricingResponse,
    summary="Apply discount",
    description="Apply a discount code to the experience",
)
async def apply_discount(
    experience_id: str,
    data: ApplyDiscountRequest,
    current_user: User = Depends(get_current_active_user),
):
    """Apply discount code"""
    try:
        experience = await experience_service.apply_discount(
            experience_id=experience_id,
            user_id=str(current_user.id),
            discount_code=data.discount_code,
        )
        return ExperiencePricingResponse.model_validate(experience.pricing.model_dump())
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except (ValidationError, ForbiddenError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# === Checkout & Payment ===

@router.post(
    "/{experience_id}/checkout",
    response_model=CheckoutResponse,
    summary="Checkout",
    description="Submit experience for checkout and get payment URL",
)
async def checkout(
    experience_id: str,
    data: CheckoutRequest,
    current_user: User = Depends(get_current_active_user),
):
    """Submit experience for checkout"""
    try:
        result = await experience_service.checkout(
            experience_id=experience_id,
            user_id=str(current_user.id),
            data=data,
        )
        return CheckoutResponse(**result)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except (ValidationError, ForbiddenError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/{experience_id}/confirm-payment",
    response_model=ExperienceResponse,
    summary="Confirm payment",
    description="Confirm payment and generate experience card (webhook endpoint)",
)
async def confirm_payment(
    experience_id: str,
    payment_reference: str,
    payment_data: Dict[str, Any] = {},
):
    """Confirm payment - called by payment webhook"""
    try:
        experience = await experience_service.confirm_payment(
            experience_id=experience_id,
            payment_reference=payment_reference,
            payment_data=payment_data,
        )
        return ExperienceResponse.model_validate(experience.model_dump(by_alias=True))
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# === Sharing ===

@router.get(
    "/{experience_id}/sharing",
    response_model=ExperienceSharingResponse,
    summary="Get sharing info",
    description="Get sharing settings and stats for an experience",
)
async def get_sharing_info(
    experience_id: str,
    current_user: User = Depends(get_current_active_user),
):
    """Get sharing info"""
    try:
        experience = await experience_service.get_experience(
            experience_id=experience_id,
            user_id=str(current_user.id),
        )
        
        if experience.user_id != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this experience"
            )
        
        return ExperienceSharingResponse.model_validate(experience.sharing.model_dump())
        
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.put(
    "/{experience_id}/sharing",
    response_model=ExperienceSharingResponse,
    summary="Update sharing settings",
    description="Update sharing settings for an experience",
)
async def update_sharing_settings(
    experience_id: str,
    settings: ExperienceSharingSettings,
    current_user: User = Depends(get_current_active_user),
):
    """Update sharing settings"""
    try:
        experience = await experience_service.update_sharing_settings(
            experience_id=experience_id,
            user_id=str(current_user.id),
            settings=settings,
        )
        return ExperienceSharingResponse.model_validate(experience.sharing.model_dump())
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except (ValidationError, ForbiddenError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# === Clone ===

@router.post(
    "/clone",
    response_model=CloneExperienceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Clone experience from share code",
    description="Clone an experience from a shared card code",
)
async def clone_experience(
    data: CloneExperienceRequest,
    current_user: User = Depends(get_current_active_user),
):
    """Clone an experience from a share code"""
    try:
        from app.models.experience import TravelGroup
        
        travelers = None
        if data.travelers:
            travelers = TravelGroup(
                adults=data.travelers.adults,
                children=data.travelers.children,
                infants=data.travelers.infants,
                total_passengers=data.travelers.adults + data.travelers.children + data.travelers.infants,
            )
        
        experience = await experience_service.clone_from_card(
            user_id=str(current_user.id),
            share_code=data.share_code,
            new_start_date=data.new_start_date,
            travelers=travelers,
            user_name=f"{current_user.first_name} {current_user.last_name}",
        )
        
        return CloneExperienceResponse(
            new_experience_id=str(experience.id),
            original_experience_id=experience.cloned_from_id or "",
            original_card_code=data.share_code,
            status=experience.status,
            requires_payment=True,
            estimated_total=experience.pricing.grand_total,
            currency=experience.pricing.currency,
        )
        
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ForbiddenError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


# === Public View ===

@router.get(
    "/shared/{share_code}",
    response_model=ExperienceResponse,
    summary="View shared experience",
    description="View a publicly shared experience by share code",
)
async def view_shared_experience(
    share_code: str,
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """View a shared experience"""
    try:
        experience = await experience_service.get_experience_by_share_code(
            share_code=share_code,
        )
        
        # Return limited data for non-owners
        response_data = experience.model_dump(by_alias=True)
        
        # Hide sensitive info if not owner
        if not current_user or str(current_user.id) != experience.user_id:
            if experience.sharing.hide_prices:
                response_data["pricing"] = None
            if experience.sharing.hide_personal_details:
                response_data["user_email"] = None
        
        return ExperienceResponse.model_validate(response_data)
        
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ForbiddenError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

