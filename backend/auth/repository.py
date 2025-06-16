import uuid
from typing import Optional

from sqlalchemy.orm import Session

from .models import GoogleUserInfo, User, UserCreate


class UserRepository:
    @staticmethod
    def get_by_id(db: Session, user_id: uuid.UUID) -> Optional[User]:
        """Get user by ID."""
        return db.query(User).filter(User.id == user_id).first()

    @staticmethod
    def get_by_email(db: Session, email: str) -> Optional[User]:
        """Get user by email."""
        return db.query(User).filter(User.email == email).first()

    @staticmethod
    def get_by_provider_id(
        db: Session, provider: str, provider_id: str
    ) -> Optional[User]:
        """Get user by provider and provider ID."""
        return (
            db.query(User)
            .filter(User.provider == provider, User.provider_id == provider_id)
            .first()
        )

    @staticmethod
    def create(db: Session, user_data: UserCreate) -> User:
        """Create a new user."""
        db_user = User(
            email=user_data.email,
            name=user_data.name,
            avatar_url=user_data.avatar_url,
            provider=user_data.provider,
            provider_id=user_data.provider_id,
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return db_user

    @staticmethod
    def create_from_google(db: Session, google_user: GoogleUserInfo) -> User:
        """Create user from Google OAuth information."""
        user_data = UserCreate(
            email=google_user.email,
            name=google_user.name,
            avatar_url=google_user.picture,
            provider="google",
            provider_id=google_user.id,
        )
        return UserRepository.create(db, user_data)

    @staticmethod
    def update(db: Session, user: User, **kwargs) -> User:
        """Update user fields."""
        for field, value in kwargs.items():
            if hasattr(user, field):
                setattr(user, field, value)

        db.commit()
        db.refresh(user)
        return user
