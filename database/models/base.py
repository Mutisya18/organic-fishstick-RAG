"""
Base SQLAlchemy Setup

Provides declarative base and common columns for all models.
"""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, func
from sqlalchemy.orm import declarative_base
from sqlalchemy.ext.declarative import DeclarativeMeta


Base: DeclarativeMeta = declarative_base()


class BaseModel(Base):
    """Abstract base model with common columns."""
    
    __abstract__ = True
    
    id = Column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        nullable=False
    )
    
    created_at = Column(
        DateTime,
        server_default=func.now(),
        default=datetime.utcnow,
        nullable=False,
        index=True
    )
    
    updated_at = Column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        default=datetime.utcnow,
        nullable=False
    )
    
    def __repr__(self) -> str:
        """String representation of model instance."""
        return f"{self.__class__.__name__}(id={self.id})"
    
    def to_dict(self) -> dict:
        """Convert model instance to dictionary."""
        return {
            key: getattr(self, key)
            for key in self.__mapper__.column_attrs.keys()
        }
