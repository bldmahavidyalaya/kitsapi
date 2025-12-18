from typing import Optional
from pydantic import BaseModel, ConfigDict


class ItemBase(BaseModel):
    """Base item schema"""
    name: str
    description: Optional[str] = None
    price: float


class ItemCreate(ItemBase):
    """Create item schema"""
    pass


class ItemUpdate(BaseModel):
    """Update item schema"""
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None


class ItemRead(ItemBase):
    """Item read schema with ORM support"""
    id: int
    model_config = ConfigDict(from_attributes=True)
