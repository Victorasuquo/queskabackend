"""
Queska Backend - Vendor Service
Business logic layer for Vendor operations
"""

import secrets
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from beanie import PydanticObjectId
from loguru import logger
from python_slugify import slugify

from app.core.constants import AccountStatus, VendorCategory, VerificationStatus
from app.core.exceptions import (
    AlreadyExistsError,
    AuthenticationError,
    InvalidCredentialsError,
    NotFoundError,
    ValidationError,
    VendorError,
)
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    create_verification_token,
    create_password_reset_token,
    verify_token,
)
from app.models.vendor import (
    Vendor,
    VendorAddress,
    VendorContact,
    VendorSocialLinks,
    VendorOperatingHours,
    VendorMedia,
    VendorVerification,
    VendorSubscription,
    VendorAnalytics,
    VendorCommission,
)
from app.repositories.vendor_repository import vendor_repository
from app.schemas.vendor import (
    VendorRegister,
    VendorLogin,
    VendorCreate,
    VendorUpdate,
    VendorListParams,
    VendorResponse,
    VendorPublicResponse,
    VendorMinimalResponse,
    VendorTokenResponse,
    VendorVerificationCreate,
    VendorVerificationReview,
)


class VendorService:
    """Service class for Vendor business logic"""
    
    def __init__(self):
        self.repository = vendor_repository
    
    # === Authentication ===
    
    async def register(self, data: VendorRegister) -> Vendor:
        """
        Register a new vendor account
        
        Args:
            data: Registration data
            
        Returns:
            Created vendor
            
        Raises:
            AlreadyExistsError: If email is already registered
        """
        # Check if email exists
        if await self.repository.email_exists(data.email):
            raise AlreadyExistsError("Vendor", "email", data.email)
        
        # Generate unique slug
        base_slug = slugify(data.business_name)
        slug = base_slug
        counter = 1
        while await self.repository.slug_exists(slug):
            slug = f"{base_slug}-{counter}"
            counter += 1
        
        # Create vendor
        vendor_data = {
            "email": data.email.lower(),
            "password_hash": hash_password(data.password),
            "business_name": data.business_name,
            "slug": slug,
            "category": data.category,
            "owner_first_name": data.owner_first_name,
            "owner_last_name": data.owner_last_name,
            "owner_phone": data.owner_phone,
            "status": AccountStatus.PENDING,
            "is_verified": False,
            "is_active": False,
            "address": VendorAddress(
                city=data.city,
                state=data.state,
                country=data.country
            ),
            "verification": VendorVerification(status=VerificationStatus.PENDING),
            "subscription": VendorSubscription(),
            "analytics": VendorAnalytics(),
            "commission": VendorCommission(),
        }
        
        vendor = await self.repository.create_vendor(vendor_data)
        
        logger.info(f"New vendor registered: {vendor.email} ({vendor.business_name})")
        
        return vendor
    
    async def login(self, data: VendorLogin) -> Dict[str, Any]:
        """
        Authenticate vendor and return tokens
        
        Args:
            data: Login credentials
            
        Returns:
            Dictionary with tokens and vendor data
            
        Raises:
            InvalidCredentialsError: If credentials are invalid
            AuthenticationError: If account is not active
        """
        vendor = await self.repository.get_by_email(data.email)
        
        if not vendor:
            raise InvalidCredentialsError()
        
        if not verify_password(data.password, vendor.password_hash):
            raise InvalidCredentialsError()
        
        if vendor.status == AccountStatus.SUSPENDED:
            raise AuthenticationError("Your account has been suspended")
        
        if vendor.status == AccountStatus.DISABLED:
            raise AuthenticationError("Your account has been disabled")
        
        # Update last login
        await self.repository.update_last_login(str(vendor.id))
        
        # Generate tokens
        access_token = create_access_token(
            subject=str(vendor.id),
            user_type="vendor"
        )
        refresh_token = create_refresh_token(
            subject=str(vendor.id),
            user_type="vendor"
        )
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": 1800,  # 30 minutes
            "vendor": self._to_response(vendor)
        }
    
    async def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """
        Refresh access token using refresh token
        
        Args:
            refresh_token: Valid refresh token
            
        Returns:
            New access token
            
        Raises:
            AuthenticationError: If token is invalid
        """
        token_data = verify_token(refresh_token, "refresh")
        if not token_data or token_data.user_type != "vendor":
            raise AuthenticationError("Invalid refresh token")
        
        vendor = await self.repository.get_by_id(token_data.user_id)
        if not vendor or not vendor.is_active:
            raise AuthenticationError("Account not found or inactive")
        
        access_token = create_access_token(
            subject=str(vendor.id),
            user_type="vendor"
        )
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": 1800
        }
    
    async def request_password_reset(self, email: str) -> str:
        """
        Request password reset token
        
        Args:
            email: Vendor email
            
        Returns:
            Password reset token
            
        Raises:
            NotFoundError: If vendor not found
        """
        vendor = await self.repository.get_by_email(email)
        if not vendor:
            raise NotFoundError("Vendor", email)
        
        token = create_password_reset_token(
            subject=str(vendor.id),
            user_type="vendor"
        )
        
        # TODO: Send email with reset token
        
        return token
    
    async def reset_password(self, token: str, new_password: str) -> bool:
        """
        Reset password using token
        
        Args:
            token: Password reset token
            new_password: New password
            
        Returns:
            True if successful
            
        Raises:
            AuthenticationError: If token is invalid
        """
        token_data = verify_token(token, "password_reset")
        if not token_data or token_data.user_type != "vendor":
            raise AuthenticationError("Invalid or expired reset token")
        
        vendor = await self.repository.get_by_id(token_data.user_id)
        if not vendor:
            raise NotFoundError("Vendor")
        
        await self.repository.update_vendor(
            str(vendor.id),
            {"password_hash": hash_password(new_password)}
        )
        
        return True
    
    async def change_password(
        self,
        vendor_id: str,
        current_password: str,
        new_password: str
    ) -> bool:
        """
        Change vendor password
        
        Args:
            vendor_id: Vendor ID
            current_password: Current password
            new_password: New password
            
        Returns:
            True if successful
            
        Raises:
            InvalidCredentialsError: If current password is wrong
        """
        vendor = await self.repository.get_by_id(vendor_id)
        if not vendor:
            raise NotFoundError("Vendor", vendor_id)
        
        if not verify_password(current_password, vendor.password_hash):
            raise InvalidCredentialsError("Current password is incorrect")
        
        await self.repository.update_vendor(
            vendor_id,
            {"password_hash": hash_password(new_password)}
        )
        
        return True
    
    # === CRUD Operations ===
    
    async def get_vendor(self, vendor_id: str) -> Vendor:
        """
        Get vendor by ID
        
        Args:
            vendor_id: Vendor ID
            
        Returns:
            Vendor document
            
        Raises:
            NotFoundError: If vendor not found
        """
        vendor = await self.repository.get_by_id(vendor_id)
        if not vendor:
            raise NotFoundError("Vendor", vendor_id)
        return vendor
    
    async def get_vendor_by_slug(self, slug: str) -> Vendor:
        """
        Get vendor by slug
        
        Args:
            slug: Vendor slug
            
        Returns:
            Vendor document
            
        Raises:
            NotFoundError: If vendor not found
        """
        vendor = await self.repository.get_by_slug(slug)
        if not vendor:
            raise NotFoundError("Vendor", slug)
        return vendor
    
    async def get_vendor_by_email(self, email: str) -> Vendor:
        """
        Get vendor by email
        
        Args:
            email: Vendor email
            
        Returns:
            Vendor document
            
        Raises:
            NotFoundError: If vendor not found
        """
        vendor = await self.repository.get_by_email(email)
        if not vendor:
            raise NotFoundError("Vendor", email)
        return vendor
    
    async def update_vendor(
        self,
        vendor_id: str,
        data: VendorUpdate
    ) -> Vendor:
        """
        Update vendor profile
        
        Args:
            vendor_id: Vendor ID
            data: Update data
            
        Returns:
            Updated vendor
            
        Raises:
            NotFoundError: If vendor not found
        """
        vendor = await self.repository.get_by_id(vendor_id)
        if not vendor:
            raise NotFoundError("Vendor", vendor_id)
        
        update_dict = data.model_dump(exclude_unset=True, exclude_none=True)
        
        # Handle nested objects
        if "address" in update_dict and update_dict["address"]:
            update_dict["address"] = VendorAddress(**update_dict["address"])
        
        if "contact" in update_dict and update_dict["contact"]:
            update_dict["contact"] = VendorContact(**update_dict["contact"])
        
        if "social_links" in update_dict and update_dict["social_links"]:
            update_dict["social_links"] = VendorSocialLinks(**update_dict["social_links"])
        
        if "operating_hours" in update_dict and update_dict["operating_hours"]:
            update_dict["operating_hours"] = VendorOperatingHours(**update_dict["operating_hours"])
        
        # Update location GeoJSON if address has coordinates
        if "address" in update_dict:
            addr = update_dict["address"]
            if addr.latitude and addr.longitude:
                update_dict["location"] = {
                    "type": "Point",
                    "coordinates": [addr.longitude, addr.latitude]
                }
        
        updated_vendor = await self.repository.update_vendor(vendor_id, update_dict)
        
        logger.info(f"Vendor updated: {vendor_id}")
        
        return updated_vendor
    
    async def delete_vendor(self, vendor_id: str, soft: bool = True) -> bool:
        """
        Delete vendor account
        
        Args:
            vendor_id: Vendor ID
            soft: Use soft delete
            
        Returns:
            True if deleted
            
        Raises:
            NotFoundError: If vendor not found
        """
        vendor = await self.repository.get_by_id(vendor_id)
        if not vendor:
            raise NotFoundError("Vendor", vendor_id)
        
        result = await self.repository.delete(vendor_id, soft=soft)
        
        logger.info(f"Vendor deleted: {vendor_id} (soft={soft})")
        
        return result
    
    async def list_vendors(
        self,
        params: VendorListParams
    ) -> Tuple[List[VendorMinimalResponse], int, int]:
        """
        List vendors with filters and pagination
        
        Args:
            params: List parameters
            
        Returns:
            Tuple of (vendors, total count, total pages)
        """
        vendors, total = await self.repository.list_vendors(params)
        
        pages = (total + params.limit - 1) // params.limit
        
        return (
            [self._to_minimal_response(v) for v in vendors],
            total,
            pages
        )
    
    # === Verification ===
    
    async def submit_verification(
        self,
        vendor_id: str,
        data: VendorVerificationCreate
    ) -> Vendor:
        """
        Submit vendor verification documents
        
        Args:
            vendor_id: Vendor ID
            data: Verification documents
            
        Returns:
            Updated vendor
        """
        vendor = await self.get_vendor(vendor_id)
        
        verification_data = {
            "status": VerificationStatus.UNDER_REVIEW,
            "submitted_at": datetime.utcnow(),
            **data.model_dump(exclude_unset=True)
        }
        
        updated_vendor = await self.repository.update_verification(
            vendor_id,
            verification_data
        )
        
        logger.info(f"Vendor verification submitted: {vendor_id}")
        
        return updated_vendor
    
    async def review_verification(
        self,
        vendor_id: str,
        admin_id: str,
        data: VendorVerificationReview
    ) -> Vendor:
        """
        Admin: Review vendor verification
        
        Args:
            vendor_id: Vendor ID
            admin_id: Admin ID
            data: Review data
            
        Returns:
            Updated vendor
        """
        vendor = await self.get_vendor(vendor_id)
        
        updated_vendor = await self.repository.verify_vendor(
            vendor_id,
            admin_id,
            data.status,
            data.notes,
            data.rejection_reason
        )
        
        logger.info(f"Vendor verification reviewed: {vendor_id} - {data.status}")
        
        # TODO: Send notification to vendor about verification status
        
        return updated_vendor
    
    # === Status Management ===
    
    async def update_status(
        self,
        vendor_id: str,
        status: AccountStatus,
        reason: Optional[str] = None
    ) -> Vendor:
        """
        Update vendor account status
        
        Args:
            vendor_id: Vendor ID
            status: New status
            reason: Optional reason
            
        Returns:
            Updated vendor
        """
        vendor = await self.get_vendor(vendor_id)
        
        updated_vendor = await self.repository.update_status(
            vendor_id,
            status,
            reason
        )
        
        logger.info(f"Vendor status updated: {vendor_id} -> {status}")
        
        # TODO: Send notification to vendor
        
        return updated_vendor
    
    async def activate_vendor(self, vendor_id: str) -> Vendor:
        """Activate vendor account"""
        return await self.update_status(vendor_id, AccountStatus.ACTIVE)
    
    async def suspend_vendor(
        self,
        vendor_id: str,
        reason: Optional[str] = None
    ) -> Vendor:
        """Suspend vendor account"""
        return await self.update_status(
            vendor_id,
            AccountStatus.SUSPENDED,
            reason
        )
    
    async def disable_vendor(
        self,
        vendor_id: str,
        reason: Optional[str] = None
    ) -> Vendor:
        """Disable vendor account"""
        return await self.update_status(
            vendor_id,
            AccountStatus.DISABLED,
            reason
        )
    
    # === Feature Management ===
    
    async def toggle_featured(
        self,
        vendor_id: str,
        is_featured: bool
    ) -> Vendor:
        """Toggle vendor featured status"""
        vendor = await self.get_vendor(vendor_id)
        
        await self.repository.update_vendor(
            vendor_id,
            {"is_featured": is_featured}
        )
        
        logger.info(f"Vendor featured status: {vendor_id} -> {is_featured}")
        
        return await self.get_vendor(vendor_id)
    
    async def toggle_premium(
        self,
        vendor_id: str,
        is_premium: bool
    ) -> Vendor:
        """Toggle vendor premium status"""
        vendor = await self.get_vendor(vendor_id)
        
        await self.repository.update_vendor(
            vendor_id,
            {"is_premium": is_premium}
        )
        
        return await self.get_vendor(vendor_id)
    
    # === Media Management ===
    
    async def update_media(
        self,
        vendor_id: str,
        media_data: Dict[str, Any]
    ) -> Vendor:
        """
        Update vendor media (logo, cover, gallery)
        
        Args:
            vendor_id: Vendor ID
            media_data: Media data
            
        Returns:
            Updated vendor
        """
        vendor = await self.get_vendor(vendor_id)
        
        if not vendor.media:
            vendor.media = VendorMedia()
        
        for field, value in media_data.items():
            if hasattr(vendor.media, field):
                setattr(vendor.media, field, value)
        
        vendor.updated_at = datetime.utcnow()
        await vendor.save()
        
        return vendor
    
    # === Bank Account Management ===
    
    async def add_bank_account(
        self,
        vendor_id: str,
        bank_data: Dict[str, Any]
    ) -> Vendor:
        """
        Add bank account to vendor
        
        Args:
            vendor_id: Vendor ID
            bank_data: Bank account data
            
        Returns:
            Updated vendor
        """
        vendor = await self.get_vendor(vendor_id)
        
        updated_vendor = await self.repository.add_bank_account(
            vendor_id,
            bank_data
        )
        
        return updated_vendor
    
    # === Analytics ===
    
    async def get_vendor_stats(self) -> Dict[str, Any]:
        """Get vendor statistics for admin dashboard"""
        return await self.repository.get_stats()
    
    async def get_category_distribution(self) -> List[Dict[str, Any]]:
        """Get vendor distribution by category"""
        return await self.repository.get_category_distribution()
    
    async def update_vendor_analytics(
        self,
        vendor_id: str,
        analytics_data: Dict[str, Any]
    ) -> Vendor:
        """Update vendor analytics"""
        return await self.repository.update_analytics(vendor_id, analytics_data)
    
    async def increment_vendor_views(self, vendor_id: str) -> None:
        """Increment vendor profile views"""
        await self.repository.increment_analytics(vendor_id, "total_views", 1)
    
    async def increment_vendor_favorites(self, vendor_id: str) -> None:
        """Increment vendor favorites count"""
        await self.repository.increment_analytics(vendor_id, "total_favorites", 1)
    
    # === Search & Discovery ===
    
    async def get_featured_vendors(self, limit: int = 10) -> List[VendorMinimalResponse]:
        """Get featured vendors"""
        vendors = await self.repository.get_featured_vendors(limit)
        return [self._to_minimal_response(v) for v in vendors]
    
    async def get_vendors_by_category(
        self,
        category: VendorCategory,
        skip: int = 0,
        limit: int = 20
    ) -> List[VendorMinimalResponse]:
        """Get vendors by category"""
        vendors = await self.repository.get_by_category(category, skip, limit)
        return [self._to_minimal_response(v) for v in vendors]
    
    async def get_nearby_vendors(
        self,
        longitude: float,
        latitude: float,
        radius_km: float = 10,
        category: Optional[VendorCategory] = None,
        limit: int = 20
    ) -> List[VendorMinimalResponse]:
        """Get vendors near a location"""
        vendors = await self.repository.get_nearby_vendors(
            longitude,
            latitude,
            radius_km,
            category,
            limit
        )
        return [self._to_minimal_response(v) for v in vendors]
    
    # === Response Converters ===
    
    def _to_response(self, vendor: Vendor) -> Dict[str, Any]:
        """Convert vendor to full response"""
        return {
            "id": str(vendor.id),
            "email": vendor.email,
            "business_name": vendor.business_name,
            "slug": vendor.slug,
            "category": vendor.category.value if vendor.category else None,
            "subcategories": vendor.subcategories,
            "description": vendor.description,
            "short_description": vendor.short_description,
            "tagline": vendor.tagline,
            "owner_first_name": vendor.owner_first_name,
            "owner_last_name": vendor.owner_last_name,
            "owner_phone": vendor.owner_phone,
            "owner_email": vendor.owner_email,
            "status": vendor.status.value if vendor.status else None,
            "is_verified": vendor.is_verified,
            "is_featured": vendor.is_featured,
            "is_premium": vendor.is_premium,
            "is_active": vendor.is_active,
            "address": vendor.address.model_dump() if vendor.address else None,
            "contact": vendor.contact.model_dump() if vendor.contact else None,
            "social_links": vendor.social_links.model_dump() if vendor.social_links else None,
            "operating_hours": vendor.operating_hours.model_dump() if vendor.operating_hours else None,
            "media": vendor.media.model_dump() if vendor.media else None,
            "verification": vendor.verification.model_dump() if vendor.verification else None,
            "subscription": vendor.subscription.model_dump() if vendor.subscription else None,
            "rating": vendor.rating.model_dump() if vendor.rating else None,
            "analytics": vendor.analytics.model_dump() if vendor.analytics else None,
            "amenities": vendor.amenities,
            "services": vendor.services,
            "features": vendor.features,
            "tags": vendor.tags,
            "price_range": vendor.price_range,
            "currency": vendor.currency,
            "languages_spoken": vendor.languages_spoken,
            "cancellation_policy": vendor.cancellation_policy.value if vendor.cancellation_policy else None,
            "certifications": vendor.certifications,
            "awards": vendor.awards,
            "stripe_connected": vendor.stripe_connected,
            "payout_enabled": vendor.payout_enabled,
            "notification_preferences": vendor.notification_preferences,
            "created_at": vendor.created_at.isoformat() if vendor.created_at else None,
            "updated_at": vendor.updated_at.isoformat() if vendor.updated_at else None,
            "last_login_at": vendor.last_login_at.isoformat() if vendor.last_login_at else None,
            "verified_at": vendor.verified_at.isoformat() if vendor.verified_at else None,
        }
    
    def _to_minimal_response(self, vendor: Vendor) -> Dict[str, Any]:
        """Convert vendor to minimal response"""
        return {
            "id": str(vendor.id),
            "business_name": vendor.business_name,
            "slug": vendor.slug,
            "category": vendor.category.value if vendor.category else None,
            "short_description": vendor.short_description,
            "is_verified": vendor.is_verified,
            "is_featured": vendor.is_featured,
            "logo": vendor.media.logo if vendor.media else None,
            "city": vendor.address.city if vendor.address else None,
            "state": vendor.address.state if vendor.address else None,
            "rating": vendor.rating.model_dump() if vendor.rating else None,
            "price_range": vendor.price_range,
        }
    
    def _to_public_response(self, vendor: Vendor) -> Dict[str, Any]:
        """Convert vendor to public response (for customers)"""
        return vendor.to_public_dict()


# Singleton instance
vendor_service = VendorService()

