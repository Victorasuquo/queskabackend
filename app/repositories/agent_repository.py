"""
Queska Backend - Agent Repository
Data access layer for Agent operations
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from beanie import PydanticObjectId
from beanie.odm.operators.find.comparison import In

from app.core.constants import AccountStatus, AgentType, VerificationStatus
from app.models.agent import Agent, AgentVerification
from app.repositories.base import BaseRepository
from app.schemas.agent import AgentListParams


class AgentRepository(BaseRepository[Agent]):
    """Repository for Agent document operations"""
    
    def __init__(self):
        super().__init__(Agent)
    
    async def get_by_email(self, email: str) -> Optional[Agent]:
        """
        Get agent by email address
        
        Args:
            email: Agent email
            
        Returns:
            Agent or None
        """
        return await self.model.find_one(
            {"email": email.lower(), "is_deleted": False}
        )
    
    async def get_by_slug(self, slug: str) -> Optional[Agent]:
        """
        Get agent by URL slug
        
        Args:
            slug: Agent slug
            
        Returns:
            Agent or None
        """
        return await self.model.find_one(
            {"slug": slug, "is_deleted": False}
        )
    
    async def get_by_referral_code(self, code: str) -> Optional[Agent]:
        """
        Get agent by referral code
        
        Args:
            code: Referral code
            
        Returns:
            Agent or None
        """
        return await self.model.find_one(
            {"referral_code": code, "is_deleted": False}
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
            exclude_id: Optional agent ID to exclude
            
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
            exclude_id: Optional agent ID to exclude
            
        Returns:
            True if exists, False otherwise
        """
        return await self.exists("slug", slug, exclude_id)
    
    async def referral_code_exists(self, code: str) -> bool:
        """
        Check if referral code exists
        
        Args:
            code: Referral code
            
        Returns:
            True if exists, False otherwise
        """
        return await self.exists("referral_code", code)
    
    async def create_agent(self, data: Dict[str, Any]) -> Agent:
        """
        Create a new agent
        
        Args:
            data: Agent data dictionary
            
        Returns:
            Created agent
        """
        agent = Agent(**data)
        await agent.insert()
        return agent
    
    async def update_agent(
        self,
        agent_id: str,
        data: Dict[str, Any]
    ) -> Optional[Agent]:
        """
        Update agent by ID
        
        Args:
            agent_id: Agent ID
            data: Update data
            
        Returns:
            Updated agent or None
        """
        agent = await self.get_by_id(agent_id)
        if not agent:
            return None
        
        for field, value in data.items():
            if value is not None:
                setattr(agent, field, value)
        
        agent.updated_at = datetime.utcnow()
        await agent.save()
        return agent
    
    async def update_status(
        self,
        agent_id: str,
        status: AccountStatus,
        reason: Optional[str] = None
    ) -> Optional[Agent]:
        """
        Update agent account status
        
        Args:
            agent_id: Agent ID
            status: New status
            reason: Optional reason for status change
            
        Returns:
            Updated agent or None
        """
        agent = await self.get_by_id(agent_id)
        if not agent:
            return None
        
        agent.status = status
        agent.is_active = status == AccountStatus.ACTIVE
        
        if reason:
            agent.metadata["status_change_reason"] = reason
            agent.metadata["status_changed_at"] = datetime.utcnow().isoformat()
        
        agent.updated_at = datetime.utcnow()
        await agent.save()
        return agent
    
    async def update_verification(
        self,
        agent_id: str,
        verification_data: Dict[str, Any]
    ) -> Optional[Agent]:
        """
        Update agent verification documents
        
        Args:
            agent_id: Agent ID
            verification_data: Verification data
            
        Returns:
            Updated agent or None
        """
        agent = await self.get_by_id(agent_id)
        if not agent:
            return None
        
        if not agent.verification:
            agent.verification = AgentVerification()
        
        for field, value in verification_data.items():
            setattr(agent.verification, field, value)
        
        agent.verification.submitted_at = datetime.utcnow()
        agent.updated_at = datetime.utcnow()
        await agent.save()
        return agent
    
    async def verify_agent(
        self,
        agent_id: str,
        admin_id: str,
        status: VerificationStatus,
        notes: Optional[str] = None,
        rejection_reason: Optional[str] = None
    ) -> Optional[Agent]:
        """
        Admin: Verify or reject agent
        
        Args:
            agent_id: Agent ID
            admin_id: Admin performing the review
            status: Verification status
            notes: Optional notes
            rejection_reason: Reason if rejected
            
        Returns:
            Updated agent or None
        """
        agent = await self.get_by_id(agent_id)
        if not agent:
            return None
        
        if not agent.verification:
            agent.verification = AgentVerification()
        
        agent.verification.status = status
        agent.verification.reviewed_at = datetime.utcnow()
        agent.verification.reviewed_by = PydanticObjectId(admin_id)
        agent.verification.notes = notes
        
        if status == VerificationStatus.VERIFIED:
            agent.is_verified = True
            agent.verified_at = datetime.utcnow()
            agent.status = AccountStatus.ACTIVE
            agent.is_active = True
        elif status == VerificationStatus.REJECTED:
            agent.verification.rejection_reason = rejection_reason
        
        agent.updated_at = datetime.utcnow()
        await agent.save()
        return agent
    
    async def update_last_login(self, agent_id: str) -> Optional[Agent]:
        """
        Update agent last login timestamp
        
        Args:
            agent_id: Agent ID
            
        Returns:
            Updated agent or None
        """
        agent = await self.get_by_id(agent_id)
        if agent:
            agent.last_login_at = datetime.utcnow()
            await agent.save()
        return agent
    
    async def list_agents(
        self,
        params: AgentListParams
    ) -> Tuple[List[Agent], int]:
        """
        List agents with filters and pagination
        
        Args:
            params: List parameters
            
        Returns:
            Tuple of (agents list, total count)
        """
        query: Dict[str, Any] = {"is_deleted": False}
        
        # Apply filters
        if params.search:
            query["$text"] = {"$search": params.search}
        
        if params.agent_type:
            query["agent_type"] = params.agent_type
        
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
        
        if params.is_available is not None:
            query["is_available"] = params.is_available
        
        if params.min_rating:
            query["rating.average"] = {"$gte": params.min_rating}
        
        if params.min_experience:
            query["years_of_experience"] = {"$gte": params.min_experience}
        
        if params.destinations:
            query["specialization.destinations"] = {"$in": params.destinations}
        
        if params.travel_types:
            query["specialization.travel_types"] = {"$in": params.travel_types}
        
        if params.languages:
            query["specialization.languages"] = {"$in": params.languages}
        
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
        agents = await self.model.find(query) \
            .sort((params.sort_by, sort_order)) \
            .skip(skip) \
            .limit(params.limit) \
            .to_list()
        
        return agents, total
    
    async def get_by_type(
        self,
        agent_type: AgentType,
        skip: int = 0,
        limit: int = 20
    ) -> List[Agent]:
        """
        Get agents by type
        
        Args:
            agent_type: Agent type
            skip: Number to skip
            limit: Maximum results
            
        Returns:
            List of agents
        """
        return await self.model.find(
            {"agent_type": agent_type, "is_deleted": False, "is_active": True}
        ).sort(["-is_featured", "-rating.average"]) \
            .skip(skip) \
            .limit(limit) \
            .to_list()
    
    async def get_featured_agents(self, limit: int = 10) -> List[Agent]:
        """
        Get featured agents
        
        Args:
            limit: Maximum results
            
        Returns:
            List of featured agents
        """
        return await self.model.find(
            {"is_featured": True, "is_deleted": False, "is_active": True}
        ).sort("-rating.average").limit(limit).to_list()
    
    async def get_available_agents(
        self,
        limit: int = 20,
        specialization: Optional[List[str]] = None
    ) -> List[Agent]:
        """
        Get available agents that can accept new clients
        
        Args:
            limit: Maximum results
            specialization: Optional specialization filter
            
        Returns:
            List of available agents
        """
        query: Dict[str, Any] = {
            "is_deleted": False,
            "is_active": True,
            "is_available": True,
            "$expr": {"$lt": [{"$size": "$client_ids"}, "$max_clients"]}
        }
        
        if specialization:
            query["specialization.destinations"] = {"$in": specialization}
        
        return await self.model.find(query) \
            .sort(["-is_featured", "-rating.average"]) \
            .limit(limit) \
            .to_list()
    
    async def get_agents_by_ids(self, ids: List[str]) -> List[Agent]:
        """
        Get multiple agents by IDs
        
        Args:
            ids: List of agent IDs
            
        Returns:
            List of agents
        """
        object_ids = [PydanticObjectId(id) for id in ids]
        return await self.model.find(
            In(self.model.id, object_ids),
            {"is_deleted": False}
        ).to_list()
    
    async def add_client(
        self,
        agent_id: str,
        client_id: str
    ) -> Optional[Agent]:
        """
        Add client to agent
        
        Args:
            agent_id: Agent ID
            client_id: Client user ID
            
        Returns:
            Updated agent or None
        """
        agent = await self.get_by_id(agent_id)
        if not agent:
            return None
        
        client_oid = PydanticObjectId(client_id)
        if client_oid not in agent.client_ids:
            if len(agent.client_ids) >= agent.max_clients:
                return None  # Cannot add more clients
            agent.client_ids.append(client_oid)
            agent.updated_at = datetime.utcnow()
            await agent.save()
        
        return agent
    
    async def remove_client(
        self,
        agent_id: str,
        client_id: str
    ) -> Optional[Agent]:
        """
        Remove client from agent
        
        Args:
            agent_id: Agent ID
            client_id: Client user ID
            
        Returns:
            Updated agent or None
        """
        agent = await self.get_by_id(agent_id)
        if not agent:
            return None
        
        client_oid = PydanticObjectId(client_id)
        if client_oid in agent.client_ids:
            agent.client_ids.remove(client_oid)
            agent.updated_at = datetime.utcnow()
            await agent.save()
        
        return agent
    
    async def get_agent_clients(self, agent_id: str) -> List[PydanticObjectId]:
        """
        Get list of agent's clients
        
        Args:
            agent_id: Agent ID
            
        Returns:
            List of client IDs
        """
        agent = await self.get_by_id(agent_id)
        if agent:
            return agent.client_ids
        return []
    
    async def add_bank_account(
        self,
        agent_id: str,
        bank_account: Dict[str, Any]
    ) -> Optional[Agent]:
        """
        Add bank account to agent
        
        Args:
            agent_id: Agent ID
            bank_account: Bank account data
            
        Returns:
            Updated agent or None
        """
        from app.models.agent import AgentBankAccount
        
        agent = await self.get_by_id(agent_id)
        if not agent:
            return None
        
        account = AgentBankAccount(**bank_account)
        
        if account.is_primary or not agent.bank_accounts:
            for acc in agent.bank_accounts:
                acc.is_primary = False
            account.is_primary = True
        
        agent.bank_accounts.append(account)
        agent.updated_at = datetime.utcnow()
        await agent.save()
        return agent
    
    async def update_analytics(
        self,
        agent_id: str,
        analytics_data: Dict[str, Any]
    ) -> Optional[Agent]:
        """
        Update agent analytics
        
        Args:
            agent_id: Agent ID
            analytics_data: Analytics data to update
            
        Returns:
            Updated agent or None
        """
        from app.models.agent import AgentAnalytics
        
        agent = await self.get_by_id(agent_id)
        if not agent:
            return None
        
        if not agent.analytics:
            agent.analytics = AgentAnalytics()
        
        for field, value in analytics_data.items():
            if hasattr(agent.analytics, field):
                setattr(agent.analytics, field, value)
        
        agent.analytics.last_updated = datetime.utcnow()
        await agent.save()
        return agent
    
    async def add_commission_earning(
        self,
        agent_id: str,
        amount: float
    ) -> Optional[Agent]:
        """
        Add commission earning to agent
        
        Args:
            agent_id: Agent ID
            amount: Commission amount
            
        Returns:
            Updated agent or None
        """
        from app.models.agent import AgentAnalytics
        
        agent = await self.get_by_id(agent_id)
        if not agent:
            return None
        
        if not agent.analytics:
            agent.analytics = AgentAnalytics()
        
        agent.analytics.total_commission_earned += amount
        agent.analytics.last_updated = datetime.utcnow()
        await agent.save()
        return agent
    
    async def increment_referral(self, agent_id: str) -> Optional[Agent]:
        """
        Increment referral count for agent
        
        Args:
            agent_id: Agent ID
            
        Returns:
            Updated agent or None
        """
        agent = await self.get_by_id(agent_id)
        if agent:
            agent.referral_count += 1
            await agent.save()
        return agent
    
    async def get_stats(self) -> Dict[str, Any]:
        """
        Get agent statistics for admin dashboard
        
        Returns:
            Dictionary with agent stats
        """
        pipeline = [
            {"$match": {"is_deleted": False}},
            {"$group": {
                "_id": None,
                "total": {"$sum": 1},
                "active": {"$sum": {"$cond": ["$is_active", 1, 0]}},
                "verified": {"$sum": {"$cond": ["$is_verified", 1, 0]}},
                "featured": {"$sum": {"$cond": ["$is_featured", 1, 0]}},
                "available": {"$sum": {"$cond": ["$is_available", 1, 0]}},
                "pending": {"$sum": {"$cond": [
                    {"$eq": ["$status", "pending"]}, 1, 0
                ]}},
                "total_clients": {"$sum": {"$size": "$client_ids"}},
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
            "available": 0,
            "pending": 0,
            "total_clients": 0
        }
    
    async def get_type_distribution(self) -> List[Dict[str, Any]]:
        """
        Get agent distribution by type
        
        Returns:
            List of type counts
        """
        pipeline = [
            {"$match": {"is_deleted": False, "is_active": True}},
            {"$group": {
                "_id": "$agent_type",
                "count": {"$sum": 1}
            }},
            {"$sort": {"count": -1}}
        ]
        
        return await self.model.aggregate(pipeline).to_list()


# Singleton instance
agent_repository = AgentRepository()

