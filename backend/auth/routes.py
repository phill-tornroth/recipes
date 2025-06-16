import secrets
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Response, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from storage.dependencies import get_db
from .models import UserResponse
from .oauth import google_oauth
from .repository import UserRepository
from .jwt_handler import JWTHandler
from .dependencies import get_current_user, get_optional_user

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.get("/google/login")
async def google_login(
    redirect_url: Optional[str] = Query(None, description="URL to redirect to after login")
):
    """Initiate Google OAuth login."""
    # Generate a random state for CSRF protection
    state = secrets.token_urlsafe(32)
    
    # In a real app, you'd store state in session/cache with redirect_url
    # For now, we'll just use the state parameter
    auth_url = google_oauth.get_auth_url(state=state)
    
    return {"auth_url": auth_url, "state": state}


@router.get("/google/callback")
async def google_callback(
    code: str = Query(..., description="Authorization code from Google"),
    state: Optional[str] = Query(None, description="State parameter for CSRF protection"),
    db: Session = Depends(get_db)
):
    """Handle Google OAuth callback."""
    if not code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Authorization code not provided"
        )

    # Exchange code for access token
    access_token = await google_oauth.exchange_code_for_token(code)
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to exchange authorization code for access token"
        )

    # Get user information from Google
    google_user = await google_oauth.get_user_info(access_token)
    if not google_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to get user information from Google"
        )

    # Check if user exists
    user = UserRepository.get_by_provider_id(db, "google", google_user.id)
    
    if not user:
        # Check if user exists with same email but different provider
        existing_user = UserRepository.get_by_email(db, google_user.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this email already exists with a different login method"
            )
        
        # Create new user
        user = UserRepository.create_from_google(db, google_user)
    else:
        # Update user information (avatar, name might have changed)
        user = UserRepository.update(
            db, 
            user,
            name=google_user.name,
            avatar_url=google_user.picture
        )

    # Create JWT token
    jwt_token = JWTHandler.create_access_token(user.id, user.email)

    # Create response with redirect
    response = RedirectResponse(
        url="http://localhost:8000",  # TODO: Make configurable
        status_code=status.HTTP_302_FOUND
    )
    
    # Set HTTP-only cookie with JWT token
    response.set_cookie(
        key="access_token",
        value=jwt_token,
        httponly=True,
        secure=False,  # Set to True in production with HTTPS
        samesite="lax",
        max_age=7 * 24 * 60 * 60,  # 7 days in seconds
    )

    return response


@router.post("/logout")
async def logout():
    """Logout user by clearing the authentication cookie."""
    response = Response(content="Logged out successfully")
    response.delete_cookie(key="access_token", httponly=True, samesite="lax")
    return response


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user = Depends(get_current_user)):
    """Get current user information."""
    return current_user


@router.get("/status")
async def auth_status(current_user = Depends(get_optional_user)):
    """Check authentication status."""
    if current_user:
        return {
            "authenticated": True,
            "user": {
                "id": current_user.id,
                "name": current_user.name,
                "email": current_user.email,
                "avatar_url": current_user.avatar_url
            }
        }
    else:
        return {"authenticated": False}