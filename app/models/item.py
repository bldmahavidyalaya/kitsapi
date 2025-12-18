from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


class Item(SQLModel, table=True):
    """Item database model"""
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    description: Optional[str] = None
    price: float = 0.0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
