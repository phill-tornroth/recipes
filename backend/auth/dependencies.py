from typing import Optional

from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy.orm import Session
from storage.dependencies import get_db

from .jwt_handler import JWTHandler
from .models import User
from .repository import UserRepository


async def get_current_user(
    access_token: Optional[str] = Cookie(None), db: Session = Depends(get_db)
) -> User:
    """Get the current authenticated user from JWT token in cookie."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not access_token:
        raise credentials_exception

    token_data = JWTHandler.verify_token(access_token)
    if token_data is None:
        raise credentials_exception

    user = UserRepository.get_by_id(db, token_data["user_id"])
    if user is None:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user"
        )

    return user


async def get_optional_user(
    access_token: Optional[str] = Cookie(None), db: Session = Depends(get_db)
) -> Optional[User]:
    """Get the current user if authenticated, None otherwise."""
    if not access_token:
        return None

    token_data = JWTHandler.verify_token(access_token)
    if token_data is None:
        return None

    user = UserRepository.get_by_id(db, token_data["user_id"])
    if user is None or not user.is_active:
        return None

    return user
