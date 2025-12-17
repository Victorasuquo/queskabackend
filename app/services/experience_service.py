"""
Queska Backend - Experience Service
Business logic for experience creation, management, and booking flow
"""

from datetime import datetime, date, timedelta
from typing import Any, Dict, List, Optional, Tuple
import secrets
import string

from beanie import PydanticObjectId
from loguru import logger
from slugify import slugify

from app.core.constants import ExperienceStatus, PaymentStatus
from app.core.exceptions import (
    NotFoundError,
    ValidationError,
    ForbiddenError,
    ConflictError,
)
from app.models.experience import (
    Experience,
    ExperienceItem,
    TravelLocation,
    TravelDates,
    TravelGroup,
    ExperiencePreferences,
    ExperiencePricing,
    ExperienceSharing,
    ExperienceAnalytics,
    ItineraryDay,
)
from app.models.experience_card import ExperienceCard
from app.schemas.experience import (
    ExperienceCreate,
    ExperienceUpdate,
    ExperienceItemCreate,
    ExperienceItemUpdate,
    AddAccommodationRequest,
    AddRideRequest,
    AddEventRequest,
    AddActivityRequest,
    AddDiningRequest,
    AddPlaceRequest,
    AddFlightRequest,
    ApplyDiscountRequest,
    CheckoutRequest,
    CloneExperienceRequest,
    ExperienceSharingSettings,
    ExperienceFilters,
)


