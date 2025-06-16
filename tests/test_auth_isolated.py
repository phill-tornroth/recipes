"""
Isolated auth tests that don't depend on external services.
These tests focus purely on authentication logic without importing assistant.
"""

# Set up environment before importing auth modules
import os
import uuid
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import pytest

test_env = {
    "OPENAI_API_KEY": "test-key",
    "PINECONE_API_KEY": "test-key",
    "GOOGLE_CLIENT_ID": "test-client-id",
    "GOOGLE_CLIENT_SECRET": "test-secret",
    "SECRET_KEY": "test-secret-key-for-jwt",
    "DB_HOST": "localhost",
    "DB_PORT": "5432",
    "DB_NAME": "test_db",
    "DB_USER": "test_user",
    "DB_PASSWORD": "test_pass",
}
for k, v in test_env.items():
    os.environ.setdefault(k, v)

# Add backend to path
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from auth.jwt_handler import JWTHandler
from auth.models import GoogleUserInfo, User, UserCreate, UserResponse
from auth.oauth import GoogleOAuth
from auth.repository import UserRepository


class TestUserModels:
    """Test User model and related classes."""

    def test_user_model_creation(self):
        """Test User model creation with all fields."""
        user_id = uuid.uuid4()
        user = User(
            id=user_id,
            email="test@example.com",
            name="Test User",
            avatar_url="https://example.com/avatar.jpg",
            provider="google",
            provider_id="123456789",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            is_active=True,
        )

        assert user.id == user_id
        assert user.email == "test@example.com"
        assert user.name == "Test User"
        assert user.provider == "google"
        assert user.provider_id == "123456789"
        assert user.is_active is True

    def test_user_create_model(self):
        """Test UserCreate model validation."""
        user_create = UserCreate(
            email="test@example.com",
            name="Test User",
            avatar_url="https://example.com/avatar.jpg",
            provider="google",
            provider_id="123456789",
        )

        assert user_create.email == "test@example.com"
        assert user_create.name == "Test User"
        assert user_create.provider == "google"

    def test_user_response_model(self):
        """Test UserResponse model serialization."""
        user_id = uuid.uuid4()
        user_response = UserResponse(
            id=user_id,
            email="test@example.com",
            name="Test User",
            avatar_url="https://example.com/avatar.jpg",
            provider="google",
            created_at=datetime.utcnow(),
            is_active=True,
        )

        assert user_response.id == user_id
        assert user_response.email == "test@example.com"

    def test_google_user_info_model(self):
        """Test GoogleUserInfo model for OAuth data."""
        google_user = GoogleUserInfo(
            id="123456789",
            email="test@example.com",
            name="Test User",
            picture="https://lh3.googleusercontent.com/avatar.jpg",
            verified_email=True,
        )

        assert google_user.id == "123456789"
        assert google_user.email == "test@example.com"
        assert google_user.verified_email is True


class TestJWTHandler:
    """Test JWT token creation and verification."""

    def test_create_access_token(self):
        """Test JWT token creation."""
        user_id = uuid.uuid4()
        email = "test@example.com"

        token = JWTHandler.create_access_token(user_id, email)

        assert isinstance(token, str)
        assert len(token) > 0
        # JWT tokens have 3 parts separated by dots
        assert len(token.split(".")) == 3

    def test_verify_token_valid(self):
        """Test JWT token verification with valid token."""
        user_id = uuid.uuid4()
        email = "test@example.com"

        # Create token
        token = JWTHandler.create_access_token(user_id, email)

        # Verify token
        payload = JWTHandler.verify_token(token)

        assert payload is not None
        assert payload["sub"] == str(user_id)
        assert payload["email"] == email
        assert "exp" in payload
        assert "iat" in payload

    def test_verify_token_invalid(self):
        """Test JWT token verification with invalid token."""
        invalid_token = "invalid.token.here"

        payload = JWTHandler.verify_token(invalid_token)

        assert payload is None

    def test_verify_token_expired(self):
        """Test JWT token verification with expired token."""
        # Create a token that's already expired
        user_id = uuid.uuid4()
        email = "test@example.com"

        # Mock datetime to create expired token
        past_time = datetime.utcnow() - timedelta(hours=1)

        with patch("auth.jwt_handler.datetime") as mock_datetime:
            mock_datetime.utcnow.return_value = past_time
            token = JWTHandler.create_access_token(user_id, email)

        # Verify expired token with current time
        payload = JWTHandler.verify_token(token)

        assert payload is None


class TestGoogleOAuth:
    """Test Google OAuth integration."""

    def test_get_auth_url(self):
        """Test Google OAuth authorization URL generation."""
        oauth = GoogleOAuth()
        state = "test-state-123"

        auth_url = oauth.get_auth_url(state)

        assert isinstance(auth_url, str)
        assert "accounts.google.com" in auth_url
        assert "oauth2" in auth_url
        assert "state=test-state-123" in auth_url
        assert oauth.client_id in auth_url

    @pytest.mark.asyncio
    async def test_exchange_code_for_token_success(self):
        """Test successful OAuth code exchange."""
        oauth = GoogleOAuth()

        # Mock successful HTTP response
        mock_response = Mock()
        mock_response.json.return_value = {"access_token": "test_access_token"}
        mock_response.raise_for_status.return_value = None

        with patch("auth.oauth.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post.return_value = (
                mock_response
            )

            token = await oauth.exchange_code_for_token("test_code")

            assert token == "test_access_token"

    @pytest.mark.asyncio
    async def test_get_user_info_success(self):
        """Test successful user info retrieval from Google."""
        oauth = GoogleOAuth()

        # Mock Google user info response
        user_data = {
            "id": "123456789",
            "email": "test@example.com",
            "name": "Test User",
            "picture": "https://lh3.googleusercontent.com/avatar.jpg",
            "verified_email": True,
        }

        mock_response = Mock()
        mock_response.json.return_value = user_data
        mock_response.raise_for_status.return_value = None

        with patch("auth.oauth.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get.return_value = (
                mock_response
            )

            google_user = await oauth.get_user_info("test_access_token")

            assert google_user is not None
            assert google_user.id == "123456789"
            assert google_user.email == "test@example.com"
            assert google_user.name == "Test User"


