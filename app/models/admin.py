"""
Queska Backend - Admin Document Model
Platform administrators with full or limited access
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from beanie import Document, Indexed, PydanticObjectId
from pydantic import EmailStr, Field

from app.core.constants import AccountStatus


class AdminActivityLog(Document):
    """Admin activity log entry"""
    action: str
    description: str
    target_type: Optional[str] = None  # user, vendor, agent, etc.
    target_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Settings:
        name = "admin_activity_logs"


class Admin(Document):
    """
    Admin Document Model
    Platform administrators with configurable permissions
    """
    
    # Account Credentials
    email: Indexed(EmailStr, unique=True)
    password_hash: str
    
    # Profile
    first_name: str
    last_name: str
    display_name: Optional[str] = None
    phone: Optional[str] = None
    profile_photo: Optional[str] = None
    
    # Association (optional link to User document)
    user_id: Optional[PydanticObjectId] = None
    
    # Status
    status: AccountStatus = AccountStatus.ACTIVE
    is_active: bool = True
    is_super_admin: bool = False
    
    # Permissions
    permissions: List[str] = Field(default_factory=list)
    # Available permissions:
    # - manage_users
    # - manage_vendors
    # - manage_agents
    # - manage_admins
    # - manage_experiences
    # - manage_bookings
    # - manage_payments
    # - manage_reviews
    # - manage_notifications
    # - manage_content
    # - view_analytics
    # - manage_settings
    # - manage_support
    
    # Department/Role
    department: Optional[str] = None
    role: Optional[str] = None
    
    # Security
    two_factor_enabled: bool = False
    two_factor_secret: Optional[str] = None
    password_changed_at: Optional[datetime] = None
    must_change_password: bool = False
    
    # Activity
    activity_logs: List[AdminActivityLog] = Field(default_factory=list)
    login_count: int = 0
    last_active_at: Optional[datetime] = None
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_login_at: Optional[datetime] = None
    
    # Soft delete
    is_deleted: bool = False
    deleted_at: Optional[datetime] = None
    deleted_by: Optional[PydanticObjectId] = None
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    class Settings:
        name = "admins"
        indexes = [
            "email",
            "status",
            "is_active",
            "is_super_admin",
            "department",
        ]
    
    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"
    
    def has_permission(self, permission: str) -> bool:
        """Check if admin has a specific permission"""
        if self.is_super_admin:
            return True
        return permission in self.permissions
    
    def has_any_permission(self, permissions: List[str]) -> bool:
        """Check if admin has any of the given permissions"""
        if self.is_super_admin:
            return True
        return any(p in self.permissions for p in permissions)
    
    def has_all_permissions(self, permissions: List[str]) -> bool:
        """Check if admin has all of the given permissions"""
        if self.is_super_admin:
            return True
        return all(p in self.permissions for p in permissions)
    
    async def add_activity_log(
        self,
        action: str,
        description: str,
        target_type: Optional[str] = None,
        target_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> None:
        """Add activity log entry"""
        log = AdminActivityLog(
            action=action,
            description=description,
            target_type=target_type,
            target_id=target_id,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        # Keep only last 500 activity logs
        if len(self.activity_logs) >= 500:
            self.activity_logs = self.activity_logs[-499:]
        
        self.activity_logs.append(log)
        await self.save()
    
    async def soft_delete(self, deleted_by: Optional[str] = None) -> None:
        """Soft delete the admin"""
        self.is_deleted = True
        self.deleted_at = datetime.utcnow()
        if deleted_by:
            self.deleted_by = PydanticObjectId(deleted_by)
        self.is_active = False
        await self.save()
