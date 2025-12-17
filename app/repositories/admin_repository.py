"""
Queska Backend - Admin Repository
Data access layer for Admin operations
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from beanie import PydanticObjectId

from app.core.constants import AccountStatus
from app.models.admin import Admin
from app.repositories.base import BaseRepository


class AdminRepository(BaseRepository[Admin]):
    """Repository for Admin document operations"""
    
    def __init__(self):
        super().__init__(Admin)
    
    # === Basic Queries ===
    
    async def get_by_email(self, email: str) -> Optional[Admin]:
        """Get admin by email"""
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
    
    async def get_by_user_id(self, user_id: str) -> Optional[Admin]:
        """Get admin by associated user ID"""
        return await self.model.find_one(
            {"user_id": PydanticObjectId(user_id), "is_deleted": False}
        )
    
    # === Admin CRUD ===
    
    async def create_admin(self, data: Dict[str, Any]) -> Admin:
        """Create a new admin"""
        admin = Admin(**data)
        await admin.insert()
        return admin
    
    async def update_admin(
        self,
        admin_id: str,
        data: Dict[str, Any]
    ) -> Optional[Admin]:
        """Update admin by ID"""
        admin = await self.get_by_id(admin_id)
        if not admin:
            return None
        
        for field, value in data.items():
            if value is not None:
                setattr(admin, field, value)
        
        admin.updated_at = datetime.utcnow()
        await admin.save()
        return admin
    
    async def update_status(
        self,
        admin_id: str,
        status: AccountStatus
    ) -> Optional[Admin]:
        """Update admin status"""
        admin = await self.get_by_id(admin_id)
        if not admin:
            return None
        
        admin.status = status
        admin.is_active = status == AccountStatus.ACTIVE
        admin.updated_at = datetime.utcnow()
        await admin.save()
        return admin
    
    async def update_last_login(
        self,
        admin_id: str,
        ip_address: Optional[str] = None
    ) -> Optional[Admin]:
        """Update admin last login"""
        admin = await self.get_by_id(admin_id)
        if admin:
            admin.last_login_at = datetime.utcnow()
            admin.last_active_at = datetime.utcnow()
            admin.login_count = (admin.login_count or 0) + 1
            
            # Log login activity
            if hasattr(admin, 'add_activity_log'):
                await admin.add_activity_log(
                    action="login",
                    description="Admin logged in",
                    ip_address=ip_address
                )
            else:
                await admin.save()
        
        return admin
    
    # === Permissions ===
    
    async def add_permission(
        self,
        admin_id: str,
        permission: str
    ) -> Optional[Admin]:
        """Add permission to admin"""
        admin = await self.get_by_id(admin_id)
        if not admin:
            return None
        
        if permission not in admin.permissions:
            admin.permissions.append(permission)
            admin.updated_at = datetime.utcnow()
            await admin.save()
        
        return admin
    
    async def remove_permission(
        self,
        admin_id: str,
        permission: str
    ) -> Optional[Admin]:
        """Remove permission from admin"""
        admin = await self.get_by_id(admin_id)
        if not admin:
            return None
        
        if permission in admin.permissions:
            admin.permissions.remove(permission)
            admin.updated_at = datetime.utcnow()
            await admin.save()
        
        return admin
    
    async def set_permissions(
        self,
        admin_id: str,
        permissions: List[str]
    ) -> Optional[Admin]:
        """Set admin permissions"""
        admin = await self.get_by_id(admin_id)
        if not admin:
            return None
        
        admin.permissions = permissions
        admin.updated_at = datetime.utcnow()
        await admin.save()
        return admin
    
    async def has_permission(
        self,
        admin_id: str,
        permission: str
    ) -> bool:
        """Check if admin has permission"""
        admin = await self.get_by_id(admin_id)
        if not admin:
            return False
        
        if admin.is_super_admin:
            return True
        
        return permission in admin.permissions
    
    # === Listing ===
    
    async def list_admins(
        self,
        skip: int = 0,
        limit: int = 100,
        status: Optional[AccountStatus] = None,
        is_super_admin: Optional[bool] = None,
        sort_by: str = "created_at",
        sort_order: int = -1
    ) -> Tuple[List[Admin], int]:
        """List admins with filters"""
        query: Dict[str, Any] = {"is_deleted": False}
        
        if status:
            query["status"] = status
        
        if is_super_admin is not None:
            query["is_super_admin"] = is_super_admin
        
        total = await self.model.find(query).count()
        
        admins = await self.model.find(query) \
            .sort((sort_by, sort_order)) \
            .skip(skip) \
            .limit(limit) \
            .to_list()
        
        return admins, total
    
    async def get_super_admins(self) -> List[Admin]:
        """Get all super admins"""
        return await self.model.find(
            {"is_super_admin": True, "is_deleted": False}
        ).to_list()
    
    # === Stats ===
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get admin statistics"""
        pipeline = [
            {"$match": {"is_deleted": False}},
            {"$group": {
                "_id": None,
                "total": {"$sum": 1},
                "active": {"$sum": {"$cond": ["$is_active", 1, 0]}},
                "super_admins": {"$sum": {"$cond": ["$is_super_admin", 1, 0]}},
            }}
        ]
        
        result = await self.model.aggregate(pipeline).to_list()
        
        if result:
            return result[0]
        
        return {
            "total": 0,
            "active": 0,
            "super_admins": 0
        }


# Singleton instance
admin_repository = AdminRepository()
