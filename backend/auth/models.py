import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from sqlalchemy import Column, String, TIMESTAMP, Boolean
from sqlalchemy.dialects.postgresql import UUID
from storage.conversations import Base


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    avatar_url = Column(String(500), nullable=True)
    provider = Column(String(50), nullable=False, default="google")
    provider_id = Column(String(255), nullable=False)
    created_at = Column(TIMESTAMP, nullable=False, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, nullable=False, default=True)


class UserCreate(BaseModel):
    email: str
    name: str
    avatar_url: Optional[str] = None
    provider: str = "google"
    provider_id: str


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    name: str
    avatar_url: Optional[str]
    provider: str
    created_at: datetime
    is_active: bool

    class Config:
        from_attributes = True


class GoogleUserInfo(BaseModel):
    """Google OAuth user information"""
    id: str
    email: str
    name: str
    picture: Optional[str] = None
    verified_email: bool = True