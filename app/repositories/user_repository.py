"""
Queska Backend - User Repository
Comprehensive data access layer for User operations
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from beanie import PydanticObjectId
from beanie.odm.operators.find.comparison import In, GTE, LTE

from app.core.constants import AccountStatus
from app.models.user import User, UserStats, UserPreferences, UserAddress, UserSubscription
from app.repositories.base import BaseRepository
from app.schemas.user import UserListParams


class UserRepository(BaseRepository):
    """Repository for User document operations"""
    
    def __init__(self):
        super().__init__(User)
    
    # === Basic Queries ===
    
    async def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        return await self.model.find_one(
            {"email": email.lower(), "is_deleted": False}
        )
    
    async def email_exists(
        self,
        email: str,
        exclude_id: Optional[str] = None
    ) -> bool:
        """Check if email exists"""
        return await self.exists("email", email.lower(), exclude_id)
    
    async def phone_exists(
        self,
        phone: str,
        exclude_id: Optional[str] = None
    ) -> bool:
        """Check if phone exists"""
        return await self.exists("phone", phone, exclude_id)
    
    async def referral_code_exists(self, code: str) -> bool:
        """Check if referral code exists"""
        return await self.exists("referral_code", code)
    
    # === OAuth Queries ===
    
    async def get_by_google_id(self, google_id: str) -> Optional[User]:
        """Get user by Google OAuth ID"""
        return await self.model.find_one(
            {"google_id": google_id, "is_deleted": False}
        )
    
    async def get_by_facebook_id(self, facebook_id: str) -> Optional[User]:
        """Get user by Facebook OAuth ID"""
        return await self.model.find_one(
            {"facebook_id": facebook_id, "is_deleted": False}
        )
    
    async def get_by_apple_id(self, apple_id: str) -> Optional[User]:
        """Get user by Apple OAuth ID"""
        return await self.model.find_one(
            {"apple_id": apple_id, "is_deleted": False}
        )
    
    # === User CRUD ===
    
    async def create_user(self, data: Dict[str, Any]) -> User:
        """Create a new user"""
        user = User(**data)
        await user.insert()
        return user
    
    async def update_user(
        self,
        user_id: str,
        data: Dict[str, Any]
    ) -> Optional[User]:
        """Update user by ID"""
        user = await self.get_by_id(user_id)
        if not user:
            return None
        
        for field, value in data.items():
            if value is not None:
                setattr(user, field, value)
        
        user.updated_at = datetime.utcnow()
        await user.save()
        return user
    
    async def update_status(
        self,
        user_id: str,
        status: AccountStatus,
        reason: Optional[str] = None
    ) -> Optional[User]:
        """Update user account status"""
        user = await self.get_by_id(user_id)
        if not user:
            return None
        
        user.status = status
        user.is_active = status == AccountStatus.ACTIVE
        
        if reason:
            user.metadata["status_change_reason"] = reason
            user.metadata["status_changed_at"] = datetime.utcnow().isoformat()
        
        user.updated_at = datetime.utcnow()
        await user.save()
        return user
    
    async def update_last_login(
        self,
        user_id: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Optional[User]:
        """Update user last login timestamp"""
        user = await self.get_by_id(user_id)
        if user:
            user.last_login_at = datetime.utcnow()
            user.last_active_at = datetime.utcnow()
            user.login_count += 1
            
            # Add activity log
            await user.add_activity_log(
                action="login",
                description="User logged in",
                ip_address=ip_address,
                user_agent=user_agent
            )
        return user
    
    async def verify_email(self, user_id: str) -> Optional[User]:
        """Mark user email as verified"""
        user = await self.get_by_id(user_id)
        if user:
            user.is_email_verified = True
            user.email_verified_at = datetime.utcnow()
            if user.status == AccountStatus.PENDING:
                user.status = AccountStatus.ACTIVE
                user.is_active = True
            await user.save()
        return user
    
    async def verify_phone(self, user_id: str) -> Optional[User]:
        """Mark user phone as verified"""
        user = await self.get_by_id(user_id)
        if user:
            user.is_phone_verified = True
            user.phone_verified_at = datetime.utcnow()
            await user.save()
        return user
    
    # === Listing & Search ===
    
    async def list_users(
        self,
        params: UserListParams
    ) -> Tuple[List[User], int]:
        """List users with filters and pagination"""
        query: Dict[str, Any] = {"is_deleted": False}
        
        # Apply filters
        if params.search:
            query["$text"] = {"$search": params.search}
        
        if params.status:
            query["status"] = params.status
        
        if params.is_email_verified is not None:
            query["is_email_verified"] = params.is_email_verified
        
        if params.is_active is not None:
            query["is_active"] = params.is_active
        
        if params.assigned_agent_id:
            query["assigned_agent_id"] = PydanticObjectId(params.assigned_agent_id)
        
        # Sort
        sort_order = -1 if params.sort_order == "desc" else 1
        
        # Get total count
        total = await self.model.find(query).count()
        
        # Get paginated results
        skip = (params.page - 1) * params.limit
        users = await self.model.find(query) \
            .sort((params.sort_by, sort_order)) \
            .skip(skip) \
            .limit(params.limit) \
            .to_list()
        
        return users, total
    
    async def search_users(
        self,
        query: str,
        skip: int = 0,
        limit: int = 20
    ) -> List[User]:
        """Full-text search for users"""
        return await self.model.find(
            {
                "$text": {"$search": query},
                "is_deleted": False,
                "is_active": True
            }
        ).skip(skip).limit(limit).to_list()
    
    # === Agent Assignment ===
    
    async def get_users_by_agent(
        self,
        agent_id: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[User]:
        """Get all users assigned to an agent"""
        return await self.model.find(
            {
                "assigned_agent_id": PydanticObjectId(agent_id),
                "is_deleted": False
            }
        ).skip(skip).limit(limit).to_list()
    
    async def assign_agent(
        self,
        user_id: str,
        agent_id: str
    ) -> Optional[User]:
        """Assign agent to user"""
        user = await self.get_by_id(user_id)
        if user:
            user.assigned_agent_id = PydanticObjectId(agent_id)
            user.updated_at = datetime.utcnow()
            await user.save()
        return user
    
    async def unassign_agent(self, user_id: str) -> Optional[User]:
        """Remove agent assignment from user"""
        user = await self.get_by_id(user_id)
        if user:
            user.assigned_agent_id = None
            user.updated_at = datetime.utcnow()
            await user.save()
        return user
    
    # === Favorites ===
    
    async def get_favorite_vendor_ids(self, user_id: str) -> List[str]:
        """Get user's favorite vendor IDs"""
        user = await self.get_by_id(user_id)
        if user:
            return [str(vid) for vid in user.favorite_vendors]
        return []
    
    async def add_favorite_vendor(
        self,
        user_id: str,
        vendor_id: str
    ) -> Optional[User]:
        """Add vendor to favorites"""
        user = await self.get_by_id(user_id)
        if user:
            await user.add_favorite_vendor(PydanticObjectId(vendor_id))
        return user
    
    async def remove_favorite_vendor(
        self,
        user_id: str,
        vendor_id: str
    ) -> Optional[User]:
        """Remove vendor from favorites"""
        user = await self.get_by_id(user_id)
        if user:
            await user.remove_favorite_vendor(PydanticObjectId(vendor_id))
        return user
    
    async def add_favorite_destination(
        self,
        user_id: str,
        destination: str
    ) -> Optional[User]:
        """Add destination to favorites"""
        user = await self.get_by_id(user_id)
        if user:
            await user.add_favorite_destination(destination)
        return user
    
    async def remove_favorite_destination(
        self,
        user_id: str,
        destination: str
    ) -> Optional[User]:
        """Remove destination from favorites"""
        user = await self.get_by_id(user_id)
        if user:
            await user.remove_favorite_destination(destination)
        return user
    
    # === Social/Following ===
    
    async def get_followers(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 20
    ) -> List[User]:
        """Get user's followers"""
        user = await self.get_by_id(user_id)
        if not user or not user.social_connections:
            return []
        
        follower_ids = user.social_connections.follower_ids[skip:skip+limit]
        return await self.model.find(
            In(self.model.id, follower_ids)
        ).to_list()
    
    async def get_following(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 20
    ) -> List[User]:
        """Get users that this user follows"""
        user = await self.get_by_id(user_id)
        if not user or not user.social_connections:
            return []
        
        following_ids = user.social_connections.following_ids[skip:skip+limit]
        return await self.model.find(
            In(self.model.id, following_ids)
        ).to_list()
    
    async def follow_user(
        self,
        follower_id: str,
        target_id: str
    ) -> bool:
        """Follow another user"""
        follower = await self.get_by_id(follower_id)
        target = await self.get_by_id(target_id)
        
        if not follower or not target:
            return False
        
        await follower.follow_user(PydanticObjectId(target_id))
        await target.add_follower(PydanticObjectId(follower_id))
        
        return True
    
    async def unfollow_user(
        self,
        follower_id: str,
        target_id: str
    ) -> bool:
        """Unfollow a user"""
        follower = await self.get_by_id(follower_id)
        target = await self.get_by_id(target_id)
        
        if not follower or not target:
            return False
        
        await follower.unfollow_user(PydanticObjectId(target_id))
        await target.remove_follower(PydanticObjectId(follower_id))
        
        return True
    
    async def is_following(
        self,
        follower_id: str,
        target_id: str
    ) -> bool:
        """Check if user is following another user"""
        user = await self.get_by_id(follower_id)
        if not user or not user.social_connections:
            return False
        return PydanticObjectId(target_id) in user.social_connections.following_ids
    
    # === Statistics ===
    
    async def update_user_stats(
        self,
        user_id: str,
        updates: Dict[str, Any]
    ) -> Optional[User]:
        """Update user statistics"""
        user = await self.get_by_id(user_id)
        if user:
            await user.update_stats(updates)
        return user
    
    async def increment_user_stat(
        self,
        user_id: str,
        stat_name: str,
        value: float = 1
    ) -> Optional[User]:
        """Increment a user stat"""
        user = await self.get_by_id(user_id)
        if user:
            await user.increment_stat(stat_name, value)
        return user
    
    # === Preferences ===
    
    async def update_preferences(
        self,
        user_id: str,
        preferences_data: Dict[str, Any]
    ) -> Optional[User]:
        """Update user preferences"""
        user = await self.get_by_id(user_id)
        if not user:
            return None
        
        if not user.preferences:
            user.preferences = UserPreferences()
        
        for field, value in preferences_data.items():
            if hasattr(user.preferences, field):
                setattr(user.preferences, field, value)
        
        user.updated_at = datetime.utcnow()
        await user.save()
        return user
    
    async def update_notification_preferences(
        self,
        user_id: str,
        preferences: Dict[str, bool]
    ) -> Optional[User]:
        """Update notification preferences"""
        user = await self.get_by_id(user_id)
        if user:
            user.notification_preferences.update(preferences)
            user.updated_at = datetime.utcnow()
            await user.save()
        return user
    
    # === Address Management ===
    
    async def add_address(
        self,
        user_id: str,
        address_data: Dict[str, Any]
    ) -> Optional[User]:
        """Add address to user"""
        user = await self.get_by_id(user_id)
        if not user:
            return None
        
        address = UserAddress(**address_data)
        
        # If this is primary, update others
        if address.is_primary:
            for addr in user.addresses:
                addr.is_primary = False
        
        user.addresses.append(address)
        user.updated_at = datetime.utcnow()
        await user.save()
        return user
    
    async def update_address(
        self,
        user_id: str,
        address_index: int,
        address_data: Dict[str, Any]
    ) -> Optional[User]:
        """Update user address by index"""
        user = await self.get_by_id(user_id)
        if not user or address_index >= len(user.addresses):
            return None
        
        for field, value in address_data.items():
            if hasattr(user.addresses[address_index], field):
                setattr(user.addresses[address_index], field, value)
        
        user.updated_at = datetime.utcnow()
        await user.save()
        return user
    
    async def remove_address(
        self,
        user_id: str,
        address_index: int
    ) -> Optional[User]:
        """Remove user address by index"""
        user = await self.get_by_id(user_id)
        if not user or address_index >= len(user.addresses):
            return None
        
        user.addresses.pop(address_index)
        user.updated_at = datetime.utcnow()
        await user.save()
        return user
    
    # === Referral ===
    
    async def get_by_referral_code(self, code: str) -> Optional[User]:
        """Get user by referral code"""
        return await self.model.find_one(
            {"referral_code": code, "is_deleted": False}
        )
    
    async def increment_referral_count(self, user_id: str) -> Optional[User]:
        """Increment user's referral count"""
        user = await self.get_by_id(user_id)
        if user:
            user.referral_count += 1
            await user.save()
        return user
    
    async def add_referral_credits(
        self,
        user_id: str,
        credits: float
    ) -> Optional[User]:
        """Add referral credits to user"""
        user = await self.get_by_id(user_id)
        if user:
            user.referral_credits += credits
            await user.save()
        return user
    
    # === Dashboard Stats ===
    
    async def get_dashboard_stats(self, user_id: str) -> Dict[str, Any]:
        """Get user dashboard statistics"""
        user = await self.get_by_id(user_id)
        if not user:
            return {}
        
        stats = user.stats or UserStats()
        
        return {
            "total_experiences": stats.total_experiences,
            "completed_experiences": stats.completed_experiences,
            "upcoming_experiences": stats.upcoming_experiences,
            "cancelled_experiences": stats.cancelled_experiences,
            "total_bookings": stats.total_bookings,
            "total_spent": stats.total_spent,
            "total_reviews": stats.total_reviews,
            "average_rating_given": stats.average_rating_given,
            "countries_visited": stats.countries_visited,
            "cities_visited": stats.cities_visited,
            "favorite_destinations_count": len(user.favorite_destinations),
            "favorite_vendors_count": len(user.favorite_vendors),
            "followers_count": user.followers_count,
            "following_count": user.following_count,
            "profile_completion": user.profile_completion_percentage,
        }
    
    # === Admin Stats ===
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get user statistics for admin dashboard"""
        pipeline = [
            {"$match": {"is_deleted": False}},
            {"$group": {
                "_id": None,
                "total": {"$sum": 1},
                "active": {"$sum": {"$cond": ["$is_active", 1, 0]}},
                "verified": {"$sum": {"$cond": ["$is_email_verified", 1, 0]}},
                "premium": {"$sum": {"$cond": ["$is_premium", 1, 0]}},
                "pending": {"$sum": {"$cond": [
                    {"$eq": ["$status", "pending"]}, 1, 0
                ]}},
                "with_agent": {"$sum": {"$cond": [
                    {"$ne": ["$assigned_agent_id", None]}, 1, 0
                ]}},
            }}
        ]
        
        result = await self.model.aggregate(pipeline).to_list()
        
        if result:
            return result[0]
        
        return {
            "total": 0,
            "active": 0,
            "verified": 0,
            "premium": 0,
            "pending": 0,
            "with_agent": 0
        }
    
    async def get_registration_stats(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> List[Dict[str, Any]]:
        """Get user registration stats by date"""
        pipeline = [
            {"$match": {
                "is_deleted": False,
                "created_at": {"$gte": start_date, "$lte": end_date}
            }},
            {"$group": {
                "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}},
                "count": {"$sum": 1}
            }},
            {"$sort": {"_id": 1}}
        ]
        
        return await self.model.aggregate(pipeline).to_list()


# Singleton instance
user_repository = UserRepository()
