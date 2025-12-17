"""
Queska Backend - Activity Service
Business logic for activities, tours, and experiences
"""

import secrets
import string
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from beanie import PydanticObjectId
from loguru import logger
from slugify import slugify

from app.core.config import settings
from app.core.exceptions import NotFoundError, ValidationError, ForbiddenError
from app.models.activity import (
    Activity,
    ActivityAvailability,
    ActivityBooking,
    ActivityReview,
    ActivityWishlist,
    ActivityLocation,
    ActivityDuration,
    ActivityPricing,
    ActivitySchedule,
    ActivityCapacity,
    ActivityInclusions,
    ActivityRequirements,
    ActivityPolicies,
    ActivityRating,
    ActivityProvider,
)
from app.schemas.activity import (
    ActivityCreate,
    ActivityUpdate,
    ActivityBookingCreate,
    ActivityReviewCreate,
    AvailabilityRequest,
    ActivitySearchRequest,
)


class ActivityService:
    """
    Activity service providing:
    - Activity CRUD
    - Availability management
    - Booking management
    - Reviews
    - Wishlist
    - Search and discovery
    """
    
    # ================================================================
    # ACTIVITY CRUD
    # ================================================================
    
    async def create_activity(
        self,
        data: ActivityCreate,
        vendor_id: Optional[str] = None,
        created_by: Optional[str] = None
    ) -> Activity:
        """Create a new activity."""
        # Generate unique slug
        base_slug = slugify(data.name)
        slug = base_slug
        counter = 1
        
        while await Activity.find_one({"slug": slug}):
            slug = f"{base_slug}-{counter}"
            counter += 1
        
        # Calculate from_price
        from_price = data.pricing.adult_price
        if data.pricing.child_price and data.pricing.child_price < from_price:
            from_price = data.pricing.child_price
        
        # Build activity
        activity = Activity(
            name=data.name,
            slug=slug,
            short_description=data.short_description,
            description=data.description,
            category=data.category,
            subcategory=data.subcategory,
            activity_type=data.activity_type,
            tags=data.tags,
            location=ActivityLocation(
                name=data.location.name,
                address=data.location.address,
                city=data.location.city,
                state=data.location.state,
                country=data.location.country,
                postal_code=data.location.postal_code,
                latitude=data.location.latitude,
                longitude=data.location.longitude,
                meeting_point=data.location.meeting_point,
                meeting_point_details=data.location.meeting_point_details,
            ),
            duration=ActivityDuration(
                minutes=data.duration.minutes,
                hours=data.duration.minutes / 60 if data.duration.minutes else None,
                display_text=data.duration.display_text,
                is_flexible=data.duration.is_flexible,
            ),
            pricing=ActivityPricing(
                currency=data.pricing.currency,
                adult_price=data.pricing.adult_price,
                child_price=data.pricing.child_price,
                infant_price=data.pricing.infant_price,
                group_price=data.pricing.group_price,
                group_min_size=data.pricing.group_min_size,
                group_max_size=data.pricing.group_max_size,
                private_price=data.pricing.private_price,
                pricing_type=data.pricing.pricing_type,
                from_price=from_price,
            ),
            schedule=ActivitySchedule(
                available_days=data.schedule.available_days if data.schedule else [],
                start_times=data.schedule.start_times if data.schedule else [],
            ) if data.schedule else ActivitySchedule(),
            capacity=ActivityCapacity(
                min_participants=data.min_participants,
                max_participants=data.max_participants,
            ),
            inclusions=ActivityInclusions(
                included=data.included,
                excluded=data.excluded,
                bring_items=data.bring_items,
            ),
            requirements=ActivityRequirements(
                min_age=data.min_age,
                max_age=data.max_age,
                fitness_level=data.fitness_level,
            ),
            policies=ActivityPolicies(
                cancellation_policy=data.cancellation_policy,
                cancellation_deadline_hours=data.cancellation_deadline_hours,
                instant_confirmation=data.instant_confirmation,
            ),
            highlights=data.highlights,
            cover_image=data.cover_image,
            images=data.images,
            video_url=data.video_url,
            available_languages=data.available_languages,
            wheelchair_accessible=data.wheelchair_accessible,
            accessibility_info=data.accessibility_info,
            vendor_id=vendor_id,
            created_by=created_by,
        )
        
        # Set provider if vendor
        if vendor_id:
            activity.provider = ActivityProvider(
                vendor_id=vendor_id,
                name="Vendor",  # Will be populated later
                is_verified=False,
            )
        
        await activity.insert()
        
        logger.info(f"Created activity: {activity.id} - {activity.name}")
        
        return activity
    
    async def get_activity_by_id(self, activity_id: str) -> Activity:
        """Get activity by ID."""
        activity = await Activity.find_one({
            "_id": PydanticObjectId(activity_id),
            "is_deleted": False
        })
        
        if not activity:
            raise NotFoundError("Activity", activity_id)
        
        return activity
    
    async def get_activity_by_slug(self, slug: str) -> Activity:
        """Get activity by slug."""
        activity = await Activity.find_one({
            "slug": slug,
            "is_deleted": False,
            "is_active": True
        })
        
        if not activity:
            raise NotFoundError("Activity", slug)
        
        # Increment view count
        activity.view_count += 1
        await activity.save()
        
        return activity
    
    async def update_activity(
        self,
        activity_id: str,
        data: ActivityUpdate,
        updated_by: Optional[str] = None,
        vendor_id: Optional[str] = None
    ) -> Activity:
        """Update an activity."""
        activity = await self.get_activity_by_id(activity_id)
        
        # Check ownership if vendor
        if vendor_id and activity.vendor_id != vendor_id:
            raise ForbiddenError("You can only update your own activities")
        
        # Update fields
        update_data = data.model_dump(exclude_unset=True)
        
        for field, value in update_data.items():
            if value is not None:
                if field == "location":
                    activity.location = ActivityLocation(**value)
                elif field == "duration":
                    activity.duration = ActivityDuration(
                        minutes=value["minutes"],
                        hours=value["minutes"] / 60,
                        display_text=value["display_text"],
                        is_flexible=value.get("is_flexible", False),
                    )
                elif field == "pricing":
                    from_price = value["adult_price"]
                    if value.get("child_price") and value["child_price"] < from_price:
                        from_price = value["child_price"]
                    value["from_price"] = from_price
                    activity.pricing = ActivityPricing(**value)
                elif field == "schedule":
                    activity.schedule = ActivitySchedule(**value)
                elif hasattr(activity, field):
                    setattr(activity, field, value)
        
        activity.update_timestamp()
        await activity.save()
        
        return activity
    
    async def delete_activity(
        self,
        activity_id: str,
        vendor_id: Optional[str] = None
    ) -> bool:
        """Soft delete an activity."""
        activity = await self.get_activity_by_id(activity_id)
        
        if vendor_id and activity.vendor_id != vendor_id:
            raise ForbiddenError("You can only delete your own activities")
        
        await activity.soft_delete()
        
        return True
    
    async def list_activities(
        self,
        category: Optional[str] = None,
        city: Optional[str] = None,
        vendor_id: Optional[str] = None,
        is_featured: Optional[bool] = None,
        is_active: bool = True,
        skip: int = 0,
        limit: int = 20,
        sort_by: str = "created_at"
    ) -> Tuple[List[Activity], int]:
        """List activities with filters."""
        query = {"is_deleted": False}
        
        if is_active is not None:
            query["is_active"] = is_active
        if category:
            query["category"] = category
        if city:
            query["location.city"] = {"$regex": city, "$options": "i"}
        if vendor_id:
            query["vendor_id"] = vendor_id
        if is_featured is not None:
            query["is_featured"] = is_featured
        
        # Sort mapping
        sort_mapping = {
            "created_at": [("created_at", -1)],
            "price_asc": [("pricing.from_price", 1)],
            "price_desc": [("pricing.from_price", -1)],
            "rating": [("rating.average", -1)],
            "popularity": [("booking_count", -1)],
            "recommended": [("is_featured", -1), ("rating.average", -1)],
        }
        
        sort_fields = sort_mapping.get(sort_by, [("created_at", -1)])
        
        total = await Activity.find(query).count()
        activities = await Activity.find(query)\
            .sort(sort_fields)\
            .skip(skip)\
            .limit(limit)\
            .to_list()
        
        return activities, total
    
    # ================================================================
    # SEARCH
    # ================================================================
    
    async def search_activities(
        self,
        request: ActivitySearchRequest,
        skip: int = 0,
        limit: int = 20
    ) -> Tuple[List[Activity], int, Dict[str, Any]]:
        """Search activities with filters."""
        query = {"is_deleted": False, "is_active": True}
        filters_applied = {}
        
        if request.destination:
            query["$or"] = [
                {"location.city": {"$regex": request.destination, "$options": "i"}},
                {"location.country": {"$regex": request.destination, "$options": "i"}},
                {"location.name": {"$regex": request.destination, "$options": "i"}},
            ]
            filters_applied["destination"] = request.destination
        
        if request.category:
            query["category"] = request.category
            filters_applied["category"] = request.category
        
        if request.price_min is not None:
            query["pricing.from_price"] = {"$gte": request.price_min}
            filters_applied["price_min"] = request.price_min
        
        if request.price_max is not None:
            if "pricing.from_price" in query:
                query["pricing.from_price"]["$lte"] = request.price_max
            else:
                query["pricing.from_price"] = {"$lte": request.price_max}
            filters_applied["price_max"] = request.price_max
        
        if request.duration_min is not None:
            query["duration.minutes"] = {"$gte": request.duration_min}
            filters_applied["duration_min"] = request.duration_min
        
        if request.duration_max is not None:
            if "duration.minutes" in query:
                query["duration.minutes"]["$lte"] = request.duration_max
            else:
                query["duration.minutes"] = {"$lte": request.duration_max}
            filters_applied["duration_max"] = request.duration_max
        
        if request.rating_min is not None:
            query["rating.average"] = {"$gte": request.rating_min}
            filters_applied["rating_min"] = request.rating_min
        
        if request.tags:
            query["tags"] = {"$in": request.tags}
            filters_applied["tags"] = request.tags
        
        if request.free_cancellation:
            query["policies.cancellation_policy"] = {"$in": ["free", "flexible"]}
            filters_applied["free_cancellation"] = True
        
        if request.instant_confirmation:
            query["policies.instant_confirmation"] = True
            filters_applied["instant_confirmation"] = True
        
        # Sort
        sort_mapping = {
            "recommended": [("is_featured", -1), ("rating.average", -1)],
            "price_asc": [("pricing.from_price", 1)],
            "price_desc": [("pricing.from_price", -1)],
            "rating": [("rating.average", -1)],
            "popularity": [("booking_count", -1)],
            "newest": [("created_at", -1)],
        }
        
        sort_fields = sort_mapping.get(request.sort_by, [("is_featured", -1), ("rating.average", -1)])
        
        total = await Activity.find(query).count()
        activities = await Activity.find(query)\
            .sort(sort_fields)\
            .skip(skip)\
            .limit(limit)\
            .to_list()
        
        return activities, total, filters_applied
    
    # ================================================================
    # AVAILABILITY
    # ================================================================
    
    async def get_availability(
        self,
        activity_id: str,
        start_date: date,
        end_date: date,
        participants: int = 1
    ) -> List[ActivityAvailability]:
        """Get availability slots for an activity."""
        activity = await self.get_activity_by_id(activity_id)
        
        # Get existing availability records
        slots = await ActivityAvailability.find({
            "activity_id": activity_id,
            "date": {"$gte": start_date, "$lte": end_date},
            "is_available": True,
            "remaining_spots": {"$gte": participants}
        }).sort("date", "start_time").to_list()
        
        return slots
    
    async def create_availability_slots(
        self,
        activity_id: str,
        dates: List[date],
        start_times: List[str],
        spots_per_slot: int = 20,
        vendor_id: Optional[str] = None
    ) -> List[ActivityAvailability]:
        """Create availability slots for an activity."""
        activity = await self.get_activity_by_id(activity_id)
        
        if vendor_id and activity.vendor_id != vendor_id:
            raise ForbiddenError("You can only manage availability for your own activities")
        
        created_slots = []
        
        for activity_date in dates:
            for start_time in start_times:
                # Check if slot exists
                existing = await ActivityAvailability.find_one({
                    "activity_id": activity_id,
                    "date": activity_date,
                    "start_time": start_time
                })
                
                if not existing:
                    slot = ActivityAvailability(
                        activity_id=activity_id,
                        date=activity_date,
                        start_time=start_time,
                        total_spots=spots_per_slot,
                        remaining_spots=spots_per_slot,
                    )
                    await slot.insert()
                    created_slots.append(slot)
        
        return created_slots
    
    # ================================================================
    # BOOKINGS
    # ================================================================
    
    def _generate_booking_reference(self) -> str:
        """Generate unique booking reference."""
        chars = string.ascii_uppercase + string.digits
        return "ACT-" + ''.join(secrets.choice(chars) for _ in range(8))
    
    async def create_booking(
        self,
        data: ActivityBookingCreate,
        user_id: str
    ) -> ActivityBooking:
        """Create an activity booking."""
        activity = await self.get_activity_by_id(data.activity_id)
        
        # Calculate total participants
        total_participants = data.adults + data.children + data.infants
        
        # Validate capacity
        if total_participants < activity.capacity.min_participants:
            raise ValidationError(f"Minimum {activity.capacity.min_participants} participants required")
        
        if total_participants > activity.capacity.max_per_booking:
            raise ValidationError(f"Maximum {activity.capacity.max_per_booking} participants per booking")
        
        # Check availability if slot specified
        if data.availability_id:
            slot = await ActivityAvailability.find_one({
                "_id": PydanticObjectId(data.availability_id),
                "is_available": True
            })
            
            if not slot or slot.remaining_spots < total_participants:
                raise ValidationError("Selected time slot is not available")
        
        # Calculate pricing
        subtotal = (
            (data.adults * activity.pricing.adult_price) +
            (data.children * (activity.pricing.child_price or activity.pricing.adult_price * 0.5)) +
            (data.infants * (activity.pricing.infant_price or 0))
        )
        
        # Platform fee
        fees = subtotal * 0.05
        taxes = 0  # Tax calculation would go here
        total_price = subtotal + fees + taxes
        
        # Generate booking reference
        booking_reference = self._generate_booking_reference()
        while await ActivityBooking.find_one({"booking_reference": booking_reference}):
            booking_reference = self._generate_booking_reference()
        
        # Create booking
        booking = ActivityBooking(
            activity_id=data.activity_id,
            availability_id=data.availability_id,
            user_id=user_id,
            experience_id=data.experience_id,
            booking_reference=booking_reference,
            activity_date=data.activity_date,
            start_time=data.start_time,
            adults=data.adults,
            children=data.children,
            infants=data.infants,
            total_participants=total_participants,
            participant_names=[p.name for p in data.participants],
            special_requirements=data.special_requirements,
            unit_price=activity.pricing.adult_price,
            subtotal=subtotal,
            fees=fees,
            taxes=taxes,
            total_price=total_price,
            currency=activity.pricing.currency,
            contact_name=data.contact_name,
            contact_email=data.contact_email,
            contact_phone=data.contact_phone,
            status="pending",
            payment_status="pending",
        )
        
        await booking.insert()
        
        # Update availability if slot specified
        if data.availability_id:
            await ActivityAvailability.find_one({"_id": PydanticObjectId(data.availability_id)}).update({
                "$inc": {"booked_spots": total_participants, "remaining_spots": -total_participants},
                "$push": {"booking_ids": str(booking.id)}
            })
        
        # Update activity booking count
        activity.booking_count += 1
        await activity.save()
        
        logger.info(f"Created booking {booking_reference} for activity {activity.name}")
        
        return booking
    
    async def confirm_booking(
        self,
        booking_id: str,
        confirmation_code: Optional[str] = None
    ) -> ActivityBooking:
        """Confirm a booking after payment."""
        booking = await ActivityBooking.find_one({
            "_id": PydanticObjectId(booking_id)
        })
        
        if not booking:
            raise NotFoundError("Booking", booking_id)
        
        booking.status = "confirmed"
        booking.payment_status = "paid"
        booking.confirmed_at = datetime.utcnow()
        booking.confirmation_code = confirmation_code or booking.booking_reference
        
        await booking.save()
        
        return booking
    
    async def cancel_booking(
        self,
        booking_id: str,
        user_id: str,
        reason: Optional[str] = None
    ) -> ActivityBooking:
        """Cancel a booking."""
        booking = await ActivityBooking.find_one({
            "_id": PydanticObjectId(booking_id),
            "user_id": user_id
        })
        
        if not booking:
            raise NotFoundError("Booking", booking_id)
        
        if booking.status in ["cancelled", "completed"]:
            raise ValidationError(f"Cannot cancel a {booking.status} booking")
        
        # Get activity for refund policy
        activity = await self.get_activity_by_id(booking.activity_id)
        
        # Calculate refund based on policy
        refund_amount = 0.0
        hours_until = (datetime.combine(booking.activity_date, datetime.min.time()) - datetime.utcnow()).total_seconds() / 3600
        
        if hours_until > activity.policies.cancellation_deadline_hours:
            if activity.policies.cancellation_policy in ["free", "flexible"]:
                refund_amount = booking.total_price
            elif activity.policies.cancellation_policy == "moderate":
                refund_amount = booking.total_price * 0.5
        
        booking.status = "cancelled"
        booking.cancelled_at = datetime.utcnow()
        booking.cancellation_reason = reason
        booking.refund_amount = refund_amount
        booking.refund_status = "pending" if refund_amount > 0 else None
        
        await booking.save()
        
        # Restore availability
        if booking.availability_id:
            await ActivityAvailability.find_one({"_id": PydanticObjectId(booking.availability_id)}).update({
                "$inc": {"booked_spots": -booking.total_participants, "remaining_spots": booking.total_participants},
                "$pull": {"booking_ids": str(booking.id)}
            })
        
        return booking
    
    async def get_user_bookings(
        self,
        user_id: str,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 20
    ) -> Tuple[List[ActivityBooking], int]:
        """Get user's activity bookings."""
        query = {"user_id": user_id}
        
        if status:
            query["status"] = status
        
        total = await ActivityBooking.find(query).count()
        bookings = await ActivityBooking.find(query)\
            .sort([("created_at", -1)])\
            .skip(skip)\
            .limit(limit)\
            .to_list()
        
        return bookings, total
    
    # ================================================================
    # REVIEWS
    # ================================================================
    
    async def create_review(
        self,
        data: ActivityReviewCreate,
        user_id: str
    ) -> ActivityReview:
        """Create an activity review."""
        activity = await self.get_activity_by_id(data.activity_id)
        
        # Check for existing review
        existing = await ActivityReview.find_one({
            "activity_id": data.activity_id,
            "user_id": user_id,
            "is_deleted": False
        })
        
        if existing:
            raise ValidationError("You have already reviewed this activity")
        
        review = ActivityReview(
            activity_id=data.activity_id,
            user_id=user_id,
            booking_id=data.booking_id,
            overall_rating=data.overall_rating,
            ratings=data.ratings,
            title=data.title,
            content=data.content,
            activity_date=data.activity_date,
            travel_type=data.travel_type,
            photos=data.photos,
            is_approved=False,  # Requires moderation
        )
        
        await review.insert()
        
        # Update activity rating
        await self._update_activity_rating(data.activity_id)
        
        return review
    
    async def _update_activity_rating(self, activity_id: str) -> None:
        """Recalculate activity rating from reviews."""
        pipeline = [
            {"$match": {"activity_id": activity_id, "is_approved": True, "is_deleted": False}},
            {"$group": {
                "_id": None,
                "average": {"$avg": "$overall_rating"},
                "count": {"$sum": 1}
            }}
        ]
        
        result = await ActivityReview.aggregate(pipeline).to_list()
        
        if result:
            await Activity.find_one({"_id": PydanticObjectId(activity_id)}).update({
                "$set": {
                    "rating.average": round(result[0]["average"], 1),
                    "rating.count": result[0]["count"]
                }
            })
    
    async def get_activity_reviews(
        self,
        activity_id: str,
        skip: int = 0,
        limit: int = 20
    ) -> Tuple[List[ActivityReview], int]:
        """Get reviews for an activity."""
        query = {
            "activity_id": activity_id,
            "is_approved": True,
            "is_deleted": False
        }
        
        total = await ActivityReview.find(query).count()
        reviews = await ActivityReview.find(query)\
            .sort([("created_at", -1)])\
            .skip(skip)\
            .limit(limit)\
            .to_list()
        
        return reviews, total
    
    # ================================================================
    # WISHLIST
    # ================================================================
    
    async def add_to_wishlist(
        self,
        user_id: str,
        activity_id: str,
        notes: Optional[str] = None,
        planned_date: Optional[date] = None
    ) -> ActivityWishlist:
        """Add activity to wishlist."""
        # Verify activity exists
        await self.get_activity_by_id(activity_id)
        
        # Check if already in wishlist
        existing = await ActivityWishlist.find_one({
            "user_id": user_id,
            "activity_id": activity_id,
            "is_deleted": False
        })
        
        if existing:
            raise ValidationError("Activity already in wishlist")
        
        wishlist_item = ActivityWishlist(
            user_id=user_id,
            activity_id=activity_id,
            notes=notes,
            planned_date=planned_date,
        )
        
        await wishlist_item.insert()
        
        # Update wishlist count
        await Activity.find_one({"_id": PydanticObjectId(activity_id)}).update({
            "$inc": {"wishlist_count": 1}
        })
        
        return wishlist_item
    
    async def remove_from_wishlist(
        self,
        user_id: str,
        activity_id: str
    ) -> bool:
        """Remove activity from wishlist."""
        result = await ActivityWishlist.find_one({
            "user_id": user_id,
            "activity_id": activity_id,
            "is_deleted": False
        })
        
        if result:
            await result.soft_delete()
            
            await Activity.find_one({"_id": PydanticObjectId(activity_id)}).update({
                "$inc": {"wishlist_count": -1}
            })
            
            return True
        
        return False
    
    async def get_user_wishlist(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 20
    ) -> Tuple[List[ActivityWishlist], int]:
        """Get user's activity wishlist."""
        query = {"user_id": user_id, "is_deleted": False}
        
        total = await ActivityWishlist.find(query).count()
        items = await ActivityWishlist.find(query)\
            .sort([("created_at", -1)])\
            .skip(skip)\
            .limit(limit)\
            .to_list()
        
        return items, total
    
    # ================================================================
    # FEATURED / POPULAR
    # ================================================================
    
    async def get_featured_activities(
        self,
        city: Optional[str] = None,
        limit: int = 10
    ) -> List[Activity]:
        """Get featured activities."""
        query = {
            "is_deleted": False,
            "is_active": True,
            "is_featured": True
        }
        
        if city:
            query["location.city"] = {"$regex": city, "$options": "i"}
        
        return await Activity.find(query)\
            .sort([("rating.average", -1)])\
            .limit(limit)\
            .to_list()
    
    async def get_popular_activities(
        self,
        city: Optional[str] = None,
        limit: int = 10
    ) -> List[Activity]:
        """Get popular activities."""
        query = {
            "is_deleted": False,
            "is_active": True,
        }
        
        if city:
            query["location.city"] = {"$regex": city, "$options": "i"}
        
        return await Activity.find(query)\
            .sort([("booking_count", -1), ("rating.average", -1)])\
            .limit(limit)\
            .to_list()
    
    async def get_categories(self) -> List[Dict[str, Any]]:
        """Get activity categories with counts."""
        pipeline = [
            {"$match": {"is_deleted": False, "is_active": True}},
            {"$group": {
                "_id": "$category",
                "count": {"$sum": 1}
            }},
            {"$sort": {"count": -1}}
        ]
        
        result = await Activity.aggregate(pipeline).to_list()
        
        return [{"category": r["_id"], "count": r["count"]} for r in result]


# Global service instance
activity_service = ActivityService()