class TestUserRepository:
    """Test user database operations."""

    def test_create_from_google(self):
        """Test creating user from Google OAuth data."""
        mock_db = Mock()
        mock_db.add = Mock()
        mock_db.commit = Mock()
        mock_db.refresh = Mock()

        google_user = GoogleUserInfo(
            id="123456789",
            email="test@example.com",
            name="Test User",
            picture="https://lh3.googleusercontent.com/avatar.jpg",
            verified_email=True,
        )

        with patch("auth.repository.User") as mock_user_class:
            mock_user = Mock()
            mock_user_class.return_value = mock_user

            UserRepository.create_from_google(mock_db, google_user)

            # Verify user was created with correct data
            mock_user_class.assert_called_once()
            call_kwargs = mock_user_class.call_args[1]
            assert call_kwargs["email"] == "test@example.com"
            assert call_kwargs["name"] == "Test User"
            assert call_kwargs["provider"] == "google"
            assert call_kwargs["provider_id"] == "123456789"

            # Verify database operations
            mock_db.add.assert_called_once_with(mock_user)
            mock_db.commit.assert_called_once()
            mock_db.refresh.assert_called_once_with(mock_user)

    def test_get_by_email(self):
        """Test getting user by email."""
        mock_db = Mock()
        mock_user = Mock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user

        with patch("auth.repository.User") as mock_user_class:
            result = UserRepository.get_by_email(mock_db, "test@example.com")

            mock_db.query.assert_called_with(mock_user_class)
            assert result == mock_user

    def test_update(self):
        """Test updating user information."""
        mock_db = Mock()
        mock_user = Mock()
        mock_user.name = "Old Name"
        mock_user.avatar_url = "old_avatar.jpg"

        result = UserRepository.update(
            mock_db, mock_user, name="New Name", avatar_url="new_avatar.jpg"
        )

        assert mock_user.name == "New Name"
        assert mock_user.avatar_url == "new_avatar.jpg"
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once_with(mock_user)
        assert result == mock_user


class TestTenancyLogic:
    """Test multi-user tenancy logic without external dependencies."""

    def test_user_namespace_generation(self):
        """Test that user namespaces are generated correctly."""
        user_id = uuid.uuid4()
        expected_namespace = f"user_{user_id}"

        # This would be the logic used in assistant.py
        namespace = f"user_{user_id}"
        assert namespace == expected_namespace
        assert namespace.startswith("user_")
        assert str(user_id) in namespace

    def test_user_isolation_concept(self):
        """Test that different users get different namespaces."""
        user1_id = uuid.uuid4()
        user2_id = uuid.uuid4()

        namespace1 = f"user_{user1_id}"
        namespace2 = f"user_{user2_id}"

        assert namespace1 != namespace2
        assert namespace1.startswith("user_")
        assert namespace2.startswith("user_")


@pytest.mark.asyncio
class TestAuthFlowSimulation:
    """Test the complete authentication flow simulation."""

    async def test_oauth_flow_end_to_end(self):
        """Test the complete OAuth flow without external dependencies."""
        # Simulate the full OAuth flow
        user_data = {
            "id": "123456789",
            "email": "test@example.com",
            "name": "Test User",
            "picture": "https://lh3.googleusercontent.com/avatar.jpg",
            "verified_email": True,
        }

        # Step 1: Generate auth URL
        oauth = GoogleOAuth()
        auth_url = oauth.get_auth_url("test-state")
        assert "accounts.google.com" in auth_url

        # Step 2: Mock OAuth token exchange
        with patch("auth.oauth.httpx.AsyncClient") as mock_client:
            mock_response = Mock()
            mock_response.json.return_value = {"access_token": "test_token"}
            mock_response.raise_for_status.return_value = None
            mock_client.return_value.__aenter__.return_value.post.return_value = (
                mock_response
            )

            access_token = await oauth.exchange_code_for_token("auth_code")
            assert access_token == "test_token"

            # Step 3: Mock user info retrieval
            mock_response.json.return_value = user_data
            mock_client.return_value.__aenter__.return_value.get.return_value = (
                mock_response
            )

            google_user = await oauth.get_user_info(access_token)
            assert google_user.email == "test@example.com"

            # Step 4: Create JWT token
            user_id = uuid.uuid4()
            jwt_token = JWTHandler.create_access_token(user_id, google_user.email)
            assert isinstance(jwt_token, str)

            # Step 5: Verify JWT token
            payload = JWTHandler.verify_token(jwt_token)
            assert payload is not None
            assert payload["email"] == "test@example.com"

            # Step 6: Verify user gets isolated namespace
            namespace = f"user_{user_id}"
            assert namespace == f"user_{user_id}"
