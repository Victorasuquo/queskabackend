"""
Queska Backend - Vendor Repository
Data access layer for Vendor operations
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from beanie import PydanticObjectId
from beanie.odm.operators.find.comparison import In, GTE, LTE

from app.core.constants import AccountStatus, VendorCategory, VerificationStatus
from app.models.vendor import Vendor, VendorAddress, VendorVerification
from app.repositories.base import BaseRepository
from app.schemas.vendor import VendorListParams


class VendorRepository(BaseRepository[Vendor]):
    """Repository for Vendor document operations"""
    
    def __init__(self):
        super().__init__(Vendor)
    
    async def get_by_email(self, email: str) -> Optional[Vendor]:
        """
        Get vendor by email address
        
        Args:
            email: Vendor email
            
        Returns:
            Vendor or None
        """
        return await self.model.find_one(
            {"email": email.lower(), "is_deleted": False}
        )
    
    async def get_by_slug(self, slug: str) -> Optional[Vendor]:
        """
        Get vendor by URL slug
        
        Args:
            slug: Vendor slug
            
        Returns:
            Vendor or None
        """
        return await self.model.find_one(
            {"slug": slug, "is_deleted": False}
        )
    
    async def email_exists(
        self,
        email: str,
        exclude_id: Optional[str] = None
    ) -> bool:
        """
        Check if email is already registered
        
        Args:
            email: Email to check
            exclude_id: Optional vendor ID to exclude
            
        Returns:
            True if exists, False otherwise
        """
        return await self.exists("email", email.lower(), exclude_id)
    
    async def slug_exists(
        self,
        slug: str,
        exclude_id: Optional[str] = None
    ) -> bool:
        """
        Check if slug is already taken
        
        Args:
            slug: Slug to check
            exclude_id: Optional vendor ID to exclude
            
        Returns:
            True if exists, False otherwise
        """
        return await self.exists("slug", slug, exclude_id)
    
    async def create_vendor(self, data: Dict[str, Any]) -> Vendor:
        """
        Create a new vendor
        
        Args:
            data: Vendor data dictionary
            
        Returns:
            Created vendor
        """
        vendor = Vendor(**data)
        await vendor.insert()
        return vendor
    
    async def update_vendor(
        self,
        vendor_id: str,
        data: Dict[str, Any]
    ) -> Optional[Vendor]:
        """
        Update vendor by ID
        
        Args:
            vendor_id: Vendor ID
            data: Update data
            
        Returns:
            Updated vendor or None
        """
        vendor = await self.get_by_id(vendor_id)
        if not vendor:
            return None
        
        for field, value in data.items():
            if value is not None:
                setattr(vendor, field, value)
        
        vendor.updated_at = datetime.utcnow()
        await vendor.save()
        return vendor
    
    async def update_status(
        self,
        vendor_id: str,
        status: AccountStatus,
        reason: Optional[str] = None
    ) -> Optional[Vendor]:
        """
        Update vendor account status
        
        Args:
            vendor_id: Vendor ID
            status: New status
            reason: Optional reason for status change
            
        Returns:
            Updated vendor or None
        """
        vendor = await self.get_by_id(vendor_id)
        if not vendor:
            return None
        
        vendor.status = status
        vendor.is_active = status == AccountStatus.ACTIVE
        
        if reason:
            vendor.metadata["status_change_reason"] = reason
            vendor.metadata["status_changed_at"] = datetime.utcnow().isoformat()
        
        vendor.updated_at = datetime.utcnow()
        await vendor.save()
        return vendor
    
    async def update_verification(
        self,
        vendor_id: str,
        verification_data: Dict[str, Any]
    ) -> Optional[Vendor]:
        """
        Update vendor verification status
        
        Args:
            vendor_id: Vendor ID
            verification_data: Verification data
            
        Returns:
            Updated vendor or None
        """
        vendor = await self.get_by_id(vendor_id)
        if not vendor:
            return None
        
        if not vendor.verification:
            vendor.verification = VendorVerification()
        
        for field, value in verification_data.items():
            setattr(vendor.verification, field, value)
        
        vendor.verification.submitted_at = datetime.utcnow()
        vendor.updated_at = datetime.utcnow()
        await vendor.save()
        return vendor
    
    async def verify_vendor(
        self,
        vendor_id: str,
        admin_id: str,
        status: VerificationStatus,
        notes: Optional[str] = None,
        rejection_reason: Optional[str] = None
    ) -> Optional[Vendor]:
        """
        Admin: Verify or reject vendor
        
        Args:
            vendor_id: Vendor ID
            admin_id: Admin performing the review
            status: Verification status
            notes: Optional notes
            rejection_reason: Reason if rejected
            
        Returns:
            Updated vendor or None
        """
        vendor = await self.get_by_id(vendor_id)
        if not vendor:
            return None
        
        if not vendor.verification:
            vendor.verification = VendorVerification()
        
        vendor.verification.status = status
        vendor.verification.reviewed_at = datetime.utcnow()
        vendor.verification.reviewed_by = PydanticObjectId(admin_id)
        vendor.verification.notes = notes
        
        if status == VerificationStatus.VERIFIED:
            vendor.is_verified = True
            vendor.verified_at = datetime.utcnow()
            vendor.status = AccountStatus.ACTIVE
            vendor.is_active = True
        elif status == VerificationStatus.REJECTED:
            vendor.verification.rejection_reason = rejection_reason
        
        vendor.updated_at = datetime.utcnow()
        await vendor.save()
        return vendor
    
    async def update_last_login(self, vendor_id: str) -> Optional[Vendor]:
        """
        Update vendor last login timestamp
        
        Args:
            vendor_id: Vendor ID
            
        Returns:
            Updated vendor or None
        """
        vendor = await self.get_by_id(vendor_id)
        if vendor:
            vendor.last_login_at = datetime.utcnow()
            await vendor.save()
        return vendor
    
    async def list_vendors(
        self,
        params: VendorListParams
    ) -> Tuple[List[Vendor], int]:
        """
        List vendors with filters and pagination
        
        Args:
            params: List parameters
            
        Returns:
            Tuple of (vendors list, total count)
        """
        query: Dict[str, Any] = {"is_deleted": False}
        
        # Apply filters
        if params.search:
            query["$text"] = {"$search": params.search}
        
        if params.category:
            query["category"] = params.category
        
        if params.city:
            query["address.city"] = {"$regex": params.city, "$options": "i"}
        
        if params.state:
            query["address.state"] = {"$regex": params.state, "$options": "i"}
        
        if params.country:
            query["address.country"] = {"$regex": params.country, "$options": "i"}
        
        if params.is_verified is not None:
            query["is_verified"] = params.is_verified
        
        if params.is_featured is not None:
            query["is_featured"] = params.is_featured
        
        if params.is_premium is not None:
            query["is_premium"] = params.is_premium
        
        if params.min_rating:
            query["rating.average"] = {"$gte": params.min_rating}
        
        if params.max_price:
            query["price_range.max_price"] = {"$lte": params.max_price}
        
        if params.amenities:
            query["amenities"] = {"$all": params.amenities}
        
        # Geo query
        if params.latitude and params.longitude and params.radius_km:
            query["location"] = {
                "$near": {
                    "$geometry": {
                        "type": "Point",
                        "coordinates": [params.longitude, params.latitude]
                    },
                    "$maxDistance": params.radius_km * 1000
                }
            }
        
        # Sort
        sort_order = -1 if params.sort_order == "desc" else 1
        
        # Get total count
        total = await self.model.find(query).count()
        
        # Get paginated results
        skip = (params.page - 1) * params.limit
        vendors = await self.model.find(query) \
            .sort((params.sort_by, sort_order)) \
            .skip(skip) \
            .limit(params.limit) \
            .to_list()
        
        return vendors, total
    
    async def get_by_category(
        self,
        category: VendorCategory,
        skip: int = 0,
        limit: int = 20
    ) -> List[Vendor]:
        """
        Get vendors by category
        
        Args:
            category: Vendor category
            skip: Number to skip
            limit: Maximum results
            
        Returns:
            List of vendors
        """
        return await self.model.find(
            {"category": category, "is_deleted": False, "is_active": True}
        ).sort(["-is_featured", "-rating.average"]) \
            .skip(skip) \
            .limit(limit) \
            .to_list()
    
    async def get_featured_vendors(self, limit: int = 10) -> List[Vendor]:
        """
        Get featured vendors
        
        Args:
            limit: Maximum results
            
        Returns:
            List of featured vendors
        """
        return await self.model.find(
            {"is_featured": True, "is_deleted": False, "is_active": True}
        ).sort("-rating.average").limit(limit).to_list()
    
    async def get_nearby_vendors(
        self,
        longitude: float,
        latitude: float,
        radius_km: float = 10,
        category: Optional[VendorCategory] = None,
        limit: int = 20
    ) -> List[Vendor]:
        """
        Get vendors near a location
        
        Args:
            longitude: Longitude
            latitude: Latitude
            radius_km: Search radius in kilometers
            category: Optional category filter
            limit: Maximum results
            
        Returns:
            List of nearby vendors
        """
        query: Dict[str, Any] = {
            "is_deleted": False,
            "is_active": True,
            "location": {
                "$near": {
                    "$geometry": {
                        "type": "Point",
                        "coordinates": [longitude, latitude]
                    },
                    "$maxDistance": radius_km * 1000
                }
            }
        }
        
        if category:
            query["category"] = category
        
        return await self.model.find(query).limit(limit).to_list()
    
    async def get_vendors_by_ids(
        self,
        ids: List[str]
    ) -> List[Vendor]:
        """
        Get multiple vendors by IDs
        
        Args:
            ids: List of vendor IDs
            
        Returns:
            List of vendors
        """
        object_ids = [PydanticObjectId(id) for id in ids]
        return await self.model.find(
            In(self.model.id, object_ids),
            {"is_deleted": False}
        ).to_list()
    
    async def add_bank_account(
        self,
        vendor_id: str,
        bank_account: Dict[str, Any]
    ) -> Optional[Vendor]:
        """
        Add bank account to vendor
        
        Args:
            vendor_id: Vendor ID
            bank_account: Bank account data
            
        Returns:
            Updated vendor or None
        """
        from app.models.vendor import VendorBankAccount
        
        vendor = await self.get_by_id(vendor_id)
        if not vendor:
            return None
        
        account = VendorBankAccount(**bank_account)
        
        # If this is the first or marked as primary, update others
        if account.is_primary or not vendor.bank_accounts:
            for acc in vendor.bank_accounts:
                acc.is_primary = False
            account.is_primary = True
        
        vendor.bank_accounts.append(account)
        vendor.updated_at = datetime.utcnow()
        await vendor.save()
        return vendor
    
    async def update_analytics(
        self,
        vendor_id: str,
        analytics_data: Dict[str, Any]
    ) -> Optional[Vendor]:
        """
        Update vendor analytics
        
        Args:
            vendor_id: Vendor ID
            analytics_data: Analytics data to update
            
        Returns:
            Updated vendor or None
        """
        from app.models.vendor import VendorAnalytics
        
        vendor = await self.get_by_id(vendor_id)
        if not vendor:
            return None
        
        if not vendor.analytics:
            vendor.analytics = VendorAnalytics()
        
        for field, value in analytics_data.items():
            if hasattr(vendor.analytics, field):
                setattr(vendor.analytics, field, value)
        
        vendor.analytics.last_updated = datetime.utcnow()
        await vendor.save()
        return vendor
    
    async def increment_analytics(
        self,
        vendor_id: str,
        field: str,
        value: float = 1
    ) -> Optional[Vendor]:
        """
        Increment analytics field
        
        Args:
            vendor_id: Vendor ID
            field: Field to increment
            value: Increment value
            
        Returns:
            Updated vendor or None
        """
        result = await self.model.find_one({"_id": PydanticObjectId(vendor_id)})
        if result:
            await result.inc({f"analytics.{field}": value})
        return result
    
    async def get_stats(self) -> Dict[str, Any]:
        """
        Get vendor statistics for admin dashboard
        
        Returns:
            Dictionary with vendor stats
        """
        pipeline = [
            {"$match": {"is_deleted": False}},
            {"$group": {
                "_id": None,
                "total": {"$sum": 1},
                "active": {"$sum": {"$cond": ["$is_active", 1, 0]}},
                "verified": {"$sum": {"$cond": ["$is_verified", 1, 0]}},
                "featured": {"$sum": {"$cond": ["$is_featured", 1, 0]}},
                "pending": {"$sum": {"$cond": [
                    {"$eq": ["$status", "pending"]}, 1, 0
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
            "featured": 0,
            "pending": 0
        }
    
    async def get_category_distribution(self) -> List[Dict[str, Any]]:
        """
        Get vendor distribution by category
        
        Returns:
            List of category counts
        """
        pipeline = [
            {"$match": {"is_deleted": False, "is_active": True}},
            {"$group": {
                "_id": "$category",
                "count": {"$sum": 1}
            }},
            {"$sort": {"count": -1}}
        ]
        
        return await self.model.aggregate(pipeline).to_list()


# Singleton instance
vendor_repository = VendorRepository()

