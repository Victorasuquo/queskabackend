"""
Queska Backend - MongoDB Database Manager
Async MongoDB connection using Motor and Beanie ODM
"""

from typing import List, Optional, Type

from beanie import Document, init_beanie
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from loguru import logger

from app.core.config import settings


class DatabaseManager:
    """MongoDB connection manager with async support"""
    
    _client: Optional[AsyncIOMotorClient] = None
    _database: Optional[AsyncIOMotorDatabase] = None
    
    @classmethod
    async def connect(cls, document_models: Optional[List[Type[Document]]] = None) -> None:
        """
        Connect to MongoDB and initialize Beanie ODM
        
        Args:
            document_models: List of Beanie Document models to register
        """
        try:
            logger.info(f"Connecting to MongoDB: {settings.MONGODB_DATABASE}")
            
            # Create Motor client
            cls._client = AsyncIOMotorClient(
                settings.MONGODB_URI,
                maxPoolSize=settings.MONGODB_MAX_POOL_SIZE,
                minPoolSize=settings.MONGODB_MIN_POOL_SIZE,
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=10000,
                retryWrites=True,
                w="majority"
            )
            
            # Get database
            cls._database = cls._client[settings.MONGODB_DATABASE]
            
            # Ping to verify connection
            await cls._client.admin.command("ping")
            logger.info("MongoDB connection established successfully")
            
            # Initialize Beanie with document models if provided
            if document_models:
                await init_beanie(
                    database=cls._database,
                    document_models=document_models
                )
                logger.info(f"Beanie initialized with {len(document_models)} document models")
                
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise
    
    @classmethod
    async def disconnect(cls) -> None:
        """Close MongoDB connection"""
        if cls._client:
            cls._client.close()
            cls._client = None
            cls._database = None
            logger.info("MongoDB connection closed")
    
    @classmethod
    def get_client(cls) -> AsyncIOMotorClient:
        """Get the MongoDB client instance"""
        if not cls._client:
            raise RuntimeError("Database not connected. Call connect() first.")
        return cls._client
    
    @classmethod
    def get_database(cls) -> AsyncIOMotorDatabase:
        """Get the database instance"""
        if not cls._database:
            raise RuntimeError("Database not connected. Call connect() first.")
        return cls._database
    
    @classmethod
    async def ping(cls) -> bool:
        """Check if database is reachable"""
        try:
            if cls._client:
                await cls._client.admin.command("ping")
                return True
        except Exception:
            pass
        return False


# Convenience functions
async def get_database() -> AsyncIOMotorDatabase:
    """Dependency to get database instance"""
    return DatabaseManager.get_database()


async def init_database(document_models: List[Type[Document]]) -> None:
    """Initialize database with document models"""
    await DatabaseManager.connect(document_models)


async def close_database() -> None:
    """Close database connection"""
    await DatabaseManager.disconnect()


# Collection helper
def get_collection(name: str):
    """Get a collection by name"""
    db = DatabaseManager.get_database()
    return db[name]

