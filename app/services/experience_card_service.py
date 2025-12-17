"""
Queska Backend - Experience Card Service
Business logic for shareable experience cards
"""

from datetime import datetime, date, timedelta
from typing import Any, Dict, List, Optional, Tuple
import secrets
import string
import qrcode
import io
import base64

from beanie import PydanticObjectId
from loguru import logger

from app.core.constants import ExperienceStatus
from app.core.exceptions import (
    NotFoundError,
    ValidationError,
    ForbiddenError,
)
from app.models.experience import Experience
from app.models.experience_card import (
    ExperienceCard,
    CardOwner,
    CardHighlight,
    CardLocation,
    CardSettings,
    CardStats,
    CardInteraction,
    TravelTimeEstimate,
)
from app.schemas.experience_card import (
    ExperienceCardCreate,
    ExperienceCardUpdate,
    CardSettingsUpdate,
    UpdateLocationRequest,
    ShareCardRequest,
    CloneCardRequest,
    CardSearchFilters,
)


class ExperienceCardService:
    """
    Service for managing experience cards.
    
    Experience cards are generated after payment and allow:
    - Sharing the experience with others via unique code/link
    - Real-time location tracking of travelers
    - Distance/time estimation from viewer's location
    - Cloning by other users
    - Social features (like, save, share)
    """

    # === Card Generation ===

    async def generate_card(
        self,
        experience_id: str,
        settings: Optional[CardSettings] = None,
        include_itinerary: bool = False,
    ) -> ExperienceCard:
        """Generate an experience card from a confirmed experience"""
        
        experience = await Experience.get(PydanticObjectId(experience_id))
        if not experience:
            raise NotFoundError(f"Experience {experience_id} not found")
        
        if experience.status != ExperienceStatus.CONFIRMED:
            raise ValidationError("Can only generate cards for confirmed experiences")
        
        if experience.card_generated:
            # Return existing card
            existing = await ExperienceCard.find_one({"experience_id": experience_id})
            if existing:
                return existing
        
        # Create card from experience
        card = await ExperienceCard.create_from_experience(experience)
        
        # Apply custom settings
        if settings:
            card.settings = settings
        
        # Include itinerary if requested
        if include_itinerary:
            card.include_full_itinerary = True
            card.itinerary = experience.itinerary
        
        # Generate QR code
        card.qr_code_url = await self._generate_qr_code(card.share_url)
        
        await card.insert()
        
        # Update experience with card info
        experience.experience_card_id = str(card.id)
        experience.card_generated = True
        experience.sharing.share_code = card.card_code
        experience.sharing.share_url = card.share_url
        await experience.save()
        
        logger.info(f"Card {card.card_code} generated for experience {experience_id}")
        
        return card

    # === Get Cards ===

    async def get_card(self, card_id: str) -> ExperienceCard:
        """Get card by ID"""
        try:
            card = await ExperienceCard.get(PydanticObjectId(card_id))
        except Exception:
            raise NotFoundError(f"Card {card_id} not found")
        
        if not card or card.is_deleted:
            raise NotFoundError(f"Card {card_id} not found")
        
        return card

    async def get_card_by_code(
        self,
        card_code: str,
        record_view: bool = True,
        viewer_id: Optional[str] = None,
        viewer_ip: Optional[str] = None,
        viewer_location: Optional[Dict[str, float]] = None,
    ) -> ExperienceCard:
        """Get card by share code"""
        
        card = await ExperienceCard.find_one({"card_code": card_code})
        
        if not card or card.is_deleted:
            raise NotFoundError(f"Card with code {card_code} not found")
        
        if not card.is_active:
            raise ForbiddenError("This card is no longer active")
        
        # Record view
        if record_view:
            card.record_view(
                user_id=viewer_id,
                ip_address=viewer_ip,
                location=viewer_location,
            )
            await card.save()
        
        return card

    async def get_user_cards(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 20,
    ) -> Tuple[List[ExperienceCard], int]:
        """Get all cards owned by a user"""
        
        query = {
            "owner.user_id": user_id,
            "is_deleted": False,
        }
        
        total = await ExperienceCard.find(query).count()
        cards = await ExperienceCard.find(query)\
            .sort("-created_at")\
            .skip(skip)\
            .limit(limit)\
            .to_list()
        
        return cards, total

    async def get_saved_cards(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 20,
    ) -> Tuple[List[ExperienceCard], int]:
        """Get cards saved by a user"""
        
        query = {
            "saved_by": user_id,
            "is_deleted": False,
            "settings.is_active": True,
        }
        
        total = await ExperienceCard.find(query).count()
        cards = await ExperienceCard.find(query)\
            .sort("-created_at")\
            .skip(skip)\
            .limit(limit)\
            .to_list()
        
        return cards, total

    # === Update Card ===

    async def update_card(
        self,
        card_id: str,
        user_id: str,
        data: ExperienceCardUpdate,
    ) -> ExperienceCard:
        """Update card details"""
        
        card = await self._get_and_verify_ownership(card_id, user_id)
        
        update_data = data.model_dump(exclude_unset=True)
        
        # Handle settings separately
        if "settings" in update_data and update_data["settings"]:
            for key, value in update_data["settings"].items():
                if value is not None:
                    setattr(card.settings, key, value)
            del update_data["settings"]
        
        for key, value in update_data.items():
            setattr(card, key, value)
        
        card.updated_at = datetime.utcnow()
        await card.save()
        
        return card

    async def update_card_settings(
        self,
        card_id: str,
        user_id: str,
        settings: CardSettingsUpdate,
    ) -> ExperienceCard:
        """Update card settings"""
        
        card = await self._get_and_verify_ownership(card_id, user_id)
        
        update_data = settings.model_dump(exclude_unset=True)
        
        for key, value in update_data.items():
            if value is not None:
                setattr(card.settings, key, value)
        
        await card.save()
        
        return card

    async def deactivate_card(
        self,
        card_id: str,
        user_id: str,
    ) -> ExperienceCard:
        """Deactivate a card (stop sharing)"""
        
        card = await self._get_and_verify_ownership(card_id, user_id)
        
        card.settings.is_active = False
        await card.save()
        
        return card

    async def delete_card(
        self,
        card_id: str,
        user_id: str,
    ) -> bool:
        """Soft delete a card"""
        
        card = await self._get_and_verify_ownership(card_id, user_id)
        
        await card.soft_delete()
        
        # Update experience
        experience = await Experience.get(PydanticObjectId(card.experience_id))
        if experience:
            experience.card_generated = False
            experience.experience_card_id = None
            await experience.save()
        
        return True

    # === Real-time Location ===

    async def update_owner_location(
        self,
        card_id: str,
        user_id: str,
        latitude: float,
        longitude: float,
        accuracy: Optional[float] = None,
    ) -> ExperienceCard:
        """Update owner's real-time location on card"""
        
        card = await self._get_and_verify_ownership(card_id, user_id)
        
        if not card.settings.show_real_time_location:
            raise ValidationError("Real-time location sharing is disabled for this card")
        
        card.update_owner_location(latitude, longitude, accuracy)
        await card.save()
        
        return card

    async def stop_location_sharing(
        self,
        card_id: str,
        user_id: str,
    ) -> ExperienceCard:
        """Stop sharing location on a card"""
        
        card = await self._get_and_verify_ownership(card_id, user_id)
        
        card.owner_location = None
        card.settings.show_real_time_location = False
        await card.save()
        
        return card

    async def get_distance_from_viewer(
        self,
        card_code: str,
        viewer_lat: float,
        viewer_lng: float,
    ) -> Optional[TravelTimeEstimate]:
        """Calculate distance from viewer's location to destination"""
        
        card = await self.get_card_by_code(card_code, record_view=False)
        
        estimate = card.calculate_distance_from(viewer_lat, viewer_lng)
        
        return estimate

    # === Sharing ===

    async def share_card(
        self,
        card_id: str,
        user_id: str,
        data: ShareCardRequest,
    ) -> Dict[str, Any]:
        """Share card with others"""
        
        card = await self._get_and_verify_ownership(card_id, user_id)
        
        if not card.settings.is_active:
            raise ValidationError("Cannot share an inactive card")
        
        # Record share
        card.record_share(user_id)
        
        # Add recipients to shared list
        if data.emails:
            card.sharing.shared_with_emails.extend(data.emails)
        
        await card.save()
        
        # TODO: Send notification emails/SMS to recipients
        # For now, just return the share info
        
        return {
            "share_url": card.share_url,
            "card_code": card.card_code,
            "shared_with_count": len(data.emails) + len(data.phone_numbers),
            "share_method": data.share_via,
        }

    async def get_share_stats(
        self,
        card_id: str,
        user_id: str,
    ) -> Dict[str, Any]:
        """Get sharing statistics for a card"""
        
        card = await self._get_and_verify_ownership(card_id, user_id)
        
        return {
            "view_count": card.stats.view_count,
            "unique_viewers": card.stats.unique_viewers,
            "share_count": card.stats.share_count,
            "clone_count": card.stats.clone_count,
            "save_count": card.stats.save_count,
            "liked_count": len(card.liked_by),
            "viewer_countries": card.stats.viewer_countries,
            "recent_interactions": [
                {
                    "action": i.action,
                    "timestamp": i.timestamp.isoformat(),
                }
                for i in card.recent_interactions[:10]
            ],
        }

    # === Social Features ===

    async def like_card(
        self,
        card_code: str,
        user_id: str,
    ) -> Dict[str, Any]:
        """Like a card"""
        
        card = await self.get_card_by_code(card_code, record_view=False)
        
        if user_id in card.liked_by:
            # Unlike
            card.liked_by.remove(user_id)
            is_liked = False
        else:
            # Like
            card.liked_by.append(user_id)
            is_liked = True
        
        await card.save()
        
        return {
            "is_liked": is_liked,
            "total_likes": len(card.liked_by),
        }

    async def save_card(
        self,
        card_code: str,
        user_id: str,
    ) -> Dict[str, Any]:
        """Save a card to user's collection"""
        
        card = await self.get_card_by_code(card_code, record_view=False)
        
        if user_id in card.saved_by:
            # Unsave
            card.saved_by.remove(user_id)
            card.stats.save_count = max(0, card.stats.save_count - 1)
            is_saved = False
        else:
            # Save
            card.saved_by.append(user_id)
            card.stats.save_count += 1
            is_saved = True
        
        await card.save()
        
        return {
            "is_saved": is_saved,
            "total_saves": len(card.saved_by),
        }

    # === Clone ===

    async def clone_card(
        self,
        card_code: str,
        user_id: str,
        data: CloneCardRequest,
        user_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Clone an experience from a card"""
        
        from app.services.experience_service import experience_service
        
        card = await self.get_card_by_code(card_code, record_view=False)
        
        if not card.settings.allow_cloning:
            raise ForbiddenError("This experience cannot be cloned")
        
        # Create travelers object if provided
        travelers = None
        if data.travelers:
            from app.models.experience import TravelGroup
            travelers = TravelGroup(
                adults=data.travelers.get("adults", 1),
                children=data.travelers.get("children", 0),
                infants=data.travelers.get("infants", 0),
                total_passengers=(
                    data.travelers.get("adults", 1) +
                    data.travelers.get("children", 0) +
                    data.travelers.get("infants", 0)
                ),
            )
        
        # Clone using experience service
        new_experience = await experience_service.clone_from_card(
            user_id=user_id,
            share_code=card_code,
            new_start_date=data.new_start_date,
            travelers=travelers,
            user_name=user_name,
        )
        
        return {
            "new_experience_id": str(new_experience.id),
            "new_experience_title": new_experience.title,
            "original_card_code": card_code,
            "status": new_experience.status.value,
            "estimated_total": new_experience.pricing.grand_total,
            "currency": new_experience.pricing.currency,
            "requires_payment": True,
        }

    # === Search & Discovery ===

    async def search_public_cards(
        self,
        filters: CardSearchFilters,
        skip: int = 0,
        limit: int = 20,
    ) -> Tuple[List[ExperienceCard], int]:
        """Search public experience cards"""
        
        query: Dict[str, Any] = {
            "settings.is_public": True,
            "settings.is_active": True,
            "is_deleted": False,
        }
        
        if filters.destination_city:
            query["destination.city"] = {"$regex": filters.destination_city, "$options": "i"}
        if filters.destination_country:
            query["destination.country"] = {"$regex": filters.destination_country, "$options": "i"}
        if filters.start_date_from:
            query["dates.start_date"] = {"$gte": filters.start_date_from}
        if filters.start_date_to:
            if "dates.start_date" in query:
                query["dates.start_date"]["$lte"] = filters.start_date_to
            else:
                query["dates.start_date"] = {"$lte": filters.start_date_to}
        if filters.min_travelers:
            query["travelers.total_passengers"] = {"$gte": filters.min_travelers}
        if filters.max_travelers:
            if "travelers.total_passengers" in query:
                query["travelers.total_passengers"]["$lte"] = filters.max_travelers
            else:
                query["travelers.total_passengers"] = {"$lte": filters.max_travelers}
        if filters.tags:
            query["tags"] = {"$in": filters.tags}
        
        total = await ExperienceCard.find(query).count()
        cards = await ExperienceCard.find(query)\
            .sort("-stats.view_count")\
            .skip(skip)\
            .limit(limit)\
            .to_list()
        
        return cards, total

    async def get_featured_cards(
        self,
        limit: int = 10,
    ) -> List[ExperienceCard]:
        """Get featured public cards"""
        
        # Featured = public, active, most viewed
        query = {
            "settings.is_public": True,
            "settings.is_active": True,
            "is_deleted": False,
        }
        
        cards = await ExperienceCard.find(query)\
            .sort("-stats.view_count")\
            .limit(limit)\
            .to_list()
        
        return cards

    async def get_nearby_cards(
        self,
        latitude: float,
        longitude: float,
        max_distance_km: float = 100,
        limit: int = 20,
    ) -> List[ExperienceCard]:
        """Get cards for destinations near a location"""
        
        # Note: For proper geo queries, we'd need MongoDB geospatial indexes
        # For now, we'll fetch public cards and filter in Python
        
        cards, _ = await self.search_public_cards(
            filters=CardSearchFilters(),
            limit=100,
        )
        
        # Filter by distance
        from math import radians, sin, cos, sqrt, atan2
        
        nearby = []
        for card in cards:
            if not card.destination.latitude or not card.destination.longitude:
                continue
            
            # Haversine formula
            R = 6371  # Earth's radius in km
            lat1, lon1 = radians(latitude), radians(longitude)
            lat2 = radians(card.destination.latitude)
            lon2 = radians(card.destination.longitude)
            
            dlat = lat2 - lat1
            dlon = lon2 - lon1
            
            a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
            c = 2 * atan2(sqrt(a), sqrt(1-a))
            distance = R * c
            
            if distance <= max_distance_km:
                nearby.append((card, distance))
        
        # Sort by distance
        nearby.sort(key=lambda x: x[1])
        
        return [card for card, _ in nearby[:limit]]

    # === QR Code ===

    async def generate_qr_code(
        self,
        card_id: str,
        user_id: str,
        size: int = 256,
        include_logo: bool = True,
    ) -> str:
        """Generate QR code for a card"""
        
        card = await self._get_and_verify_ownership(card_id, user_id)
        
        qr_url = await self._generate_qr_code(card.share_url, size)
        
        card.qr_code_url = qr_url
        await card.save()
        
        return qr_url

    async def _generate_qr_code(
        self,
        url: str,
        size: int = 256,
    ) -> str:
        """Generate QR code as base64 data URL"""
        
        try:
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(url)
            qr.make(fit=True)
            
            img = qr.make_image(fill_color="black", back_color="white")
            
            # Resize
            img = img.resize((size, size))
            
            # Convert to base64
            buffer = io.BytesIO()
            img.save(buffer, format="PNG")
            buffer.seek(0)
            
            base64_image = base64.b64encode(buffer.read()).decode("utf-8")
            
            return f"data:image/png;base64,{base64_image}"
            
        except Exception as e:
            logger.error(f"Error generating QR code: {e}")
            return ""

    # === Helpers ===

    async def _get_and_verify_ownership(
        self,
        card_id: str,
        user_id: str,
    ) -> ExperienceCard:
        """Get card and verify user owns it"""
        
        card = await self.get_card(card_id)
        
        if card.owner.user_id != user_id:
            raise ForbiddenError("You don't have permission to access this card")
        
        return card


# Global service instance
experience_card_service = ExperienceCardService()

