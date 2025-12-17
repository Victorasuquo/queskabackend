"""
Queska Backend - Agent Service
Business logic layer for Agent operations
"""

import secrets
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from beanie import PydanticObjectId
from loguru import logger
from slugify import slugify

from app.core.constants import AccountStatus, AgentType, VerificationStatus
from app.core.exceptions import (
    AgentError,
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
from app.models.agent import (
    Agent,
    AgentAddress,
    AgentContact,
    AgentSocialLinks,
    AgentMedia,
    AgentVerification,
    AgentSubscription,
    AgentAnalytics,
    AgentCommission,
    AgentSpecialization,
)
from app.repositories.agent_repository import agent_repository
from app.schemas.agent import (
    AgentRegister,
    AgentLogin,
    AgentCreate,
    AgentUpdate,
    AgentListParams,
    AgentResponse,
    AgentPublicResponse,
    AgentMinimalResponse,
    AgentTokenResponse,
    AgentVerificationCreate,
    AgentVerificationReview,
)


class AgentService:
    """Service class for Agent business logic"""
    
    def __init__(self):
        self.repository = agent_repository
    
    # === Authentication ===
    
    async def register(self, data: AgentRegister) -> Agent:
        """
        Register a new agent account
        
        Args:
            data: Registration data
            
        Returns:
            Created agent
            
        Raises:
            AlreadyExistsError: If email is already registered
        """
        # Check if email exists
        if await self.repository.email_exists(data.email):
            raise AlreadyExistsError("Agent", "email", data.email)
        
        # Generate unique slug
        base_slug = slugify(f"{data.first_name}-{data.last_name}")
        slug = base_slug
        counter = 1
        while await self.repository.slug_exists(slug):
            slug = f"{base_slug}-{counter}"
            counter += 1
        
        # Generate unique referral code
        referral_code = self._generate_referral_code()
        while await self.repository.referral_code_exists(referral_code):
            referral_code = self._generate_referral_code()
        
        # Check for referrer
        referred_by = None
        if data.referral_code:
            referrer = await self.repository.get_by_referral_code(data.referral_code)
            if referrer:
                referred_by = referrer.id
        
        # Create agent
        agent_data = {
            "email": data.email.lower(),
            "password_hash": hash_password(data.password),
            "first_name": data.first_name,
            "last_name": data.last_name,
            "phone": data.phone,
            "slug": slug,
            "agent_type": data.agent_type,
            "referral_code": referral_code,
            "referred_by": referred_by,
            "status": AccountStatus.PENDING,
            "is_verified": False,
            "is_active": True,  # Active but pending verification
            "address": AgentAddress(
                city=data.city,
                state=data.state,
                country=data.country
            ),
            "verification": AgentVerification(status=VerificationStatus.PENDING),
            "subscription": AgentSubscription(),
            "analytics": AgentAnalytics(),
            "commission": AgentCommission(),
            "specialization": AgentSpecialization(),
        }
        
        agent = await self.repository.create_agent(agent_data)
        
        # Update referrer's referral count
        if referred_by:
            await self.repository.increment_referral(str(referred_by))
        
        logger.info(f"New agent registered: {agent.email}")
        
        return agent
    
    async def login(self, data: AgentLogin) -> Dict[str, Any]:
        """
        Authenticate agent and return tokens
        
        Args:
            data: Login credentials
            
        Returns:
            Dictionary with tokens and agent data
            
        Raises:
            InvalidCredentialsError: If credentials are invalid
            AuthenticationError: If account is not active
        """
        agent = await self.repository.get_by_email(data.email)
        
        if not agent:
            raise InvalidCredentialsError()
        
        if not verify_password(data.password, agent.password_hash):
            raise InvalidCredentialsError()
        
        if agent.status == AccountStatus.SUSPENDED:
            raise AuthenticationError("Your account has been suspended")
        
        if agent.status == AccountStatus.DISABLED:
            raise AuthenticationError("Your account has been disabled")
        
        # Update last login
        await self.repository.update_last_login(str(agent.id))
        
        # Generate tokens
        access_token = create_access_token(
            subject=str(agent.id),
            user_type="agent"
        )
        refresh_token = create_refresh_token(
            subject=str(agent.id),
            user_type="agent"
        )
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": 1800,
            "agent": self._to_response(agent)
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
        if not token_data or token_data.user_type != "agent":
            raise AuthenticationError("Invalid refresh token")
        
        agent = await self.repository.get_by_id(token_data.user_id)
        if not agent or not agent.is_active:
            raise AuthenticationError("Account not found or inactive")
        
        access_token = create_access_token(
            subject=str(agent.id),
            user_type="agent"
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
            email: Agent email
            
        Returns:
            Password reset token
            
        Raises:
            NotFoundError: If agent not found
        """
        agent = await self.repository.get_by_email(email)
        if not agent:
            raise NotFoundError("Agent", email)
        
        token = create_password_reset_token(
            subject=str(agent.id),
            user_type="agent"
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
        if not token_data or token_data.user_type != "agent":
            raise AuthenticationError("Invalid or expired reset token")
        
        agent = await self.repository.get_by_id(token_data.user_id)
        if not agent:
            raise NotFoundError("Agent")
        
        await self.repository.update_agent(
            str(agent.id),
            {"password_hash": hash_password(new_password)}
        )
        
        return True
    
    async def change_password(
        self,
        agent_id: str,
        current_password: str,
        new_password: str
    ) -> bool:
        """
        Change agent password
        
        Args:
            agent_id: Agent ID
            current_password: Current password
            new_password: New password
            
        Returns:
            True if successful
            
        Raises:
            InvalidCredentialsError: If current password is wrong
        """
        agent = await self.repository.get_by_id(agent_id)
        if not agent:
            raise NotFoundError("Agent", agent_id)
        
        if not verify_password(current_password, agent.password_hash):
            raise InvalidCredentialsError("Current password is incorrect")
        
        await self.repository.update_agent(
            agent_id,
            {"password_hash": hash_password(new_password)}
        )
        
        return True
    
    # === CRUD Operations ===
    
    async def get_agent(self, agent_id: str) -> Agent:
        """
        Get agent by ID
        
        Args:
            agent_id: Agent ID
            
        Returns:
            Agent document
            
        Raises:
            NotFoundError: If agent not found
        """
        agent = await self.repository.get_by_id(agent_id)
        if not agent:
            raise NotFoundError("Agent", agent_id)
        return agent
    
    async def get_agent_by_slug(self, slug: str) -> Agent:
        """
        Get agent by slug
        
        Args:
            slug: Agent slug
            
        Returns:
            Agent document
            
        Raises:
            NotFoundError: If agent not found
        """
        agent = await self.repository.get_by_slug(slug)
        if not agent:
            raise NotFoundError("Agent", slug)
        return agent
    
    async def get_agent_by_email(self, email: str) -> Agent:
        """
        Get agent by email
        
        Args:
            email: Agent email
            
        Returns:
            Agent document
            
        Raises:
            NotFoundError: If agent not found
        """
        agent = await self.repository.get_by_email(email)
        if not agent:
            raise NotFoundError("Agent", email)
        return agent
    
    async def update_agent(
        self,
        agent_id: str,
        data: AgentUpdate
    ) -> Agent:
        """
        Update agent profile
        
        Args:
            agent_id: Agent ID
            data: Update data
            
        Returns:
            Updated agent
            
        Raises:
            NotFoundError: If agent not found
        """
        agent = await self.repository.get_by_id(agent_id)
        if not agent:
            raise NotFoundError("Agent", agent_id)
        
        update_dict = data.model_dump(exclude_unset=True, exclude_none=True)
        
        # Handle nested objects
        if "address" in update_dict and update_dict["address"]:
            update_dict["address"] = AgentAddress(**update_dict["address"])
        
        if "contact" in update_dict and update_dict["contact"]:
            update_dict["contact"] = AgentContact(**update_dict["contact"])
        
        if "social_links" in update_dict and update_dict["social_links"]:
            update_dict["social_links"] = AgentSocialLinks(**update_dict["social_links"])
        
        if "specialization" in update_dict and update_dict["specialization"]:
            update_dict["specialization"] = AgentSpecialization(**update_dict["specialization"])
        
        # Update location GeoJSON if address has coordinates
        if "address" in update_dict:
            addr = update_dict["address"]
            if addr.latitude and addr.longitude:
                update_dict["location"] = {
                    "type": "Point",
                    "coordinates": [addr.longitude, addr.latitude]
                }
        
        updated_agent = await self.repository.update_agent(agent_id, update_dict)
        
        logger.info(f"Agent updated: {agent_id}")
        
        return updated_agent
    
    async def delete_agent(self, agent_id: str, soft: bool = True) -> bool:
        """
        Delete agent account
        
        Args:
            agent_id: Agent ID
            soft: Use soft delete
            
        Returns:
            True if deleted
            
        Raises:
            NotFoundError: If agent not found
        """
        agent = await self.repository.get_by_id(agent_id)
        if not agent:
            raise NotFoundError("Agent", agent_id)
        
        result = await self.repository.delete(agent_id, soft=soft)
        
        logger.info(f"Agent deleted: {agent_id} (soft={soft})")
        
        return result
    
    async def list_agents(
        self,
        params: AgentListParams
    ) -> Tuple[List[AgentMinimalResponse], int, int]:
        """
        List agents with filters and pagination
        
        Args:
            params: List parameters
            
        Returns:
            Tuple of (agents, total count, total pages)
        """
        agents, total = await self.repository.list_agents(params)
        
        pages = (total + params.limit - 1) // params.limit
        
        return (
            [self._to_minimal_response(a) for a in agents],
            total,
            pages
        )
    
    # === Client Management ===
    
    async def add_client(
        self,
        agent_id: str,
        client_id: str
    ) -> Agent:
        """
        Add client to agent
        
        Args:
            agent_id: Agent ID
            client_id: Client user ID
            
        Returns:
            Updated agent
            
        Raises:
            AgentError: If agent cannot accept more clients
        """
        agent = await self.get_agent(agent_id)
        
        if not agent.can_accept_clients:
            raise AgentError(
                "Agent cannot accept more clients",
                {"max_clients": agent.max_clients}
            )
        
        updated_agent = await self.repository.add_client(agent_id, client_id)
        
        if not updated_agent:
            raise AgentError("Failed to add client")
        
        logger.info(f"Client {client_id} added to agent {agent_id}")
        
        return updated_agent
    
    async def remove_client(
        self,
        agent_id: str,
        client_id: str
    ) -> Agent:
        """
        Remove client from agent
        
        Args:
            agent_id: Agent ID
            client_id: Client user ID
            
        Returns:
            Updated agent
        """
        agent = await self.get_agent(agent_id)
        
        updated_agent = await self.repository.remove_client(agent_id, client_id)
        
        logger.info(f"Client {client_id} removed from agent {agent_id}")
        
        return updated_agent
    
    async def get_agent_clients(self, agent_id: str) -> List[str]:
        """
        Get list of agent's client IDs
        
        Args:
            agent_id: Agent ID
            
        Returns:
            List of client IDs
        """
        client_ids = await self.repository.get_agent_clients(agent_id)
        return [str(cid) for cid in client_ids]
    
    # === Verification ===
    
    async def submit_verification(
        self,
        agent_id: str,
        data: AgentVerificationCreate
    ) -> Agent:
        """
        Submit agent verification documents
        
        Args:
            agent_id: Agent ID
            data: Verification documents
            
        Returns:
            Updated agent
        """
        agent = await self.get_agent(agent_id)
        
        verification_data = {
            "status": VerificationStatus.UNDER_REVIEW,
            "submitted_at": datetime.utcnow(),
            **data.model_dump(exclude_unset=True)
        }
        
        updated_agent = await self.repository.update_verification(
            agent_id,
            verification_data
        )
        
        logger.info(f"Agent verification submitted: {agent_id}")
        
        return updated_agent
    
    async def review_verification(
        self,
        agent_id: str,
        admin_id: str,
        data: AgentVerificationReview
    ) -> Agent:
        """
        Admin: Review agent verification
        
        Args:
            agent_id: Agent ID
            admin_id: Admin ID
            data: Review data
            
        Returns:
            Updated agent
        """
        agent = await self.get_agent(agent_id)
        
        updated_agent = await self.repository.verify_agent(
            agent_id,
            admin_id,
            data.status,
            data.notes,
            data.rejection_reason
        )
        
        logger.info(f"Agent verification reviewed: {agent_id} - {data.status}")
        
        # TODO: Send notification to agent
        
        return updated_agent
    
    # === Status Management ===
    
    async def update_status(
        self,
        agent_id: str,
        status: AccountStatus,
        reason: Optional[str] = None
    ) -> Agent:
        """
        Update agent account status
        
        Args:
            agent_id: Agent ID
            status: New status
            reason: Optional reason
            
        Returns:
            Updated agent
        """
        agent = await self.get_agent(agent_id)
        
        updated_agent = await self.repository.update_status(
            agent_id,
            status,
            reason
        )
        
        logger.info(f"Agent status updated: {agent_id} -> {status}")
        
        # TODO: Send notification
        
        return updated_agent
    
    async def activate_agent(self, agent_id: str) -> Agent:
        """Activate agent account"""
        return await self.update_status(agent_id, AccountStatus.ACTIVE)
    
    async def suspend_agent(
        self,
        agent_id: str,
        reason: Optional[str] = None
    ) -> Agent:
        """Suspend agent account"""
        return await self.update_status(
            agent_id,
            AccountStatus.SUSPENDED,
            reason
        )
    
    async def toggle_availability(
        self,
        agent_id: str,
        is_available: bool
    ) -> Agent:
        """Toggle agent availability"""
        agent = await self.get_agent(agent_id)
        
        await self.repository.update_agent(
            agent_id,
            {"is_available": is_available}
        )
        
        return await self.get_agent(agent_id)
    
    # === Feature Management ===
    
    async def toggle_featured(
        self,
        agent_id: str,
        is_featured: bool
    ) -> Agent:
        """Toggle agent featured status"""
        agent = await self.get_agent(agent_id)
        
        await self.repository.update_agent(
            agent_id,
            {"is_featured": is_featured}
        )
        
        logger.info(f"Agent featured status: {agent_id} -> {is_featured}")
        
        return await self.get_agent(agent_id)
    
    async def toggle_premium(
        self,
        agent_id: str,
        is_premium: bool
    ) -> Agent:
        """Toggle agent premium status"""
        agent = await self.get_agent(agent_id)
        
        await self.repository.update_agent(
            agent_id,
            {"is_premium": is_premium}
        )
        
        return await self.get_agent(agent_id)
    
    # === Media Management ===
    
    async def update_media(
        self,
        agent_id: str,
        media_data: Dict[str, Any]
    ) -> Agent:
        """
        Update agent media
        
        Args:
            agent_id: Agent ID
            media_data: Media data
            
        Returns:
            Updated agent
        """
        agent = await self.get_agent(agent_id)
        
        if not agent.media:
            agent.media = AgentMedia()
        
        for field, value in media_data.items():
            if hasattr(agent.media, field):
                setattr(agent.media, field, value)
        
        agent.updated_at = datetime.utcnow()
        await agent.save()
        
        return agent
    
    # === Bank Account Management ===
    
    async def add_bank_account(
        self,
        agent_id: str,
        bank_data: Dict[str, Any]
    ) -> Agent:
        """
        Add bank account to agent
        
        Args:
            agent_id: Agent ID
            bank_data: Bank account data
            
        Returns:
            Updated agent
        """
        agent = await self.get_agent(agent_id)
        
        updated_agent = await self.repository.add_bank_account(
            agent_id,
            bank_data
        )
        
        return updated_agent
    
    # === Commission ===
    
    async def add_commission_earning(
        self,
        agent_id: str,
        amount: float
    ) -> Agent:
        """
        Add commission earning to agent
        
        Args:
            agent_id: Agent ID
            amount: Commission amount
            
        Returns:
            Updated agent
        """
        return await self.repository.add_commission_earning(agent_id, amount)
    
    # === Analytics ===
    
    async def get_agent_stats(self) -> Dict[str, Any]:
        """Get agent statistics for admin dashboard"""
        return await self.repository.get_stats()
    
    async def get_type_distribution(self) -> List[Dict[str, Any]]:
        """Get agent distribution by type"""
        return await self.repository.get_type_distribution()
    
    # === Search & Discovery ===
    
    async def get_featured_agents(self, limit: int = 10) -> List[AgentMinimalResponse]:
        """Get featured agents"""
        agents = await self.repository.get_featured_agents(limit)
        return [self._to_minimal_response(a) for a in agents]
    
    async def get_agents_by_type(
        self,
        agent_type: AgentType,
        skip: int = 0,
        limit: int = 20
    ) -> List[AgentMinimalResponse]:
        """Get agents by type"""
        agents = await self.repository.get_by_type(agent_type, skip, limit)
        return [self._to_minimal_response(a) for a in agents]
    
    async def get_available_agents(
        self,
        limit: int = 20,
        specialization: Optional[List[str]] = None
    ) -> List[AgentMinimalResponse]:
        """Get available agents"""
        agents = await self.repository.get_available_agents(limit, specialization)
        return [self._to_minimal_response(a) for a in agents]
    
    # === Helpers ===
    
    def _generate_referral_code(self) -> str:
        """Generate unique referral code"""
        return f"QA{secrets.token_hex(4).upper()}"
    
    # === Response Converters ===
    
    def _to_response(self, agent: Agent) -> Dict[str, Any]:
        """Convert agent to full response"""
        return {
            "id": str(agent.id),
            "email": agent.email,
            "first_name": agent.first_name,
            "last_name": agent.last_name,
            "display_name": agent.display_name,
            "full_name": agent.full_name,
            "slug": agent.slug,
            "agent_type": agent.agent_type.value if agent.agent_type else None,
            "bio": agent.bio,
            "tagline": agent.tagline,
            "phone": agent.phone,
            "status": agent.status.value if agent.status else None,
            "is_verified": agent.is_verified,
            "is_featured": agent.is_featured,
            "is_premium": agent.is_premium,
            "is_active": agent.is_active,
            "is_available": agent.is_available,
            "address": agent.address.model_dump() if agent.address else None,
            "contact": agent.contact.model_dump() if agent.contact else None,
            "social_links": agent.social_links.model_dump() if agent.social_links else None,
            "specialization": agent.specialization.model_dump() if agent.specialization else None,
            "media": agent.media.model_dump() if agent.media else None,
            "agency": agent.agency.model_dump() if agent.agency else None,
            "verification": agent.verification.model_dump() if agent.verification else None,
            "subscription": agent.subscription.model_dump() if agent.subscription else None,
            "rating": agent.rating.model_dump() if agent.rating else None,
            "analytics": agent.analytics.model_dump() if agent.analytics else None,
            "referral_code": agent.referral_code,
            "referral_count": agent.referral_count,
            "client_count": agent.client_count,
            "max_clients": agent.max_clients,
            "can_accept_clients": agent.can_accept_clients,
            "certifications": agent.certifications,
            "awards": agent.awards,
            "years_of_experience": agent.years_of_experience,
            "response_time": agent.response_time,
            "booking_link": agent.booking_link,
            "stripe_connected": agent.stripe_connected,
            "payout_enabled": agent.payout_enabled,
            "notification_preferences": agent.notification_preferences,
            "created_at": agent.created_at.isoformat() if agent.created_at else None,
            "updated_at": agent.updated_at.isoformat() if agent.updated_at else None,
            "last_login_at": agent.last_login_at.isoformat() if agent.last_login_at else None,
            "verified_at": agent.verified_at.isoformat() if agent.verified_at else None,
        }
    
    def _to_minimal_response(self, agent: Agent) -> Dict[str, Any]:
        """Convert agent to minimal response"""
        return {
            "id": str(agent.id),
            "first_name": agent.first_name,
            "last_name": agent.last_name,
            "display_name": agent.display_name,
            "slug": agent.slug,
            "agent_type": agent.agent_type.value if agent.agent_type else None,
            "tagline": agent.tagline,
            "is_verified": agent.is_verified,
            "is_featured": agent.is_featured,
            "is_available": agent.is_available,
            "profile_photo": agent.media.profile_photo if agent.media else None,
            "city": agent.address.city if agent.address else None,
            "state": agent.address.state if agent.address else None,
            "rating": agent.rating.model_dump() if agent.rating else None,
            "years_of_experience": agent.years_of_experience,
        }
    
    def _to_public_response(self, agent: Agent) -> Dict[str, Any]:
        """Convert agent to public response"""
        return agent.to_public_dict()


# Singleton instance
agent_service = AgentService()