class ExperienceService:
    """
    Service for managing travel experiences.
    
    The experience flow:
    1. User creates experience (destination, dates, travelers, preferences)
    2. User adds items (accommodation, rides, events, activities, dining, flights)
    3. System generates itinerary and calculates pricing
    4. User proceeds to checkout and pays
    5. Experience card is generated and shareable
    """

    # === Create Experience ===

    async def create_experience(
        self,
        user_id: str,
        data: ExperienceCreate,
        user_name: Optional[str] = None,
        user_email: Optional[str] = None,
        agent_id: Optional[str] = None,
        agent_name: Optional[str] = None,
    ) -> Experience:
        """Create a new experience (Step 1 of the flow)"""
        
        # Validate dates
        if data.dates.start_date < date.today():
            raise ValidationError("Start date cannot be in the past")
        
        if data.dates.end_date < data.dates.start_date:
            raise ValidationError("End date must be after start date")
        
        # Calculate total passengers
        total_passengers = data.travelers.adults + data.travelers.children + data.travelers.infants
        
        # Generate slug
        base_slug = slugify(data.title)
        slug = await self._generate_unique_slug(base_slug)
        
        # Generate share code
        share_code = self._generate_share_code()
        
        # Create experience
        experience = Experience(
            user_id=user_id,
            user_name=user_name,
            user_email=user_email,
            agent_id=agent_id,
            agent_name=agent_name,
            created_by_agent=agent_id is not None,
            title=data.title,
            slug=slug,
            description=data.description,
            cover_image=data.cover_image,
            origin=TravelLocation(**data.origin.model_dump()) if data.origin else None,
            destination=TravelLocation(**data.destination.model_dump()),
            dates=TravelDates(**data.dates.model_dump()),
            travelers=TravelGroup(
                **data.travelers.model_dump(),
                total_passengers=total_passengers
            ),
            preferences=ExperiencePreferences(**data.preferences.model_dump()),
            sharing=ExperienceSharing(
                share_code=share_code,
                share_url=f"https://queska.app/e/{share_code}",
            ),
            tags=data.tags,
            status=ExperienceStatus.DRAFT,
        )
        
        await experience.insert()
        logger.info(f"Experience created: {experience.id} for user {user_id}")
        
        return experience

    async def get_experience(
        self,
        experience_id: str,
        user_id: Optional[str] = None,
    ) -> Experience:
        """Get experience by ID"""
        try:
            experience = await Experience.get(PydanticObjectId(experience_id))
        except Exception:
            raise NotFoundError(f"Experience {experience_id} not found")
        
        if not experience or experience.is_deleted:
            raise NotFoundError(f"Experience {experience_id} not found")
        
        return experience

    async def get_user_experiences(
        self,
        user_id: str,
        status: Optional[ExperienceStatus] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> Tuple[List[Experience], int]:
        """Get all experiences for a user"""
        query: Dict[str, Any] = {
            "user_id": user_id,
            "is_deleted": False,
        }
        
        if status:
            query["status"] = status
        
        total = await Experience.find(query).count()
        experiences = await Experience.find(query)\
            .sort("-created_at")\
            .skip(skip)\
            .limit(limit)\
            .to_list()
        
        return experiences, total

    async def update_experience(
        self,
        experience_id: str,
        user_id: str,
        data: ExperienceUpdate,
    ) -> Experience:
        """Update experience details"""
        experience = await self._get_and_verify_ownership(experience_id, user_id)
        
        # Can only update draft or pending experiences
        if experience.status not in [ExperienceStatus.DRAFT, ExperienceStatus.PENDING]:
            raise ValidationError("Cannot update a confirmed or completed experience")
        
        update_data = data.model_dump(exclude_unset=True)
        
        # Update slug if title changed
        if "title" in update_data:
            base_slug = slugify(update_data["title"])
            update_data["slug"] = await self._generate_unique_slug(base_slug, experience_id)
        
        # Handle nested updates
        if "origin" in update_data and update_data["origin"]:
            update_data["origin"] = TravelLocation(**update_data["origin"])
        if "destination" in update_data and update_data["destination"]:
            update_data["destination"] = TravelLocation(**update_data["destination"])
        if "dates" in update_data and update_data["dates"]:
            update_data["dates"] = TravelDates(**update_data["dates"])
        if "travelers" in update_data and update_data["travelers"]:
            travelers_data = update_data["travelers"]
            total = travelers_data.get("adults", 1) + travelers_data.get("children", 0) + travelers_data.get("infants", 0)
            travelers_data["total_passengers"] = total
            update_data["travelers"] = TravelGroup(**travelers_data)
        if "preferences" in update_data and update_data["preferences"]:
            update_data["preferences"] = ExperiencePreferences(**update_data["preferences"])
        
        for key, value in update_data.items():
            setattr(experience, key, value)
        
        experience.updated_at = datetime.utcnow()
        await experience.save()
        
        return experience

    async def delete_experience(self, experience_id: str, user_id: str) -> bool:
        """Soft delete an experience"""
        experience = await self._get_and_verify_ownership(experience_id, user_id)
        
        # Can't delete paid/confirmed experiences
        if experience.status in [ExperienceStatus.CONFIRMED, ExperienceStatus.IN_PROGRESS]:
            raise ValidationError("Cannot delete a confirmed or ongoing experience")
        
        await experience.soft_delete()
        logger.info(f"Experience {experience_id} deleted by user {user_id}")
        
        return True

    # === Add Items ===

    async def add_item(
        self,
        experience_id: str,
        user_id: str,
        item_data: ExperienceItemCreate,
    ) -> Experience:
        """Add a generic item to experience"""
        experience = await self._get_and_verify_ownership(experience_id, user_id)
        self._verify_can_modify(experience)
        
        # Calculate total price
        total_price = item_data.price_per_unit * item_data.quantity if not item_data.is_free else 0
        
        item = ExperienceItem(
            type=item_data.type,
            name=item_data.name,
            description=item_data.description,
            category=item_data.category,
            vendor_id=item_data.vendor_id,
            vendor_name=item_data.vendor_name,
            location=TravelLocation(**item_data.location.model_dump()) if item_data.location else None,
            scheduled_date=item_data.scheduled_date,
            start_time=item_data.start_time,
            end_time=item_data.end_time,
            duration_minutes=item_data.duration_minutes,
            price_per_unit=item_data.price_per_unit,
            quantity=item_data.quantity,
            total_price=total_price,
            currency=item_data.currency,
            is_free=item_data.is_free,
            image_url=item_data.image_url,
            images=item_data.images,
            details=item_data.details,
            notes=item_data.notes,
            order=len(experience.items),
            day_number=self._calculate_day_number(experience, item_data.scheduled_date),
        )
        
        experience.add_item(item)
        experience.generate_itinerary()
        await experience.save()
        
        return experience

    async def add_accommodation(
        self,
        experience_id: str,
        user_id: str,
        data: AddAccommodationRequest,
    ) -> Experience:
        """Add hotel/accommodation to experience"""
        experience = await self._get_and_verify_ownership(experience_id, user_id)
        self._verify_can_modify(experience)
        
        total_price = data.price_per_night * data.nights
        
        item = ExperienceItem(
            type="accommodation",
            name=data.name,
            category="hotel",
            vendor_id=data.vendor_id,
            location=TravelLocation(**data.location.model_dump()),
            scheduled_date=data.check_in_date,
            start_time=data.check_in_time,
            end_time=data.check_out_time,
            price_per_unit=data.price_per_night,
            quantity=data.nights,
            total_price=total_price,
            image_url=data.image_url,
            notes=data.notes,
            details={
                "room_type": data.room_type,
                "nights": data.nights,
                "check_in_date": data.check_in_date.isoformat(),
                "check_out_date": data.check_out_date.isoformat(),
                "check_in_time": data.check_in_time,
                "check_out_time": data.check_out_time,
                "guests": data.guests,
                "amenities": data.amenities,
            },
            order=len(experience.items),
            day_number=self._calculate_day_number(experience, data.check_in_date),
        )
        
        experience.add_item(item)
        experience.generate_itinerary()
        await experience.save()
        
        return experience

    async def add_ride(
        self,
        experience_id: str,
        user_id: str,
        data: AddRideRequest,
    ) -> Experience:
        """Add ride/transportation to experience"""
        experience = await self._get_and_verify_ownership(experience_id, user_id)
        self._verify_can_modify(experience)
        
        item = ExperienceItem(
            type="ride",
            name=f"{data.vehicle_type.title()} Ride",
            category=data.vehicle_type,
            vendor_id=data.vendor_id,
            location=TravelLocation(**data.pickup_location.model_dump()),
            scheduled_date=data.scheduled_date,
            start_time=data.pickup_time,
            duration_minutes=data.duration_minutes,
            price_per_unit=data.price,
            quantity=1,
            total_price=data.price,
            notes=data.notes,
            details={
                "vehicle_type": data.vehicle_type,
                "pickup_location": data.pickup_location.model_dump(),
                "dropoff_location": data.dropoff_location.model_dump(),
                "passengers": data.passengers,
                "distance_km": data.distance_km,
                "driver_name": data.driver_name,
            },
            order=len(experience.items),
            day_number=self._calculate_day_number(experience, data.scheduled_date),
        )
        
        experience.add_item(item)
        experience.generate_itinerary()
        await experience.save()
        
        return experience

    async def add_event(
        self,
        experience_id: str,
        user_id: str,
        data: AddEventRequest,
    ) -> Experience:
        """Add event to experience"""
        experience = await self._get_and_verify_ownership(experience_id, user_id)
        self._verify_can_modify(experience)
        
        total_price = 0 if data.is_free else (data.price_per_ticket * data.tickets_count)
        
        # Calculate duration if end_time provided
        duration = None
        if data.end_time:
            try:
                start = datetime.strptime(data.start_time, "%H:%M")
                end = datetime.strptime(data.end_time, "%H:%M")
                duration = int((end - start).total_seconds() / 60)
            except:
                pass
        
        item = ExperienceItem(
            type="event",
            name=data.name,
            category=data.event_type,
            vendor_id=data.vendor_id,
            location=TravelLocation(**data.location.model_dump()),
            scheduled_date=data.event_date,
            start_time=data.start_time,
            end_time=data.end_time,
            duration_minutes=duration,
            price_per_unit=data.price_per_ticket,
            quantity=data.tickets_count,
            total_price=total_price,
            is_free=data.is_free,
            image_url=data.image_url,
            notes=data.notes,
            details={
                "event_type": data.event_type,
                "ticket_type": data.ticket_type,
                "venue": data.venue,
            },
            order=len(experience.items),
            day_number=self._calculate_day_number(experience, data.event_date),
        )
        
        experience.add_item(item)
        experience.generate_itinerary()
        await experience.save()
        
        return experience

    async def add_activity(
        self,
        experience_id: str,
        user_id: str,
        data: AddActivityRequest,
    ) -> Experience:
        """Add activity to experience"""
        experience = await self._get_and_verify_ownership(experience_id, user_id)
        self._verify_can_modify(experience)
        
        total_price = data.price_per_person * data.participants
        
        item = ExperienceItem(
            type="activity",
            name=data.name,
            category=data.activity_type,
            vendor_id=data.vendor_id,
            location=TravelLocation(**data.location.model_dump()),
            scheduled_date=data.scheduled_date,
            start_time=data.start_time,
            duration_minutes=data.duration_minutes,
            price_per_unit=data.price_per_person,
            quantity=data.participants,
            total_price=total_price,
            image_url=data.image_url,
            notes=data.notes,
            details={
                "activity_type": data.activity_type,
                "difficulty_level": data.difficulty_level,
                "equipment_included": data.equipment_included,
                "what_to_bring": data.what_to_bring,
            },
            order=len(experience.items),
            day_number=self._calculate_day_number(experience, data.scheduled_date),
        )
        
        experience.add_item(item)
        experience.generate_itinerary()
        await experience.save()
        
        return experience

    async def add_dining(
        self,
        experience_id: str,
        user_id: str,
        data: AddDiningRequest,
    ) -> Experience:
        """Add restaurant/dining to experience"""
        experience = await self._get_and_verify_ownership(experience_id, user_id)
        self._verify_can_modify(experience)
        
        total_price = data.estimated_cost_per_person * data.party_size
        
        item = ExperienceItem(
            type="dining",
            name=data.name,
            category=data.cuisine_type,
            vendor_id=data.vendor_id,
            location=TravelLocation(**data.location.model_dump()),
            scheduled_date=data.reservation_date,
            start_time=data.reservation_time,
            duration_minutes=90,  # Default dining duration
            price_per_unit=data.estimated_cost_per_person,
            quantity=data.party_size,
            total_price=total_price,
            image_url=data.image_url,
            notes=data.notes,
            details={
                "cuisine_type": data.cuisine_type,
                "meal_type": data.meal_type,
                "party_size": data.party_size,
                "dietary_options": data.dietary_options,
                "dress_code": data.dress_code,
            },
            order=len(experience.items),
            day_number=self._calculate_day_number(experience, data.reservation_date),
        )
        
        experience.add_item(item)
        experience.generate_itinerary()
        await experience.save()
        
        return experience

    async def add_place(
        self,
        experience_id: str,
        user_id: str,
        data: AddPlaceRequest,
    ) -> Experience:
        """Add place to visit"""
        experience = await self._get_and_verify_ownership(experience_id, user_id)
        self._verify_can_modify(experience)
        
        total_price = 0 if data.is_free else (data.entrance_fee * data.visitors)
        
        item = ExperienceItem(
            type="place",
            name=data.name,
            category=data.place_type,
            location=TravelLocation(**data.location.model_dump()),
            scheduled_date=data.visit_date,
            start_time=data.visit_time,
            duration_minutes=data.duration_minutes,
            price_per_unit=data.entrance_fee,
            quantity=data.visitors,
            total_price=total_price,
            is_free=data.is_free,
            image_url=data.image_url,
            notes=data.notes,
            details={
                "place_type": data.place_type,
                "opening_hours": data.opening_hours,
            },
            order=len(experience.items),
            day_number=self._calculate_day_number(experience, data.visit_date),
        )
        
        experience.add_item(item)
        experience.generate_itinerary()
        await experience.save()
        
        return experience

    async def add_flight(
        self,
        experience_id: str,
        user_id: str,
        data: AddFlightRequest,
    ) -> Experience:
        """Add flight to experience"""
        experience = await self._get_and_verify_ownership(experience_id, user_id)
        self._verify_can_modify(experience)
        
        total_price = data.price_per_passenger * data.passengers
        
        item = ExperienceItem(
            type="flight",
            name=f"{data.airline} {data.flight_number}",
            category=data.cabin_class,
            scheduled_date=data.departure_date,
            start_time=data.departure_time,
            end_time=data.arrival_time,
            duration_minutes=data.flight_duration_minutes,
            price_per_unit=data.price_per_passenger,
            quantity=data.passengers,
            total_price=total_price,
            booking_reference=data.booking_reference,
            notes=data.notes,
            details={
                "airline": data.airline,
                "flight_number": data.flight_number,
                "departure_airport": data.departure_airport,
                "arrival_airport": data.arrival_airport,
                "cabin_class": data.cabin_class,
                "baggage_included": data.baggage_included,
            },
            order=len(experience.items),
            day_number=self._calculate_day_number(experience, data.departure_date),
        )
        
        experience.add_item(item)
        experience.generate_itinerary()
        await experience.save()
        
        return experience

    async def update_item(
        self,
        experience_id: str,
        user_id: str,
        item_id: str,
        data: ExperienceItemUpdate,
    ) -> Experience:
        """Update an item in the experience"""
        experience = await self._get_and_verify_ownership(experience_id, user_id)
        self._verify_can_modify(experience)
        
        update_data = data.model_dump(exclude_unset=True)
        
        if not experience.update_item(item_id, update_data):
            raise NotFoundError(f"Item {item_id} not found in experience")
        
        experience.generate_itinerary()
        await experience.save()
        
        return experience

    async def remove_item(
        self,
        experience_id: str,
        user_id: str,
        item_id: str,
    ) -> Experience:
        """Remove an item from the experience"""
        experience = await self._get_and_verify_ownership(experience_id, user_id)
        self._verify_can_modify(experience)
        
        if not experience.remove_item(item_id):
            raise NotFoundError(f"Item {item_id} not found in experience")
        
        experience.generate_itinerary()
        await experience.save()
        
        return experience

    async def reorder_items(
        self,
        experience_id: str,
        user_id: str,
        item_order: List[str],  # List of item IDs in new order
    ) -> Experience:
        """Reorder items in the experience"""
        experience = await self._get_and_verify_ownership(experience_id, user_id)
        self._verify_can_modify(experience)
        
        # Create ID to item mapping
        item_map = {item.id: item for item in experience.items}
        
        # Reorder
        new_items = []
        for i, item_id in enumerate(item_order):
            if item_id in item_map:
                item = item_map[item_id]
                item.order = i
                new_items.append(item)
        
        experience.items = new_items
        experience.generate_itinerary()
        await experience.save()
        
        return experience

    # === Checkout & Payment ===

    async def apply_discount(
        self,
        experience_id: str,
        user_id: str,
        discount_code: str,
    ) -> Experience:
        """Apply discount code to experience"""
        experience = await self._get_and_verify_ownership(experience_id, user_id)
        self._verify_can_modify(experience)
        
        # TODO: Validate discount code against promotions collection
        # For now, hardcode some sample discounts
        discount_percentage = 0.0
        if discount_code.upper() == "WELCOME10":
            discount_percentage = 10.0
        elif discount_code.upper() == "SUMMER20":
            discount_percentage = 20.0
        else:
            raise ValidationError("Invalid discount code")
        
        discount_amount = experience.pricing.items_subtotal * (discount_percentage / 100)
        
        experience.pricing.discount_code = discount_code.upper()
        experience.pricing.discount_percentage = discount_percentage
        experience.pricing.discount_amount = discount_amount
        experience.pricing.calculate_totals(experience.items, experience.travelers.total_passengers)
        
        await experience.save()
        
        return experience

    async def checkout(
        self,
        experience_id: str,
        user_id: str,
        data: CheckoutRequest,
    ) -> Dict[str, Any]:
        """Submit experience for checkout and payment"""
        experience = await self._get_and_verify_ownership(experience_id, user_id)
        
        # Validate experience is ready for checkout
        if not experience.items:
            raise ValidationError("Experience must have at least one item")
        
        if experience.status not in [ExperienceStatus.DRAFT, ExperienceStatus.PENDING]:
            raise ValidationError("Experience is not in a valid state for checkout")
        
        # Recalculate pricing
        experience.pricing.calculate_totals(experience.items, experience.travelers.total_passengers)
        
        # Apply discount if provided
        if data.discount_code:
            await self.apply_discount(experience_id, user_id, data.discount_code)
        
        # Update status
        experience.status = ExperienceStatus.PENDING
        experience.submitted_at = datetime.utcnow()
        await experience.save()
        
        # TODO: Create Stripe checkout session
        # For now, return mock payment info
        payment_reference = f"QSK-{secrets.token_hex(8).upper()}"
        
        return {
            "experience_id": str(experience.id),
            "total_amount": experience.pricing.grand_total,
            "currency": experience.pricing.currency,
            "payment_reference": payment_reference,
            "payment_url": f"https://checkout.stripe.com/pay/{payment_reference}",  # Mock
            "status": experience.status,
            "expires_at": datetime.utcnow() + timedelta(hours=24),
        }

    async def confirm_payment(
        self,
        experience_id: str,
        payment_reference: str,
        payment_data: Dict[str, Any],
    ) -> Experience:
        """Confirm payment and generate experience card"""
        experience = await Experience.get(PydanticObjectId(experience_id))
        
        if not experience:
            raise NotFoundError(f"Experience {experience_id} not found")
        
        if experience.status != ExperienceStatus.PENDING:
            raise ValidationError("Experience is not pending payment")
        
        # Update payment status
        experience.pricing.payment_status = PaymentStatus.COMPLETED
        experience.pricing.amount_paid = experience.pricing.grand_total
        experience.pricing.balance_due = 0
        
        # Update experience status
        experience.status = ExperienceStatus.CONFIRMED
        experience.paid_at = datetime.utcnow()
        
        # Generate experience card
        card = await ExperienceCard.create_from_experience(experience)
        await card.insert()
        
        experience.experience_card_id = str(card.id)
        experience.card_generated = True
        experience.sharing.share_code = card.card_code
        experience.sharing.share_url = card.share_url
        
        await experience.save()
        
        logger.info(f"Payment confirmed for experience {experience_id}, card {card.card_code} generated")
        
        return experience

    # === Clone Experience ===

    async def clone_from_card(
        self,
        user_id: str,
        share_code: str,
        new_start_date: date,
        travelers: Optional[TravelGroup] = None,
        user_name: Optional[str] = None,
    ) -> Experience:
        """Clone an experience from a shared card"""
        
        # Find the card
        card = await ExperienceCard.find_one({"card_code": share_code})
        if not card or not card.is_active:
            raise NotFoundError(f"Experience card {share_code} not found or inactive")
        
        if not card.settings.allow_cloning:
            raise ForbiddenError("This experience cannot be cloned")
        
        # Find original experience
        original = await Experience.get(PydanticObjectId(card.experience_id))
        if not original:
            raise NotFoundError("Original experience not found")
        
        # Calculate date offset
        date_offset = (new_start_date - original.dates.start_date).days
        new_end_date = original.dates.end_date + timedelta(days=date_offset)
        
        # Clone items with adjusted dates
        cloned_items = []
        for item in original.items:
            new_item = ExperienceItem(**item.model_dump())
            new_item.id = str(PydanticObjectId())
            new_item.booking_status = "pending"
            new_item.booking_reference = None
            new_item.confirmation_code = None
            
            if new_item.scheduled_date:
                new_item.scheduled_date = new_item.scheduled_date + timedelta(days=date_offset)
            
            cloned_items.append(new_item)
        
        # Create new experience
        new_travelers = travelers or original.travelers
        
        clone = Experience(
            user_id=user_id,
            user_name=user_name,
            title=f"{original.title} (Clone)",
            slug=await self._generate_unique_slug(slugify(original.title)),
            description=original.description,
            cover_image=original.cover_image,
            images=original.images,
            origin=original.origin,
            destination=original.destination,
            dates=TravelDates(
                start_date=new_start_date,
                end_date=new_end_date,
                flexible_dates=False,
            ),
            travelers=new_travelers,
            preferences=original.preferences,
            items=cloned_items,
            tags=original.tags,
            categories=original.categories,
            cloned_from_id=str(original.id),
            cloned_from_card_code=share_code,
            is_clone=True,
            status=ExperienceStatus.DRAFT,
            sharing=ExperienceSharing(
                share_code=self._generate_share_code(),
            ),
        )
        
        clone.generate_itinerary()
        clone.pricing.calculate_totals(clone.items, clone.travelers.total_passengers)
        
        await clone.insert()
        
        # Record clone on original card
        card.record_clone(str(clone.id), user_id)
        await card.save()
        
        logger.info(f"Experience cloned from card {share_code} to {clone.id}")
        
        return clone

    # === Sharing ===

    async def update_sharing_settings(
        self,
        experience_id: str,
        user_id: str,
        settings: ExperienceSharingSettings,
    ) -> Experience:
        """Update sharing settings"""
        experience = await self._get_and_verify_ownership(experience_id, user_id)
        
        update_data = settings.model_dump(exclude_unset=True)
        
        for key, value in update_data.items():
            setattr(experience.sharing, key, value)
        
        await experience.save()
        
        return experience

    async def get_experience_by_share_code(
        self,
        share_code: str,
    ) -> Experience:
        """Get experience by share code"""
        experience = await Experience.find_one({
            "sharing.share_code": share_code,
            "is_deleted": False,
        })
        
        if not experience:
            raise NotFoundError(f"Experience with share code {share_code} not found")
        
        if not experience.sharing.is_shareable:
            raise ForbiddenError("This experience is not shareable")
        
        # Increment view count
        experience.sharing.view_count += 1
        await experience.save()
        
        return experience

    # === Search & Filter ===

    async def search_experiences(
        self,
        filters: ExperienceFilters,
        skip: int = 0,
        limit: int = 20,
    ) -> Tuple[List[Experience], int]:
        """Search experiences with filters"""
        query: Dict[str, Any] = {"is_deleted": False}
        
        if filters.status:
            query["status"] = filters.status
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
        if filters.tags:
            query["tags"] = {"$in": filters.tags}
        if filters.is_upcoming:
            query["dates.start_date"] = {"$gt": date.today()}
        if filters.card_generated is not None:
            query["card_generated"] = filters.card_generated
        
        total = await Experience.find(query).count()
        experiences = await Experience.find(query)\
            .sort("-created_at")\
            .skip(skip)\
            .limit(limit)\
            .to_list()
        
        return experiences, total

    # === Helper Methods ===

    async def _get_and_verify_ownership(
        self,
        experience_id: str,
        user_id: str,
    ) -> Experience:
        """Get experience and verify user owns it"""
        experience = await self.get_experience(experience_id)
        
        if experience.user_id != user_id:
            raise ForbiddenError("You don't have permission to access this experience")
        
        return experience

    def _verify_can_modify(self, experience: Experience) -> None:
        """Verify experience can be modified"""
        if experience.status not in [ExperienceStatus.DRAFT, ExperienceStatus.PENDING]:
            raise ValidationError("Cannot modify a confirmed or completed experience")

    async def _generate_unique_slug(
        self,
        base_slug: str,
        exclude_id: Optional[str] = None,
    ) -> str:
        """Generate unique slug"""
        slug = base_slug
        counter = 1
        
        while True:
            query = {"slug": slug, "is_deleted": False}
            if exclude_id:
                query["_id"] = {"$ne": PydanticObjectId(exclude_id)}
            
            existing = await Experience.find_one(query)
            if not existing:
                return slug
            
            slug = f"{base_slug}-{counter}"
            counter += 1

    def _generate_share_code(self) -> str:
        """Generate unique share code"""
        chars = string.ascii_uppercase + string.digits
        chars = chars.replace('O', '').replace('0', '').replace('I', '').replace('1', '')
        return ''.join(secrets.choice(chars) for _ in range(8))

    def _calculate_day_number(
        self,
        experience: Experience,
        item_date: Optional[date],
    ) -> int:
        """Calculate which day of the trip an item falls on"""
        if not item_date:
            return 1
        
        day_diff = (item_date - experience.dates.start_date).days
        return max(1, day_diff + 1)


# Global service instance
experience_service = ExperienceService()

