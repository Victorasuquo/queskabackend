"""
Queska Backend - User Service
Comprehensive business logic layer for User operations
"""

import secrets
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from beanie import PydanticObjectId
from loguru import logger

from app.core.config import settings
from app.core.constants import AccountStatus, SubscriptionPlan
from app.core.exceptions import (
    AlreadyExistsError,
    AuthenticationError,
    InvalidCredentialsError,
    NotFoundError,
    ValidationError,
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
from app.models.user import (
    User,
    UserPreferences,
    UserAddress,
    UserSubscription,
    UserStats,
    UserSocialConnections,
)
from app.repositories.user_repository import user_repository
from app.repositories.vendor_repository import vendor_repository
from app.repositories.agent_repository import agent_repository
from app.schemas.user import (
    UserRegister,
    UserLogin,
    UserCreate,
    UserUpdate,
    UserListParams,
    UserPreferencesUpdate,
    UserNotificationPreferences,
)
from app.services.email_service import email_service


class UserService:
    """Service class for User business logic"""
    
    def __init__(self):
        self.repository = user_repository
    
    # === Authentication ===
    
    async def register(
        self,
        data: UserRegister,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> User:
        """
        Register a new user account
        
        Args:
            data: Registration data
            ip_address: Client IP address
            user_agent: Client user agent
            
        Returns:
            Created user
            
        Raises:
            AlreadyExistsError: If email is already registered
        """
        # Check if email exists
        if await self.repository.email_exists(data.email):
            raise AlreadyExistsError("User", "email", data.email)
        
        # Generate unique referral code
        referral_code = self._generate_referral_code()
        while await self.repository.referral_code_exists(referral_code):
            referral_code = self._generate_referral_code()
        
        # Create user
        user_data = {
            "email": data.email.lower(),
            "password_hash": hash_password(data.password),
            "first_name": data.first_name,
            "last_name": data.last_name,
            "phone": data.phone,
            "referral_code": referral_code,
            "status": AccountStatus.PENDING,
            "is_active": True,  # User is active on registration
            "subscription": UserSubscription(plan=SubscriptionPlan.FREE),
            "stats": UserStats(),
            "social_connections": UserSocialConnections(),
        }
        
        user = await self.repository.create_user(user_data)
        
        # Log activity
        await user.add_activity_log(
            action="register",
            description="User account created",
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        logger.info(f"New user registered: {user.email}")
        
        # Send verification email
        try:
            verification_token = create_verification_token(
                subject=str(user.id),
                user_type="user"
            )
            verification_url = f"{settings.FRONTEND_URL}/verify-email?token={verification_token}"
            
            email_result = await email_service.send_verification_email(
                to_email=user.email,
                to_name=user.full_name or user.first_name,
                verification_url=verification_url,
                token=verification_token
            )
            
            if email_result.success:
                logger.info(f"Verification email sent to: {user.email}")
            else:
                logger.warning(f"Failed to send verification email to {user.email}: {email_result.error}")
        except Exception as e:
            logger.error(f"Error sending verification email to {user.email}: {e}")
            # Don't fail registration if email fails - user can request resend
        
        return user
    
    async def login(
        self,
        data: UserLogin,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Authenticate user and return tokens
        
        Args:
            data: Login credentials
            ip_address: Client IP address
            user_agent: Client user agent
            
        Returns:
            Dictionary with tokens and user data
            
        Raises:
            InvalidCredentialsError: If credentials are invalid
            AuthenticationError: If account is not active
        """
        user = await self.repository.get_by_email(data.email)
        
        if not user:
            raise InvalidCredentialsError()
        
        if not verify_password(data.password, user.password_hash):
            raise InvalidCredentialsError()
        
        if user.status == AccountStatus.SUSPENDED:
            raise AuthenticationError("Your account has been suspended")
        
        if user.status == AccountStatus.DISABLED:
            raise AuthenticationError("Your account has been disabled")
        
        # Update last login
        await self.repository.update_last_login(str(user.id), ip_address, user_agent)
        
        # Generate tokens
        access_token = create_access_token(
            subject=str(user.id),
            user_type="user"
        )
        refresh_token = create_refresh_token(
            subject=str(user.id),
            user_type="user"
        )
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": 1800,  # 30 minutes
            "user": self._to_response(user)
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
        if not token_data or token_data.user_type != "user":
            raise AuthenticationError("Invalid refresh token")
        
        user = await self.repository.get_by_id(token_data.user_id)
        if not user or not user.is_active:
            raise AuthenticationError("Account not found or inactive")
        
        access_token = create_access_token(
            subject=str(user.id),
            user_type="user"
        )
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": 1800
        }
    
    async def logout(
        self,
        user_id: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> bool:
        """Log out user and record activity"""
        user = await self.repository.get_by_id(user_id)
        if user:
            await user.add_activity_log(
                action="logout",
                description="User logged out",
                ip_address=ip_address,
                user_agent=user_agent
            )
        return True
    
    # === OAuth ===
    
    async def google_auth(
        self,
        google_id: str,
        email: str,
        first_name: str,
        last_name: str,
        profile_photo: Optional[str] = None
    ) -> Tuple[User, bool]:
        """
        Authenticate or register user via Google OAuth
        
        Returns:
            Tuple of (user, is_new_user)
        """
        # Check if user exists with Google ID
        user = await self.repository.get_by_google_id(google_id)
        if user:
            await self.repository.update_last_login(str(user.id))
            return user, False
        
        # Check if user exists with email
        user = await self.repository.get_by_email(email)
        if user:
            # Link Google account
            user.google_id = google_id
            await user.save()
            await self.repository.update_last_login(str(user.id))
            return user, False
        
        # Create new user
        referral_code = self._generate_referral_code()
        user_data = {
            "email": email.lower(),
            "password_hash": hash_password(secrets.token_urlsafe(32)),
            "first_name": first_name,
            "last_name": last_name,
            "google_id": google_id,
            "profile_photo": profile_photo,
            "referral_code": referral_code,
            "status": AccountStatus.ACTIVE,
            "is_active": True,
            "is_email_verified": True,
            "email_verified_at": datetime.utcnow(),
            "subscription": UserSubscription(plan=SubscriptionPlan.FREE),
            "stats": UserStats(),
        }
        
        user = await self.repository.create_user(user_data)
        logger.info(f"New user registered via Google: {user.email}")
        
        return user, True
    
    async def google_oauth_callback(
        self,
        code: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Handle Google OAuth callback with authorization code.
        Exchanges code for tokens, fetches user info, creates/logs in user.
        
        Args:
            code: Authorization code from Google
            ip_address: Client IP address
            user_agent: Client user agent
            
        Returns:
            Dict with tokens and user data
        """
        import httpx
        
        # Exchange code for tokens
        token_data = {
            "code": code,
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "redirect_uri": settings.GOOGLE_REDIRECT_URI,
            "grant_type": "authorization_code",
        }
        
        async with httpx.AsyncClient() as client:
            # Get tokens from Google
            token_response = await client.post(
                "https://oauth2.googleapis.com/token",
                data=token_data
            )
            
            if token_response.status_code != 200:
                logger.error(f"Google token exchange failed: {token_response.text}")
                raise ValidationError("Failed to exchange authorization code")
            
            tokens = token_response.json()
            access_token = tokens.get("access_token")
            
            # Get user info from Google
            userinfo_response = await client.get(
                "https://www.googleapis.com/oauth2/v3/userinfo",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            
            if userinfo_response.status_code != 200:
                logger.error(f"Google userinfo failed: {userinfo_response.text}")
                raise ValidationError("Failed to get user info from Google")
            
            google_user = userinfo_response.json()
        
        # Extract user info
        google_id = google_user.get("sub")
        email = google_user.get("email")
        first_name = google_user.get("given_name", "")
        last_name = google_user.get("family_name", "")
        profile_photo = google_user.get("picture")
        
        if not email:
            raise ValidationError("Email not provided by Google")
        
        # Authenticate or create user
        user, is_new_user = await self.google_auth(
            google_id=google_id,
            email=email,
            first_name=first_name,
            last_name=last_name,
            profile_photo=profile_photo
        )
        
        # Update profile photo if it changed
        if profile_photo and user.profile_photo != profile_photo:
            user.profile_photo = profile_photo
            await user.save()
        
        # Log activity
        await user.add_activity_log(
            action="google_login",
            description="Logged in via Google OAuth",
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        # Send welcome email for new users
        if is_new_user:
            try:
                email_result = await email_service.send_welcome_email(
                    to_email=user.email,
                    to_name=user.full_name or user.first_name
                )
                if email_result.success:
                    logger.info(f"Welcome email sent to new Google user: {user.email}")
            except Exception as e:
                logger.error(f"Failed to send welcome email: {e}")
        
        # Generate JWT tokens
        jwt_access_token = create_access_token(
            subject=str(user.id),
            user_type="user"
        )
        jwt_refresh_token = create_refresh_token(
            subject=str(user.id),
            user_type="user"
        )
        
        return {
            "access_token": jwt_access_token,
            "refresh_token": jwt_refresh_token,
            "token_type": "bearer",
            "expires_in": 1800,
            "user": self._to_response(user),
            "is_new_user": is_new_user
        }
    
    async def google_id_token_auth(
        self,
        id_token: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Authenticate using a Google ID token (for mobile/frontend).
        Verifies the token with Google and creates/logs in user.
        
        Args:
            id_token: Google ID token from frontend
            ip_address: Client IP address
            user_agent: Client user agent
            
        Returns:
            Dict with tokens and user data
        """
        import httpx
        
        # Verify ID token with Google
        async with httpx.AsyncClient() as client:
            # Use Google's tokeninfo endpoint to verify
            verify_response = await client.get(
                f"https://oauth2.googleapis.com/tokeninfo?id_token={id_token}"
            )
            
            if verify_response.status_code != 200:
                logger.error(f"Google ID token verification failed: {verify_response.text}")
                raise AuthenticationError("Invalid Google ID token")
            
            token_info = verify_response.json()
        
        # Verify the token was issued for our app
        if token_info.get("aud") != settings.GOOGLE_CLIENT_ID:
            raise AuthenticationError("Token not issued for this application")
        
        # Extract user info
        google_id = token_info.get("sub")
        email = token_info.get("email")
        first_name = token_info.get("given_name", "")
        last_name = token_info.get("family_name", "")
        profile_photo = token_info.get("picture")
        
        if not email:
            raise ValidationError("Email not provided in token")
        
        # Authenticate or create user
        user, is_new_user = await self.google_auth(
            google_id=google_id,
            email=email,
            first_name=first_name,
            last_name=last_name,
            profile_photo=profile_photo
        )
        
        # Update profile photo if it changed
        if profile_photo and user.profile_photo != profile_photo:
            user.profile_photo = profile_photo
            await user.save()
        
        # Log activity
        await user.add_activity_log(
            action="google_login",
            description="Logged in via Google ID token",
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        # Send welcome email for new users
        if is_new_user:
            try:
                email_result = await email_service.send_welcome_email(
                    to_email=user.email,
                    to_name=user.full_name or user.first_name
                )
                if email_result.success:
                    logger.info(f"Welcome email sent to new Google user: {user.email}")
            except Exception as e:
                logger.error(f"Failed to send welcome email: {e}")
        
        # Generate JWT tokens
        jwt_access_token = create_access_token(
            subject=str(user.id),
            user_type="user"
        )
        jwt_refresh_token = create_refresh_token(
            subject=str(user.id),
            user_type="user"
        )
        
        return {
            "access_token": jwt_access_token,
            "refresh_token": jwt_refresh_token,
            "token_type": "bearer",
            "expires_in": 1800,
            "user": self._to_response(user),
            "is_new_user": is_new_user
        }

    async def facebook_auth(
        self,
        facebook_id: str,
        email: str,
        first_name: str,
        last_name: str,
        profile_photo: Optional[str] = None
    ) -> Tuple[User, bool]:
        """Authenticate or register user via Facebook OAuth"""
        user = await self.repository.get_by_facebook_id(facebook_id)
        if user:
            await self.repository.update_last_login(str(user.id))
            return user, False
        
        user = await self.repository.get_by_email(email)
        if user:
            user.facebook_id = facebook_id
            await user.save()
            await self.repository.update_last_login(str(user.id))
            return user, False
        
        referral_code = self._generate_referral_code()
        user_data = {
            "email": email.lower(),
            "password_hash": hash_password(secrets.token_urlsafe(32)),
            "first_name": first_name,
            "last_name": last_name,
            "facebook_id": facebook_id,
            "profile_photo": profile_photo,
            "referral_code": referral_code,
            "status": AccountStatus.ACTIVE,
            "is_active": True,
            "is_email_verified": True,
            "email_verified_at": datetime.utcnow(),
            "subscription": UserSubscription(plan=SubscriptionPlan.FREE),
            "stats": UserStats(),
        }
        
        user = await self.repository.create_user(user_data)
        logger.info(f"New user registered via Facebook: {user.email}")
        
        return user, True
    
    # === Email Verification ===
    
    async def request_email_verification(self, user_id: str) -> str:
        """Request email verification token"""
        user = await self.repository.get_by_id(user_id)
        if not user:
            raise NotFoundError("User", user_id)
        
        if user.is_email_verified:
            raise ValidationError("Email is already verified")
        
        token = create_verification_token(
            subject=str(user.id),
            user_type="user",
            purpose="email_verification"
        )
        
        # Send verification email
        try:
            verification_url = f"{settings.FRONTEND_URL}/verify-email?token={token}"
            
            email_result = await email_service.send_verification_email(
                to_email=user.email,
                to_name=user.full_name or user.first_name,
                verification_url=verification_url,
                token=token
            )
            
            if email_result.success:
                logger.info(f"Verification email sent to: {user.email}")
            else:
                logger.warning(f"Failed to send verification email to {user.email}: {email_result.error}")
        except Exception as e:
            logger.error(f"Error sending verification email to {user.email}: {e}")
        
        return token
    
    async def verify_email(self, token: str) -> User:
        """Verify email using token"""
        token_data = verify_token(token, "verification")
        if not token_data or token_data.user_type != "user":
            raise AuthenticationError("Invalid or expired verification token")
        
        user = await self.repository.verify_email(token_data.user_id)
        if not user:
            raise NotFoundError("User")
        
        logger.info(f"Email verified for user: {user.email}")
        
        # Send welcome email after verification
        try:
            email_result = await email_service.send_welcome_email(
                to_email=user.email,
                to_name=user.full_name or user.first_name
            )
            
            if email_result.success:
                logger.info(f"Welcome email sent to: {user.email}")
            else:
                logger.warning(f"Failed to send welcome email to {user.email}: {email_result.error}")
        except Exception as e:
            logger.error(f"Error sending welcome email to {user.email}: {e}")
        
        return user
    
    # === Password Management ===
    
    async def request_password_reset(self, email: str) -> str:
        """Request password reset token"""
        user = await self.repository.get_by_email(email)
        if not user:
            raise NotFoundError("User", email)
        
        token = create_password_reset_token(
            subject=str(user.id),
            user_type="user"
        )
        
        # Send password reset email
        try:
            reset_url = f"{settings.FRONTEND_URL}/reset-password?token={token}"
            
            email_result = await email_service.send_password_reset_email(
                to_email=user.email,
                to_name=user.full_name or user.first_name,
                reset_url=reset_url
            )
            
            if email_result.success:
                logger.info(f"Password reset email sent to: {user.email}")
            else:
                logger.warning(f"Failed to send password reset email to {user.email}: {email_result.error}")
        except Exception as e:
            logger.error(f"Error sending password reset email to {user.email}: {e}")
        
        return token
    
    async def reset_password(self, token: str, new_password: str) -> bool:
        """Reset password using token"""
        token_data = verify_token(token, "password_reset")
        if not token_data or token_data.user_type != "user":
            raise AuthenticationError("Invalid or expired reset token")
        
        user = await self.repository.get_by_id(token_data.user_id)
        if not user:
            raise NotFoundError("User")
        
        await self.repository.update_user(
            str(user.id),
            {"password_hash": hash_password(new_password)}
        )
        
        await user.add_activity_log(
            action="password_reset",
            description="Password was reset"
        )
        
        return True
    
    async def change_password(
        self,
        user_id: str,
        current_password: str,
        new_password: str,
        ip_address: Optional[str] = None
    ) -> bool:
        """Change user password"""
        user = await self.repository.get_by_id(user_id)
        if not user:
            raise NotFoundError("User", user_id)
        
        if not verify_password(current_password, user.password_hash):
            raise InvalidCredentialsError("Current password is incorrect")
        
        await self.repository.update_user(
            user_id,
            {"password_hash": hash_password(new_password)}
        )
        
        await user.add_activity_log(
            action="password_change",
            description="Password was changed",
            ip_address=ip_address
        )
        
        return True
    
    # === Profile Management ===
    
    async def get_user(self, user_id: str) -> User:
        """Get user by ID"""
        user = await self.repository.get_by_id(user_id)
        if not user:
            raise NotFoundError("User", user_id)
        return user
    
    async def get_user_by_email(self, email: str) -> User:
        """Get user by email"""
        user = await self.repository.get_by_email(email)
        if not user:
            raise NotFoundError("User", email)
        return user
    
    async def update_profile(
        self,
        user_id: str,
        data: UserUpdate
    ) -> User:
        """Update user profile"""
        user = await self.repository.get_by_id(user_id)
        if not user:
            raise NotFoundError("User", user_id)
        
        update_dict = data.model_dump(exclude_unset=True, exclude_none=True)
        
        # Handle nested address
        if "address" in update_dict and update_dict["address"]:
            address = UserAddress(**update_dict["address"])
            # Add or update primary address
            if user.addresses:
                for i, addr in enumerate(user.addresses):
                    if addr.is_primary:
                        user.addresses[i] = address
                        break
                else:
                    user.addresses.append(address)
            else:
                user.addresses = [address]
            del update_dict["address"]
        
        updated_user = await self.repository.update_user(user_id, update_dict)
        
        await updated_user.add_activity_log(
            action="profile_update",
            description="Profile was updated"
        )
        
        logger.info(f"User profile updated: {user_id}")
        
        return updated_user
    
    async def update_profile_photo(
        self,
        user_id: str,
        photo_url: str
    ) -> User:
        """Update user profile photo"""
        user = await self.repository.update_user(
            user_id,
            {"profile_photo": photo_url}
        )
        if not user:
            raise NotFoundError("User", user_id)
        
        return user
    
    async def update_cover_photo(
        self,
        user_id: str,
        photo_url: str
    ) -> User:
        """Update user cover photo"""
        user = await self.repository.update_user(
            user_id,
            {"cover_photo": photo_url}
        )
        if not user:
            raise NotFoundError("User", user_id)
        
        return user
    
    async def delete_user(
        self,
        user_id: str,
        reason: Optional[str] = None,
        soft: bool = True
    ) -> bool:
        """Delete user account"""
        user = await self.repository.get_by_id(user_id)
        if not user:
            raise NotFoundError("User", user_id)
        
        if soft:
            await user.soft_delete(reason)
        else:
            await self.repository.delete(user_id, soft=False)
        
        logger.info(f"User deleted: {user_id} (soft={soft})")
        
        return True
    
    # === Preferences ===
    
    async def update_preferences(
        self,
        user_id: str,
        data: UserPreferencesUpdate
    ) -> User:
        """Update user preferences"""
        preferences_data = data.model_dump(exclude_unset=True, exclude_none=True)
        user = await self.repository.update_preferences(user_id, preferences_data)
        if not user:
            raise NotFoundError("User", user_id)
        return user
    
    async def update_notification_preferences(
        self,
        user_id: str,
        preferences: Dict[str, bool]
    ) -> User:
        """Update notification preferences"""
        user = await self.repository.update_notification_preferences(
            user_id,
            preferences
        )
        if not user:
            raise NotFoundError("User", user_id)
        return user
    
    # === Favorites ===
    
    async def add_favorite_vendor(
        self,
        user_id: str,
        vendor_id: str
    ) -> User:
        """Add vendor to favorites"""
        # Verify vendor exists
        vendor = await vendor_repository.get_by_id(vendor_id)
        if not vendor:
            raise NotFoundError("Vendor", vendor_id)
        
        user = await self.repository.add_favorite_vendor(user_id, vendor_id)
        if not user:
            raise NotFoundError("User", user_id)
        
        # Increment vendor's favorite count
        await vendor_repository.increment_analytics(vendor_id, "total_favorites", 1)
        
        return user
    
    async def remove_favorite_vendor(
        self,
        user_id: str,
        vendor_id: str
    ) -> User:
        """Remove vendor from favorites"""
        user = await self.repository.remove_favorite_vendor(user_id, vendor_id)
        if not user:
            raise NotFoundError("User", user_id)
        return user
    
    async def add_favorite_destination(
        self,
        user_id: str,
        destination: str
    ) -> User:
        """Add destination to favorites"""
        user = await self.repository.add_favorite_destination(user_id, destination)
        if not user:
            raise NotFoundError("User", user_id)
        return user
    
    async def remove_favorite_destination(
        self,
        user_id: str,
        destination: str
    ) -> User:
        """Remove destination from favorites"""
        user = await self.repository.remove_favorite_destination(user_id, destination)
        if not user:
            raise NotFoundError("User", user_id)
        return user
    
    async def get_user_favorites(self, user_id: str) -> Dict[str, Any]:
        """Get user's favorites with details"""
        user = await self.get_user(user_id)
        
        # Get vendor details
        favorite_vendors = []
        for vendor_id in user.favorite_vendors:
            vendor = await vendor_repository.get_by_id(str(vendor_id))
            if vendor:
                favorite_vendors.append({
                    "id": str(vendor.id),
                    "business_name": vendor.business_name,
                    "slug": vendor.slug,
                    "category": vendor.category.value if vendor.category else None,
                    "logo": vendor.media.logo if vendor.media else None,
                    "rating": vendor.rating.average if vendor.rating else 0,
                })
        
        return {
            "favorite_vendors": favorite_vendors,
            "favorite_destinations": user.favorite_destinations
        }
    
    # === Social/Following ===
    
    async def follow_user(
        self,
        follower_id: str,
        target_id: str
    ) -> bool:
        """Follow another user"""
        if follower_id == target_id:
            raise ValidationError("Cannot follow yourself")
        
        # Check both users exist
        follower = await self.repository.get_by_id(follower_id)
        target = await self.repository.get_by_id(target_id)
        
        if not follower:
            raise NotFoundError("User", follower_id)
        if not target:
            raise NotFoundError("User", target_id)
        
        # Check if already following
        if await self.repository.is_following(follower_id, target_id):
            raise ValidationError("Already following this user")
        
        await self.repository.follow_user(follower_id, target_id)
        
        # TODO: Create notification for target user
        
        return True
    
    async def unfollow_user(
        self,
        follower_id: str,
        target_id: str
    ) -> bool:
        """Unfollow a user"""
        if follower_id == target_id:
            raise ValidationError("Cannot unfollow yourself")
        
        await self.repository.unfollow_user(follower_id, target_id)
        return True
    
    async def get_followers(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 20
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Get user's followers"""
        user = await self.get_user(user_id)
        followers = await self.repository.get_followers(user_id, skip, limit)
        
        return (
            [self._to_minimal_response(f) for f in followers],
            user.followers_count
        )
    
    async def get_following(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 20
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Get users that this user follows"""
        user = await self.get_user(user_id)
        following = await self.repository.get_following(user_id, skip, limit)
        
        return (
            [self._to_minimal_response(f) for f in following],
            user.following_count
        )
    
    # === Agent Assignment ===
    
    async def assign_agent(
        self,
        user_id: str,
        agent_id: str
    ) -> User:
        """Assign agent to user"""
        # Verify agent exists and can accept clients
        agent = await agent_repository.get_by_id(agent_id)
        if not agent:
            raise NotFoundError("Agent", agent_id)
        if not agent.can_accept_clients:
            raise ValidationError("Agent cannot accept more clients")
        
        # Assign agent
        user = await self.repository.assign_agent(user_id, agent_id)
        if not user:
            raise NotFoundError("User", user_id)
        
        # Add client to agent
        await agent_repository.add_client(agent_id, user_id)
        
        return user
    
    async def unassign_agent(self, user_id: str) -> User:
        """Remove agent assignment"""
        user = await self.get_user(user_id)
        
        if user.assigned_agent_id:
            # Remove from agent's clients
            await agent_repository.remove_client(
                str(user.assigned_agent_id),
                user_id
            )
        
        user = await self.repository.unassign_agent(user_id)
        return user
    
    # === Dashboard ===
    
    async def get_dashboard(self, user_id: str) -> Dict[str, Any]:
        """Get comprehensive user dashboard data"""
        user = await self.get_user(user_id)
        
        # Get stats
        stats = await self.repository.get_dashboard_stats(user_id)
        
        # Get assigned agent info
        assigned_agent = None
        if user.assigned_agent_id:
            agent = await agent_repository.get_by_id(str(user.assigned_agent_id))
            if agent:
                assigned_agent = {
                    "id": str(agent.id),
                    "name": agent.full_name,
                    "profile_photo": agent.media.profile_photo if agent.media else None,
                    "phone": agent.phone,
                    "email": agent.email,
                    "rating": agent.rating.average if agent.rating else 0,
                }
        
        # TODO: Get upcoming experiences, recent bookings, notifications
        # from respective services when implemented
        
        return {
            "stats": stats,
            "upcoming_experiences": [],  # TODO: Implement
            "recent_bookings": [],  # TODO: Implement
            "recent_notifications": [],  # TODO: Implement
            "recommended_destinations": [],  # TODO: Implement from AI
            "recommended_experiences": [],  # TODO: Implement from AI
            "assigned_agent": assigned_agent,
            "profile_completion": user.profile_completion_percentage,
            "is_email_verified": user.is_email_verified,
            "is_phone_verified": user.is_phone_verified,
        }
    
    async def get_activity_logs(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 20
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Get user activity logs"""
        user = await self.get_user(user_id)
        
        logs = user.activity_logs[skip:skip+limit]
        total = len(user.activity_logs)
        
        return (
            [
                {
                    "action": log.action,
                    "description": log.description,
                    "ip_address": log.ip_address,
                    "user_agent": log.user_agent,
                    "created_at": log.created_at.isoformat()
                }
                for log in reversed(logs)  # Most recent first
            ],
            total
        )
    
    # === Listing ===
    
    async def list_users(
        self,
        params: UserListParams
    ) -> Tuple[List[Dict[str, Any]], int, int]:
        """List users with filters and pagination"""
        users, total = await self.repository.list_users(params)
        pages = (total + params.limit - 1) // params.limit
        
        return (
            [self._to_minimal_response(u) for u in users],
            total,
            pages
        )
    
    # === Admin ===
    
    async def update_status(
        self,
        user_id: str,
        status: AccountStatus,
        reason: Optional[str] = None
    ) -> User:
        """Admin: Update user status"""
        user = await self.repository.update_status(user_id, status, reason)
        if not user:
            raise NotFoundError("User", user_id)
        
        logger.info(f"User status updated: {user_id} -> {status}")
        
        # TODO: Send notification
        
        return user
    
    async def get_user_stats(self) -> Dict[str, Any]:
        """Get user statistics for admin dashboard"""
        return await self.repository.get_stats()
    
    # === Helpers ===
    
    def _generate_referral_code(self) -> str:
        """Generate unique referral code"""
        return f"QU{secrets.token_hex(4).upper()}"
    
    def _to_response(self, user: User) -> Dict[str, Any]:
        """Convert user to full response"""
        return {
            "id": str(user.id),
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "display_name": user.display_name,
            "full_name": user.full_name,
            "phone": user.phone,
            "bio": user.bio,
            "profile_photo": user.profile_photo,
            "cover_photo": user.cover_photo,
            "date_of_birth": user.date_of_birth.isoformat() if user.date_of_birth else None,
            "gender": user.gender,
            "status": user.status.value if user.status else None,
            "is_email_verified": user.is_email_verified,
            "is_phone_verified": user.is_phone_verified,
            "is_active": user.is_active,
            "address": user.primary_address.model_dump() if user.primary_address else None,
            "preferences": user.preferences.model_dump() if user.preferences else None,
            "notification_preferences": user.notification_preferences,
            "subscription": user.subscription.model_dump() if user.subscription else None,
            "followers_count": user.followers_count,
            "following_count": user.following_count,
            "experiences_count": user.experiences_count,
            "reviews_count": user.reviews_count,
            "assigned_agent_id": str(user.assigned_agent_id) if user.assigned_agent_id else None,
            "favorite_destinations": user.favorite_destinations,
            "referral_code": user.referral_code,
            "profile_completion": user.profile_completion_percentage,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "updated_at": user.updated_at.isoformat() if user.updated_at else None,
            "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
        }
    
    def _to_minimal_response(self, user: User) -> Dict[str, Any]:
        """Convert user to minimal response"""
        return {
            "id": str(user.id),
            "first_name": user.first_name,
            "last_name": user.last_name,
            "display_name": user.display_name,
            "profile_photo": user.profile_photo,
            "is_email_verified": user.is_email_verified,
        }
    
    def _to_public_response(self, user: User) -> Dict[str, Any]:
        """Convert user to public response"""
        return user.to_public_dict()


# Singleton instance
user_service = UserService()

