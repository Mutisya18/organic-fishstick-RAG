"""
Base Repository

Provides generic CRUD operations for all models.
Subclassed by ConversationRepository and MessageRepository for domain-specific queries.
"""

import logging
from typing import TypeVar, Generic, Type, List, Optional, Dict, Any

from sqlalchemy.orm import Session
from sqlalchemy import desc

from ..models import BaseModel
from ..exceptions import NotFoundError, DatabaseError
from ..core.session import get_session

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=BaseModel)


class BaseRepository(Generic[T]):
    """
    Generic repository for CRUD operations on model T.
    
    Subclassed by ConversationRepository, MessageRepository, etc.
    Handles common operations: create, read, update, delete.
    """
    
    def __init__(self, model_class: Type[T]):
        """
        Initialize repository.
        
        Args:
            model_class: The SQLAlchemy model class this repository manages
        """
        self.model_class = model_class
    
    def create(self, data: Dict[str, Any]) -> T:
        """
        Create and insert a new record.
        
        Args:
            data: Dictionary of field values
            
        Returns:
            Created model instance with auto-generated fields
            
        Raises:
            DatabaseError: On creation failure
        """
        try:
            with get_session() as session:
                instance = self.model_class(**data)
                session.add(instance)
                session.flush()  # Get auto-generated ID
                return instance
        
        except Exception as e:
            logger.error(f"Failed to create {self.model_class.__name__}: {str(e)}")
            raise DatabaseError(f"Failed to create record: {str(e)}") from e
    
    def get_by_id(self, id: str) -> Optional[T]:
        """
        Fetch a record by ID.
        
        Args:
            id: Primary key value
            
        Returns:
            Model instance or None if not found
            
        Raises:
            DatabaseError: On query failure
        """
        try:
            with get_session() as session:
                instance = session.query(self.model_class).filter_by(id=id).first()
                return instance
        
        except Exception as e:
            logger.error(f"Failed to get {self.model_class.__name__} by id: {str(e)}")
            raise DatabaseError(f"Failed to fetch record: {str(e)}") from e
    
    def list_all(self, limit: int = 100, offset: int = 0) -> List[T]:
        """
        Fetch all records with pagination.
        
        Args:
            limit: Maximum records to return
            offset: Pagination offset
            
        Returns:
            List of model instances
            
        Raises:
            DatabaseError: On query failure
        """
        try:
            with get_session() as session:
                return (session.query(self.model_class)
                        .limit(limit)
                        .offset(offset)
                        .all())
        
        except Exception as e:
            logger.error(f"Failed to list {self.model_class.__name__}: {str(e)}")
            raise DatabaseError(f"Failed to list records: {str(e)}") from e
    
    def filter(self, filters: Dict[str, Any], limit: int = 100, offset: int = 0) -> List[T]:
        """
        Fetch records matching filters.
        
        Args:
            filters: Dictionary of field=value pairs
            limit: Maximum records to return
            offset: Pagination offset
            
        Returns:
            List of matching model instances
            
        Raises:
            DatabaseError: On query failure
        """
        try:
            with get_session() as session:
                query = session.query(self.model_class)
                
                for field_name, value in filters.items():
                    if hasattr(self.model_class, field_name):
                        query = query.filter(getattr(self.model_class, field_name) == value)
                
                return (query
                        .limit(limit)
                        .offset(offset)
                        .all())
        
        except Exception as e:
            logger.error(f"Failed to filter {self.model_class.__name__}: {str(e)}")
            raise DatabaseError(f"Failed to filter records: {str(e)}") from e
    
    def update(self, id: str, data: Dict[str, Any]) -> T:
        """
        Update a record by ID.
        
        Args:
            id: Primary key value
            data: Dictionary of fields to update
            
        Returns:
            Updated model instance
            
        Raises:
            NotFoundError: If record not found
            DatabaseError: On update failure
        """
        try:
            with get_session() as session:
                instance = session.query(self.model_class).filter_by(id=id).first()
                
                if instance is None:
                    raise NotFoundError(f"Record with id={id} not found")
                
                for field, value in data.items():
                    if hasattr(instance, field):
                        setattr(instance, field, value)
                
                session.add(instance)
                return instance
        
        except NotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to update {self.model_class.__name__} id={id}: {str(e)}")
            raise DatabaseError(f"Failed to update record: {str(e)}") from e
    
    def delete(self, id: str) -> bool:
        """
        Delete a record by ID.
        
        Note: For audit trail requirements, prefer soft-delete (update status field).
        Hard-delete permanently removes the record.
        
        Args:
            id: Primary key value
            
        Returns:
            True if deleted, False if not found
            
        Raises:
            DatabaseError: On delete failure
        """
        try:
            with get_session() as session:
                instance = session.query(self.model_class).filter_by(id=id).first()
                
                if instance is None:
                    return False
                
                session.delete(instance)
                return True
        
        except Exception as e:
            logger.error(f"Failed to delete {self.model_class.__name__} id={id}: {str(e)}")
            raise DatabaseError(f"Failed to delete record: {str(e)}") from e
    
    def count(self) -> int:
        """
        Count total records.
        
        Returns:
            Total record count
        """
        try:
            with get_session() as session:
                return session.query(self.model_class).count()
        
        except Exception as e:
            logger.error(f"Failed to count {self.model_class.__name__}: {str(e)}")
            raise DatabaseError(f"Failed to count records: {str(e)}") from e
