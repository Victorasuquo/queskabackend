"""
Queska Backend - Experience Card Endpoints
API routes for shareable experience cards
"""

from datetime import date
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from app.api.deps import get_current_active_user, get_current_user_optional
from app.core.exceptions import NotFoundError, ValidationError, ForbiddenError
from app.models.user import User
from app.schemas.base import SuccessResponse
from app.schemas.experience_card import (
    ExperienceCardCreate,
    ExperienceCardUpdate,
    ExperienceCardResponse,
    ExperienceCardPublicResponse,
    ExperienceCardSummary,
    PaginatedCardsResponse,
    PaginatedPublicCardsResponse,
    CardSettingsUpdate,
    UpdateLocationRequest,
    LocationResponse,
    ViewCardRequest,
    ViewCardResponse,
    ShareCardRequest,
    ShareCardResponse,
    CloneCardRequest,
    CloneCardResponse,
    LikeCardResponse,
    SaveCardResponse,
    CardSearchFilters,
    GenerateQRCodeRequest,
    GenerateQRCodeResponse,
    TravelTimeEstimateSchema,
)
from app.services.experience_card_service import experience_card_service

router = APIRouter()


# === My Cards ===

@router.get(
    "/me",
    response_model=PaginatedCardsResponse,
    summary="Get my cards",
    description="Get all experience cards owned by the current user",
)
async def get_my_cards(
    current_user: User = Depends(get_current_active_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    """Get all cards for the logged-in user"""
    cards, total = await experience_card_service.get_user_cards(
        user_id=str(current_user.id),
        skip=skip,
        limit=limit,
    )
    
    return PaginatedCardsResponse(
        data=[
            ExperienceCardSummary(
                id=str(card.id),
                card_code=card.card_code,
                title=card.title,
                cover_image=card.cover_image,
                destination_city=card.destination.city,
                destination_country=card.destination.country,
                start_date=card.dates.start_date,
                end_date=card.dates.end_date,
                total_days=(card.dates.end_date - card.dates.start_date).days + 1,
                travelers_count=card.travelers.total_passengers,
                highlights_count=len(card.highlights),
                view_count=card.stats.view_count,
                is_public=card.settings.is_public,
                is_active=card.settings.is_active,
                created_at=card.created_at,
            )
            for card in cards
        ],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/me/saved",
    response_model=PaginatedCardsResponse,
    summary="Get saved cards",
    description="Get cards saved by the current user",
)
async def get_saved_cards(
    current_user: User = Depends(get_current_active_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    """Get saved cards"""
    cards, total = await experience_card_service.get_saved_cards(
        user_id=str(current_user.id),
        skip=skip,
        limit=limit,
    )
    
    return PaginatedCardsResponse(
        data=[
            ExperienceCardSummary(
                id=str(card.id),
                card_code=card.card_code,
                title=card.title,
                cover_image=card.cover_image,
                destination_city=card.destination.city,
                destination_country=card.destination.country,
                start_date=card.dates.start_date,
                end_date=card.dates.end_date,
                total_days=(card.dates.end_date - card.dates.start_date).days + 1,
                travelers_count=card.travelers.total_passengers,
                highlights_count=len(card.highlights),
                view_count=card.stats.view_count,
                is_public=card.settings.is_public,
                is_active=card.settings.is_active,
                created_at=card.created_at,
            )
            for card in cards
        ],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/me/{card_id}",
    response_model=ExperienceCardResponse,
    summary="Get my card details",
    description="Get full details of a card owned by the current user",
)
async def get_my_card(
    card_id: str,
    current_user: User = Depends(get_current_active_user),
):
    """Get card details (owner only)"""
    try:
        card = await experience_card_service.get_card(card_id)
        
        if card.owner.user_id != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this card"
            )
        
        response_data = card.model_dump(by_alias=True)
        response_data["share_url"] = card.share_url
        response_data["liked_by_count"] = len(card.liked_by)
        response_data["saved_by_count"] = len(card.saved_by)
        response_data["is_liked_by_me"] = str(current_user.id) in card.liked_by
        response_data["is_saved_by_me"] = str(current_user.id) in card.saved_by
        response_data["days_until_trip"] = card.days_until_trip
        response_data["is_trip_ongoing"] = card.is_trip_ongoing
        response_data["is_active"] = card.is_active
        
        return ExperienceCardResponse.model_validate(response_data)
        
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.put(
    "/me/{card_id}",
    response_model=ExperienceCardResponse,
    summary="Update my card",
    description="Update card details",
)
async def update_my_card(
    card_id: str,
    data: ExperienceCardUpdate,
    current_user: User = Depends(get_current_active_user),
):
    """Update card"""
    try:
        card = await experience_card_service.update_card(
            card_id=card_id,
            user_id=str(current_user.id),
            data=data,
        )
        
        response_data = card.model_dump(by_alias=True)
        response_data["share_url"] = card.share_url
        
        return ExperienceCardResponse.model_validate(response_data)
        
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except (ValidationError, ForbiddenError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.put(
    "/me/{card_id}/settings",
    response_model=ExperienceCardResponse,
    summary="Update card settings",
    description="Update card visibility and sharing settings",
)
async def update_card_settings(
    card_id: str,
    settings: CardSettingsUpdate,
    current_user: User = Depends(get_current_active_user),
):
    """Update card settings"""
    try:
        card = await experience_card_service.update_card_settings(
            card_id=card_id,
            user_id=str(current_user.id),
            settings=settings,
        )
        
        response_data = card.model_dump(by_alias=True)
        response_data["share_url"] = card.share_url
        
        return ExperienceCardResponse.model_validate(response_data)
        
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except (ValidationError, ForbiddenError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/me/{card_id}/deactivate",
    response_model=SuccessResponse,
    summary="Deactivate card",
    description="Deactivate a card to stop sharing",
)
async def deactivate_card(
    card_id: str,
    current_user: User = Depends(get_current_active_user),
):
    """Deactivate card"""
    try:
        await experience_card_service.deactivate_card(
            card_id=card_id,
            user_id=str(current_user.id),
        )
        return SuccessResponse(message="Card deactivated successfully")
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ForbiddenError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.delete(
    "/me/{card_id}",
    response_model=SuccessResponse,
    summary="Delete card",
    description="Delete a card",
)
async def delete_card(
    card_id: str,
    current_user: User = Depends(get_current_active_user),
):
    """Delete card"""
    try:
        await experience_card_service.delete_card(
            card_id=card_id,
            user_id=str(current_user.id),
        )
        return SuccessResponse(message="Card deleted successfully")
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ForbiddenError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


# === Location Sharing ===

@router.post(
    "/me/{card_id}/location",
    response_model=LocationResponse,
    summary="Update my location",
    description="Update real-time location on a card for trip tracking",
)
async def update_location(
    card_id: str,
    data: UpdateLocationRequest,
    current_user: User = Depends(get_current_active_user),
):
    """Update real-time location"""
    try:
        card = await experience_card_service.update_owner_location(
            card_id=card_id,
            user_id=str(current_user.id),
            latitude=data.latitude,
            longitude=data.longitude,
            accuracy=data.accuracy,
        )
        return LocationResponse(
            success=True,
            updated_at=card.owner_location.updated_at if card.owner_location else None,
            is_sharing=card.settings.show_real_time_location,
        )
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except (ValidationError, ForbiddenError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/me/{card_id}/location/stop",
    response_model=SuccessResponse,
    summary="Stop location sharing",
    description="Stop sharing location on a card",
)
async def stop_location_sharing(
    card_id: str,
    current_user: User = Depends(get_current_active_user),
):
    """Stop location sharing"""
    try:
        await experience_card_service.stop_location_sharing(
            card_id=card_id,
            user_id=str(current_user.id),
        )
        return SuccessResponse(message="Location sharing stopped")
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ForbiddenError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


# === Share Card ===

@router.post(
    "/me/{card_id}/share",
    response_model=ShareCardResponse,
    summary="Share card",
    description="Share card with others via email, SMS, or link",
)
async def share_card(
    card_id: str,
    data: ShareCardRequest,
    current_user: User = Depends(get_current_active_user),
):
    """Share card"""
    try:
        result = await experience_card_service.share_card(
            card_id=card_id,
            user_id=str(current_user.id),
            data=data,
        )
        return ShareCardResponse(**result)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except (ValidationError, ForbiddenError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "/me/{card_id}/stats",
    response_model=Dict[str, Any],
    summary="Get share stats",
    description="Get sharing statistics for a card",
)
async def get_share_stats(
    card_id: str,
    current_user: User = Depends(get_current_active_user),
):
    """Get share statistics"""
    try:
        stats = await experience_card_service.get_share_stats(
            card_id=card_id,
            user_id=str(current_user.id),
        )
        return stats
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ForbiddenError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


# === QR Code ===

@router.post(
    "/me/{card_id}/qrcode",
    response_model=GenerateQRCodeResponse,
    summary="Generate QR code",
    description="Generate a QR code for the card",
)
async def generate_qr_code(
    card_id: str,
    data: GenerateQRCodeRequest = GenerateQRCodeRequest(),
    current_user: User = Depends(get_current_active_user),
):
    """Generate QR code"""
    try:
        card = await experience_card_service.get_card(card_id)
        
        if card.owner.user_id != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this card"
            )
        
        qr_url = await experience_card_service.generate_qr_code(
            card_id=card_id,
            user_id=str(current_user.id),
            size=data.size,
            include_logo=data.include_logo,
        )
        
        return GenerateQRCodeResponse(
            qr_code_url=qr_url,
            card_code=card.card_code,
            share_url=card.share_url,
        )
        
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# === Public Card View ===

@router.get(
    "/view/{card_code}",
    response_model=ViewCardResponse,
    summary="View card by code",
    description="View a public card by its share code",
)
async def view_card(
    card_code: str,
    request: Request,
    viewer_lat: Optional[float] = Query(None, description="Viewer's latitude"),
    viewer_lng: Optional[float] = Query(None, description="Viewer's longitude"),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """View a shared card"""
    try:
        # Get viewer info
        viewer_ip = request.client.host if request.client else None
        viewer_location = None
        if viewer_lat and viewer_lng:
            viewer_location = {"lat": viewer_lat, "lng": viewer_lng}
        
        card = await experience_card_service.get_card_by_code(
            card_code=card_code,
            record_view=True,
            viewer_id=str(current_user.id) if current_user else None,
            viewer_ip=viewer_ip,
            viewer_location=viewer_location,
        )
        
        # Calculate distance if viewer location provided
        travel_estimate = None
        viewer_distance_km = None
        viewer_message = None
        
        if viewer_lat and viewer_lng:
            estimate = await experience_card_service.get_distance_from_viewer(
                card_code=card_code,
                viewer_lat=viewer_lat,
                viewer_lng=viewer_lng,
            )
            
            if estimate:
                viewer_distance_km = estimate.driving_distance_km
                
                # Format friendly message
                if viewer_distance_km < 10:
                    viewer_message = f"Just {viewer_distance_km:.1f} km away!"
                elif viewer_distance_km < 50:
                    viewer_message = f"{viewer_distance_km:.0f} km away"
                elif estimate.driving_time_minutes:
                    hours = estimate.driving_time_minutes // 60
                    if hours > 0:
                        viewer_message = f"About {hours} hour{'s' if hours > 1 else ''} drive"
                    else:
                        viewer_message = f"About {estimate.driving_time_minutes} minutes away"
                
                travel_estimate = TravelTimeEstimateSchema(
                    driving_time_minutes=estimate.driving_time_minutes,
                    driving_distance_km=estimate.driving_distance_km,
                    flight_time_minutes=estimate.flight_time_minutes,
                    friendly_distance=viewer_message or "",
                )
        
        # Build public response
        public_data = card.get_public_data()
        
        # Add computed fields
        is_owner = current_user and str(current_user.id) == card.owner.user_id
        
        card_response = ExperienceCardPublicResponse(
            card_code=card.card_code,
            share_url=card.share_url,
            owner={"name": card.owner.name, "avatar_url": card.owner.avatar_url} if card.settings.show_owner_name else None,
            title=card.title,
            description=card.description,
            tagline=card.tagline,
            cover_image=card.cover_image,
            images=card.images[:4],
            destination_name=card.destination.name,
            destination_city=card.destination.city,
            destination_country=card.destination.country,
            start_date=card.dates.start_date,
            end_date=card.dates.end_date,
            total_days=(card.dates.end_date - card.dates.start_date).days + 1,
            travelers_count=card.travelers.total_passengers,
            highlights=[h.model_dump() for h in card.highlights],
            total_price=card.pricing.grand_total if card.settings.show_prices and card.pricing else None,
            price_per_person=card.pricing.price_per_person if card.settings.show_prices and card.pricing else None,
            currency=card.pricing.currency if card.pricing else "NGN",
            view_count=card.stats.view_count,
            share_count=card.stats.share_count,
            can_clone=card.settings.allow_cloning,
            tags=card.tags,
            travel_tips=card.ai_travel_tips,
            days_until_trip=card.days_until_trip,
            is_trip_ongoing=card.is_trip_ongoing,
            trip_status="ongoing" if card.is_trip_ongoing else ("upcoming" if card.days_until_trip > 0 else "completed"),
        )
        
        return ViewCardResponse(
            card=card_response,
            travel_estimate=travel_estimate,
            viewer_distance_km=viewer_distance_km,
            viewer_message=viewer_message,
        )
        
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ForbiddenError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


# === Social Interactions ===

@router.post(
    "/{card_code}/like",
    response_model=LikeCardResponse,
    summary="Like card",
    description="Like or unlike a card",
)
async def like_card(
    card_code: str,
    current_user: User = Depends(get_current_active_user),
):
    """Like/unlike a card"""
    try:
        result = await experience_card_service.like_card(
            card_code=card_code,
            user_id=str(current_user.id),
        )
        return LikeCardResponse(**result)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post(
    "/{card_code}/save",
    response_model=SaveCardResponse,
    summary="Save card",
    description="Save or unsave a card to your collection",
)
async def save_card(
    card_code: str,
    current_user: User = Depends(get_current_active_user),
):
    """Save/unsave a card"""
    try:
        result = await experience_card_service.save_card(
            card_code=card_code,
            user_id=str(current_user.id),
        )
        return SaveCardResponse(**result)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# === Clone ===

@router.post(
    "/{card_code}/clone",
    response_model=CloneCardResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Clone card",
    description="Clone an experience from a card",
)
async def clone_card(
    card_code: str,
    data: CloneCardRequest,
    current_user: User = Depends(get_current_active_user),
):
    """Clone experience from card"""
    try:
        result = await experience_card_service.clone_card(
            card_code=card_code,
            user_id=str(current_user.id),
            data=data,
            user_name=f"{current_user.first_name} {current_user.last_name}",
        )
        return CloneCardResponse(**result)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ForbiddenError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


# === Discovery ===

@router.get(
    "/discover",
    response_model=PaginatedPublicCardsResponse,
    summary="Discover public cards",
    description="Browse public experience cards",
)
async def discover_cards(
    destination_city: Optional[str] = Query(None),
    destination_country: Optional[str] = Query(None),
    start_date_from: Optional[date] = Query(None),
    start_date_to: Optional[date] = Query(None),
    min_travelers: Optional[int] = Query(None),
    max_travelers: Optional[int] = Query(None),
    tags: Optional[List[str]] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    """Discover public cards"""
    filters = CardSearchFilters(
        destination_city=destination_city,
        destination_country=destination_country,
        start_date_from=start_date_from,
        start_date_to=start_date_to,
        min_travelers=min_travelers,
        max_travelers=max_travelers,
        tags=tags,
    )
    
    cards, total = await experience_card_service.search_public_cards(
        filters=filters,
        skip=skip,
        limit=limit,
    )
    
    return PaginatedPublicCardsResponse(
        data=[
            ExperienceCardPublicResponse(
                card_code=card.card_code,
                share_url=card.share_url,
                owner={"name": card.owner.name} if card.settings.show_owner_name else None,
                title=card.title,
                description=card.description,
                tagline=card.tagline,
                cover_image=card.cover_image,
                images=card.images[:2],
                destination_name=card.destination.name,
                destination_city=card.destination.city,
                destination_country=card.destination.country,
                start_date=card.dates.start_date,
                end_date=card.dates.end_date,
                total_days=(card.dates.end_date - card.dates.start_date).days + 1,
                travelers_count=card.travelers.total_passengers,
                highlights=[h.model_dump() for h in card.highlights[:3]],
                view_count=card.stats.view_count,
                share_count=card.stats.share_count,
                can_clone=card.settings.allow_cloning,
                tags=card.tags,
                days_until_trip=card.days_until_trip,
                is_trip_ongoing=card.is_trip_ongoing,
                trip_status="ongoing" if card.is_trip_ongoing else ("upcoming" if card.days_until_trip > 0 else "completed"),
            )
            for card in cards
        ],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/featured",
    response_model=List[ExperienceCardPublicResponse],
    summary="Get featured cards",
    description="Get featured public experience cards",
)
async def get_featured_cards(
    limit: int = Query(10, ge=1, le=20),
):
    """Get featured cards"""
    cards = await experience_card_service.get_featured_cards(limit=limit)
    
    return [
        ExperienceCardPublicResponse(
            card_code=card.card_code,
            share_url=card.share_url,
            owner={"name": card.owner.name} if card.settings.show_owner_name else None,
            title=card.title,
            description=card.description,
            tagline=card.tagline,
            cover_image=card.cover_image,
            images=card.images[:2],
            destination_name=card.destination.name,
            destination_city=card.destination.city,
            destination_country=card.destination.country,
            start_date=card.dates.start_date,
            end_date=card.dates.end_date,
            total_days=(card.dates.end_date - card.dates.start_date).days + 1,
            travelers_count=card.travelers.total_passengers,
            highlights=[h.model_dump() for h in card.highlights[:3]],
            view_count=card.stats.view_count,
            share_count=card.stats.share_count,
            can_clone=card.settings.allow_cloning,
            tags=card.tags,
            days_until_trip=card.days_until_trip,
            is_trip_ongoing=card.is_trip_ongoing,
            trip_status="ongoing" if card.is_trip_ongoing else ("upcoming" if card.days_until_trip > 0 else "completed"),
        )
        for card in cards
    ]


@router.get(
    "/nearby",
    response_model=List[ExperienceCardPublicResponse],
    summary="Get nearby cards",
    description="Get cards for destinations near a location",
)
async def get_nearby_cards(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    max_distance_km: float = Query(100, ge=1, le=500),
    limit: int = Query(20, ge=1, le=50),
):
    """Get cards for nearby destinations"""
    cards = await experience_card_service.get_nearby_cards(
        latitude=latitude,
        longitude=longitude,
        max_distance_km=max_distance_km,
        limit=limit,
    )
    
    return [
        ExperienceCardPublicResponse(
            card_code=card.card_code,
            share_url=card.share_url,
            owner={"name": card.owner.name} if card.settings.show_owner_name else None,
            title=card.title,
            description=card.description,
            tagline=card.tagline,
            cover_image=card.cover_image,
            images=card.images[:2],
            destination_name=card.destination.name,
            destination_city=card.destination.city,
            destination_country=card.destination.country,
            start_date=card.dates.start_date,
            end_date=card.dates.end_date,
            total_days=(card.dates.end_date - card.dates.start_date).days + 1,
            travelers_count=card.travelers.total_passengers,
            highlights=[h.model_dump() for h in card.highlights[:3]],
            view_count=card.stats.view_count,
            share_count=card.stats.share_count,
            can_clone=card.settings.allow_cloning,
            tags=card.tags,
            days_until_trip=card.days_until_trip,
            is_trip_ongoing=card.is_trip_ongoing,
            trip_status="ongoing" if card.is_trip_ongoing else ("upcoming" if card.days_until_trip > 0 else "completed"),
        )
        for card in cards
    ]

