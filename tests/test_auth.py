import pytest
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
from fastapi import HTTPException
import uuid
from datetime import datetime, timedelta

from auth.models import User, UserCreate, UserResponse, GoogleUserInfo
from auth.jwt_handler import JWTHandler
from auth.oauth import GoogleOAuth
from auth.repository import UserRepository


class TestUser:
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
            is_active=True
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
            provider_id="123456789"
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
            created_at=datetime.utcnow(),
            is_active=True
        )
        
        assert user_response.id == user_id
        assert user_response.email == "test@example.com"
        # Should not include sensitive fields like provider_id

    def test_google_user_model(self):
        """Test GoogleUserInfo model for OAuth data."""
        google_user = GoogleUserInfo(
            id="123456789",
            email="test@example.com",
            name="Test User",
            picture="https://lh3.googleusercontent.com/avatar.jpg",
            verified_email=True
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
        assert len(token.split('.')) == 3

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
        # Mock timedelta to create expired token
        with patch('auth.jwt_handler.timedelta') as mock_timedelta:
            mock_timedelta.return_value = timedelta(seconds=-1)  # Expired
            
            user_id = uuid.uuid4()
            email = "test@example.com"
            token = JWTHandler.create_access_token(user_id, email)
            
        # Verify expired token
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
        
        with patch('auth.oauth.httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
            
            token = await oauth.exchange_code_for_token("test_code")
            
            assert token == "test_access_token"

    @pytest.mark.asyncio
    async def test_exchange_code_for_token_failure(self):
        """Test failed OAuth code exchange."""
        oauth = GoogleOAuth()
        
        # Mock failed HTTP response
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = Exception("HTTP Error")
        
        with patch('auth.oauth.httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
            
            token = await oauth.exchange_code_for_token("invalid_code")
            
            assert token is None

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
            "verified_email": True
        }
        
        mock_response = Mock()
        mock_response.json.return_value = user_data
        mock_response.raise_for_status.return_value = None
        
        with patch('auth.oauth.httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.get.return_value = mock_response
            
            google_user = await oauth.get_user_info("test_access_token")
            
            assert google_user is not None
            assert google_user.id == "123456789"
            assert google_user.email == "test@example.com"
            assert google_user.name == "Test User"

    @pytest.mark.asyncio
    async def test_get_user_info_failure(self):
        """Test failed user info retrieval from Google."""
        oauth = GoogleOAuth()
        
        # Mock failed HTTP response
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = Exception("HTTP Error")
        
        with patch('auth.oauth.httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.get.return_value = mock_response
            
            google_user = await oauth.get_user_info("invalid_token")
            
            assert google_user is None


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
            verified_email=True
        )
        
        with patch('auth.repository.User') as mock_user_class:
            mock_user = Mock()
            mock_user_class.return_value = mock_user
            
            result = UserRepository.create_from_google(mock_db, google_user)
            
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
        
        with patch('auth.repository.User') as mock_user_class:
            result = UserRepository.get_by_email(mock_db, "test@example.com")
            
            mock_db.query.assert_called_with(mock_user_class)
            assert result == mock_user

    def test_get_by_provider_id(self):
        """Test getting user by provider and provider_id."""
        mock_db = Mock()
        mock_user = Mock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        
        with patch('auth.repository.User') as mock_user_class:
            result = UserRepository.get_by_provider_id(mock_db, "google", "123456789")
            
            mock_db.query.assert_called_with(mock_user_class)
            assert result == mock_user

    def test_update(self):
        """Test updating user information."""
        mock_db = Mock()
        mock_user = Mock()
        mock_user.name = "Old Name"
        mock_user.avatar_url = "old_avatar.jpg"
        
        result = UserRepository.update(
            mock_db, 
            mock_user, 
            name="New Name",
            avatar_url="new_avatar.jpg"
        )
        
        assert mock_user.name == "New Name"
        assert mock_user.avatar_url == "new_avatar.jpg"
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once_with(mock_user)
        assert result == mock_user


class TestTenancy:
    """Test multi-user tenancy and data isolation."""
    
    def test_user_namespace_isolation(self):
        """Test that users get isolated Pinecone namespaces."""
        from assistant import find_relevant_recipes
        
        user1_id = uuid.uuid4()
        user2_id = uuid.uuid4()
        
        with patch('assistant.index') as mock_index:
            with patch('assistant.get_embeddings', return_value=[[0.1, 0.2, 0.3]]):
                # User 1 searches
                find_relevant_recipes("pasta", user1_id)
                
                # Verify namespace isolation
                mock_index.query.assert_called_with(
                    namespace=f"user_{user1_id}",
                    vector=[0.1, 0.2, 0.3],
                    top_k=5,
                    include_values=False,
                    include_metadata=True,
                )
                
                # User 2 searches
                find_relevant_recipes("pizza", user2_id)
                
                # Verify different namespace
                mock_index.query.assert_called_with(
                    namespace=f"user_{user2_id}",
                    vector=[0.1, 0.2, 0.3],
                    top_k=5,
                    include_values=False,
                    include_metadata=True,
                )

    def test_recipe_storage_isolation(self):
        """Test that recipes are stored in user-specific namespaces."""
        from assistant import update_recipe
        
        user_id = uuid.uuid4()
        recipe_yaml = "recipe:\n  title: Test Recipe"
        recipe_id = "test-recipe-123"
        
        with patch('assistant.yaml.safe_load', return_value={"title": "Test Recipe"}):
            with patch('assistant.yaml.dump', return_value=recipe_yaml):
                with patch('assistant.get_embeddings', return_value=[[0.1, 0.2, 0.3]]):
                    with patch('assistant.index') as mock_index:
                        
                        update_recipe(recipe_id, recipe_yaml, user_id)
                        
                        # Verify recipe stored in user namespace
                        mock_index.upsert.assert_called_once()
                        call_args = mock_index.upsert.call_args
                        assert call_args[1]["namespace"] == f"user_{user_id}"
                        
                        # Verify recipe data
                        vectors = call_args[1]["vectors"]
                        assert len(vectors) == 1
                        assert vectors[0]["id"] == recipe_id
                        assert vectors[0]["values"] == [0.1, 0.2, 0.3]


@pytest.mark.asyncio
class TestAuthIntegration:
    """Integration tests for authentication flow."""
    
    async def test_full_oauth_flow_simulation(self):
        """Test the complete OAuth flow from login to authenticated user."""
        # This would be a more comprehensive integration test
        # that tests the entire flow without external dependencies
        
        user_data = {
            "id": "123456789",
            "email": "test@example.com", 
            "name": "Test User",
            "picture": "https://lh3.googleusercontent.com/avatar.jpg",
            "verified_email": True
        }
        
        # Mock database operations
        mock_db = Mock()
        mock_db.add = Mock()
        mock_db.commit = Mock()
        mock_db.refresh = Mock()
        
        # Mock OAuth service
        with patch('auth.oauth.GoogleOAuth') as mock_oauth_class:
            mock_oauth = Mock()
            mock_oauth.exchange_code_for_token.return_value = "test_access_token"
            mock_oauth.get_user_info.return_value = GoogleUserInfo(**user_data)
            mock_oauth_class.return_value = mock_oauth
            
            # Mock user repository
            with patch('auth.repository.UserRepository') as mock_repo:
                mock_user = Mock()
                mock_user.id = uuid.uuid4()
                mock_user.email = "test@example.com"
                mock_repo.get_by_provider_id.return_value = None  # New user
                mock_repo.create_from_google.return_value = mock_user
                
                # Simulate OAuth callback processing
                oauth_service = mock_oauth_class()
                
                # Exchange code for token
                access_token = await oauth_service.exchange_code_for_token("auth_code")
                assert access_token == "test_access_token"
                
                # Get user info
                google_user = await oauth_service.get_user_info(access_token)
                assert google_user.email == "test@example.com"
                
                # Create or get user
                user = mock_repo.get_by_provider_id(mock_db, "google", google_user.id)
                if not user:
                    user = mock_repo.create_from_google(mock_db, google_user)
                
                # Generate JWT
                jwt_token = JWTHandler.create_access_token(user.id, user.email)
                assert isinstance(jwt_token, str)
                
                # Verify JWT
                payload = JWTHandler.verify_token(jwt_token)
                assert payload is not None
                assert payload["email"] == "test@example.com"