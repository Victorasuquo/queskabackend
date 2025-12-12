"""
Queska Backend - Consultant Repository
Data access layer for Consultant operations
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from beanie import PydanticObjectId

from app.models.consultant import Consultant
from app.repositories.base import BaseRepository


class ConsultantRepository(BaseRepository):
    """Repository for Consultant document operations"""
    
    def __init__(self):
        super().__init__(Consultant)
    
    async def get_by_email(self, email: str) -> Optional[Consultant]:
        """Get consultant by email"""
        return await self.model.find_one(
            {"email": email.lower(), "is_deleted": False}
        )
    
    async def get_by_slug(self, slug: str) -> Optional[Consultant]:
        """Get consultant by slug"""
        return await self.model.find_one(
            {"slug": slug, "is_deleted": False}
        )
    
    async def email_exists(self, email: str, exclude_id: Optional[str] = None) -> bool:
        """Check if email exists"""
        return await self.exists("email", email.lower(), exclude_id)
    
    async def get_featured_consultants(self, limit: int = 10) -> List[Consultant]:
        """Get featured consultants"""
        return await self.model.find(
            {"is_featured": True, "is_deleted": False, "is_active": True}
        ).sort("-rating.average").limit(limit).to_list()
    
    async def get_available_consultants(self, limit: int = 20) -> List[Consultant]:
        """Get available consultants"""
        return await self.model.find(
            {
                "is_deleted": False,
                "is_active": True,
                "is_verified": True,
                "is_available": True
            }
        ).sort(("-is_featured", "-rating.average")).limit(limit).to_list()
    
    async def update_last_login(self, consultant_id: str) -> Optional[Consultant]:
        """Update consultant last login"""
        consultant = await self.get_by_id(consultant_id)
        if consultant:
            consultant.last_login_at = datetime.utcnow()
            await consultant.save()
        return consultant


# Singleton instance
consultant_repository = ConsultantRepository()

