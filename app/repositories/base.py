"""
Queska Backend - Base Repository
Generic base repository for MongoDB operations using Beanie ODM
"""

from datetime import datetime
from typing import Any, Dict, Generic, List, Optional, Type, TypeVar, Tuple

from beanie import Document, PydanticObjectId
from beanie.odm.operators.find.comparison import In
from pydantic import BaseModel


# Type variable for document models
ModelType = TypeVar("ModelType", bound=Document)


class BaseRepository(Generic[ModelType]):
    """
    Generic base repository providing common CRUD operations.
    
    Usage:
        class UserRepository(BaseRepository[User]):
            def __init__(self):
                super().__init__(User)
    """
    
    def __init__(self, model: Type[ModelType]):
        """
        Initialize repository with a document model.
        
        Args:
            model: The Beanie Document model class
        """
        self.model = model
    
    # === Create ===
    
    async def create(self, obj: ModelType) -> ModelType:
        """
        Create a new document.
        
        Args:
            obj: Document instance to insert
            
        Returns:
            Inserted document with ID
        """
        await obj.insert()
        return obj
    
    async def create_many(self, objects: List[ModelType]) -> List[ModelType]:
        """
        Create multiple documents.
        
        Args:
            objects: List of document instances
            
        Returns:
            List of inserted documents
        """
        if not objects:
            return []
        await self.model.insert_many(objects)
        return objects
    
    # === Read ===
    
    async def get_by_id(self, id: str) -> Optional[ModelType]:
        """
        Get document by ID.
        
        Args:
            id: Document ID string
            
        Returns:
            Document if found, None otherwise
        """
        try:
            return await self.model.get(PydanticObjectId(id))
        except Exception:
            return None
    
    async def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        sort_field: str = "created_at",
        sort_order: int = -1
    ) -> List[ModelType]:
        """
        Get all documents with pagination.
        
        Args:
            skip: Number of documents to skip
            limit: Maximum documents to return
            sort_field: Field to sort by
            sort_order: Sort direction (1=asc, -1=desc)
            
        Returns:
            List of documents
        """
        return await self.model.find_all() \
            .sort((sort_field, sort_order)) \
            .skip(skip) \
            .limit(limit) \
            .to_list()
    
    async def get_by_ids(self, ids: List[str]) -> List[ModelType]:
        """
        Get multiple documents by IDs.
        
        Args:
            ids: List of document ID strings
            
        Returns:
            List of found documents
        """
        object_ids = [PydanticObjectId(id) for id in ids]
        return await self.model.find(In(self.model.id, object_ids)).to_list()
    
    async def get_by_field(
        self,
        field: str,
        value: Any,
        multiple: bool = False
    ) -> Optional[ModelType] | List[ModelType]:
        """
        Get document(s) by field value.
        
        Args:
            field: Field name to search
            value: Value to match
            multiple: If True, return list; otherwise single
            
        Returns:
            Document, list of documents, or None
        """
        query = {field: value}
        if multiple:
            return await self.model.find(query).to_list()
        return await self.model.find_one(query)
    
    async def find(
        self,
        query: Dict[str, Any],
        skip: int = 0,
        limit: int = 100,
        sort_field: str = "created_at",
        sort_order: int = -1
    ) -> List[ModelType]:
        """
        Find documents matching query.
        
        Args:
            query: MongoDB query dict
            skip: Number to skip
            limit: Maximum to return
            sort_field: Field to sort by
            sort_order: Sort direction
            
        Returns:
            List of matching documents
        """
        return await self.model.find(query) \
            .sort((sort_field, sort_order)) \
            .skip(skip) \
            .limit(limit) \
            .to_list()
    
    async def find_one(self, query: Dict[str, Any]) -> Optional[ModelType]:
        """
        Find single document matching query.
        
        Args:
            query: MongoDB query dict
            
        Returns:
            Document if found, None otherwise
        """
        return await self.model.find_one(query)
    
    async def find_paginated(
        self,
        query: Dict[str, Any],
        page: int = 1,
        limit: int = 20,
        sort_field: str = "created_at",
        sort_order: int = -1
    ) -> Tuple[List[ModelType], int, int]:
        """
        Find documents with pagination info.
        
        Args:
            query: MongoDB query dict
            page: Page number (1-indexed)
            limit: Items per page
            sort_field: Field to sort by
            sort_order: Sort direction
            
        Returns:
            Tuple of (documents, total_count, total_pages)
        """
        total = await self.model.find(query).count()
        skip = (page - 1) * limit
        
        documents = await self.model.find(query) \
            .sort((sort_field, sort_order)) \
            .skip(skip) \
            .limit(limit) \
            .to_list()
        
        pages = (total + limit - 1) // limit
        
        return documents, total, pages
    
    # === Update ===
    
    async def update(
        self,
        id: str,
        update_data: Dict[str, Any]
    ) -> Optional[ModelType]:
        """
        Update document by ID.
        
        Args:
            id: Document ID
            update_data: Fields to update
            
        Returns:
            Updated document if found
        """
        doc = await self.get_by_id(id)
        if not doc:
            return None
        
        for field, value in update_data.items():
            if hasattr(doc, field) and value is not None:
                setattr(doc, field, value)
        
        if hasattr(doc, "updated_at"):
            doc.updated_at = datetime.utcnow()
        
        await doc.save()
        return doc
    
    async def update_one(
        self,
        query: Dict[str, Any],
        update_data: Dict[str, Any]
    ) -> bool:
        """
        Update single document matching query.
        
        Args:
            query: MongoDB query dict
            update_data: Update operations
            
        Returns:
            True if updated, False otherwise
        """
        result = await self.model.find_one(query).update({"$set": update_data})
        return result is not None
    
    async def update_many(
        self,
        query: Dict[str, Any],
        update_data: Dict[str, Any]
    ) -> int:
        """
        Update multiple documents matching query.
        
        Args:
            query: MongoDB query dict
            update_data: Update operations
            
        Returns:
            Number of documents updated
        """
        result = await self.model.find(query).update_many({"$set": update_data})
        return result.modified_count if result else 0
    
    async def increment(
        self,
        id: str,
        field: str,
        value: float = 1
    ) -> Optional[ModelType]:
        """
        Increment a numeric field.
        
        Args:
            id: Document ID
            field: Field to increment
            value: Amount to increment by
            
        Returns:
            Updated document
        """
        doc = await self.get_by_id(id)
        if not doc:
            return None
        
        await doc.inc({field: value})
        return doc
    
    # === Delete ===
    
    async def delete(self, id: str, soft: bool = True) -> bool:
        """
        Delete document by ID.
        
        Args:
            id: Document ID
            soft: If True, mark as deleted; otherwise remove
            
        Returns:
            True if deleted, False otherwise
        """
        doc = await self.get_by_id(id)
        if not doc:
            return False
        
        if soft and hasattr(doc, "is_deleted"):
            doc.is_deleted = True
            if hasattr(doc, "deleted_at"):
                doc.deleted_at = datetime.utcnow()
            await doc.save()
        else:
            await doc.delete()
        
        return True
    
    async def delete_many(
        self,
        query: Dict[str, Any],
        soft: bool = True
    ) -> int:
        """
        Delete multiple documents matching query.
        
        Args:
            query: MongoDB query dict
            soft: If True, mark as deleted
            
        Returns:
            Number of documents deleted
        """
        if soft:
            return await self.update_many(query, {
                "is_deleted": True,
                "deleted_at": datetime.utcnow()
            })
        
        result = await self.model.find(query).delete()
        return result.deleted_count if result else 0
    
    async def restore(self, id: str) -> Optional[ModelType]:
        """
        Restore a soft-deleted document.
        
        Args:
            id: Document ID
            
        Returns:
            Restored document if found
        """
        doc = await self.get_by_id(id)
        if not doc or not hasattr(doc, "is_deleted"):
            return None
        
        doc.is_deleted = False
        if hasattr(doc, "deleted_at"):
            doc.deleted_at = None
        
        await doc.save()
        return doc
    
    # === Utility ===
    
    async def count(self, query: Optional[Dict[str, Any]] = None) -> int:
        """
        Count documents matching query.
        
        Args:
            query: Optional MongoDB query dict
            
        Returns:
            Number of matching documents
        """
        if query:
            return await self.model.find(query).count()
        return await self.model.count()
    
    async def exists(
        self,
        field: str,
        value: Any,
        exclude_id: Optional[str] = None
    ) -> bool:
        """
        Check if document with field value exists.
        
        Args:
            field: Field name
            value: Value to check
            exclude_id: Optional ID to exclude
            
        Returns:
            True if exists, False otherwise
        """
        query = {field: value}
        if exclude_id:
            query["_id"] = {"$ne": PydanticObjectId(exclude_id)}
        return await self.model.find_one(query) is not None
    
    async def aggregate(
        self,
        pipeline: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Run aggregation pipeline.
        
        Args:
            pipeline: MongoDB aggregation pipeline
            
        Returns:
            Aggregation results
        """
        return await self.model.aggregate(pipeline).to_list()
    
    async def distinct(
        self,
        field: str,
        query: Optional[Dict[str, Any]] = None
    ) -> List[Any]:
        """
        Get distinct values for a field.
        
        Args:
            field: Field name
            query: Optional filter query
            
        Returns:
            List of distinct values
        """
        if query:
            return await self.model.find(query).distinct(field)
        return await self.model.distinct(field)
    
    async def text_search(
        self,
        query: str,
        skip: int = 0,
        limit: int = 20
    ) -> List[ModelType]:
        """
        Perform text search.
        
        Args:
            query: Search text
            skip: Documents to skip
            limit: Max documents to return
            
        Returns:
            List of matching documents
        """
        return await self.model.find(
            {"$text": {"$search": query}}
        ).skip(skip).limit(limit).to_list()
    
    async def get_stats(self) -> Dict[str, Any]:
        """
        Get collection statistics.
        
        Returns:
            Dictionary with count stats
        """
        total = await self.count()
        query = {"is_deleted": False} if hasattr(self.model, "is_deleted") else {}
        active = await self.count(query) if query else total
        
        return {
            "total": total,
            "active": active
        }
