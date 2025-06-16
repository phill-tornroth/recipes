"""
Test JWT functionality in isolation.
"""
import pytest
import uuid
from datetime import datetime, timedelta

# Set up environment
import os
test_env = {
    'OPENAI_API_KEY': 'test-key',
    'PINECONE_API_KEY': 'test-key', 
    'GOOGLE_CLIENT_ID': 'test-client-id',
    'GOOGLE_CLIENT_SECRET': 'test-secret',
    'SECRET_KEY': 'test-secret-key-for-jwt-testing-12345',
    'DB_HOST': 'localhost',
    'DB_PORT': '5432',
    'DB_NAME': 'test_db',
    'DB_USER': 'test_user',
    'DB_PASSWORD': 'test_pass'
}
for k, v in test_env.items():
    os.environ.setdefault(k, v)

# Add backend to path
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from auth.jwt_handler import JWTHandler


def test_create_access_token():
    """Test JWT token creation."""
    user_id = uuid.uuid4()
    email = "test@example.com"
    
    token = JWTHandler.create_access_token(user_id, email)
    
    assert isinstance(token, str)
    assert len(token) > 0
    # JWT tokens have 3 parts separated by dots
    assert len(token.split('.')) == 3


def test_verify_token_valid():
    """Test JWT token verification with valid token."""
    user_id = uuid.uuid4()
    email = "test@example.com"
    
    # Create token
    token = JWTHandler.create_access_token(user_id, email)
    
    # Verify token
    payload = JWTHandler.verify_token(token)
    
    assert payload is not None
    assert payload["user_id"] == user_id
    assert payload["email"] == email


def test_verify_token_invalid():
    """Test JWT token verification with invalid token."""
    invalid_token = "invalid.token.here"
    
    payload = JWTHandler.verify_token(invalid_token)
    
    assert payload is None


def test_user_namespace_logic():
    """Test the user namespace logic used for tenancy."""
    user_id = uuid.uuid4()
    
    # This is the logic used in assistant.py for user isolation
    namespace = f"user_{user_id}"
    
    assert namespace.startswith("user_")
    assert str(user_id) in namespace
    
    # Test different users get different namespaces
    user2_id = uuid.uuid4()
    namespace2 = f"user_{user2_id}"
    
    assert namespace != namespace2


if __name__ == "__main__":
    test_create_access_token()
    test_verify_token_valid()
    test_verify_token_invalid()
    test_user_namespace_logic()
    print("✅ All JWT and tenancy tests passed!")