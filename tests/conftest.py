"""
Simple conftest that properly mocks external services before imports.
"""

import os
import sys
from unittest.mock import Mock, patch

# Set environment variables first
test_env_vars = {
    "OPENAI_API_KEY": "test-openai-key",
    "PINECONE_API_KEY": "test-pinecone-key",
    "GOOGLE_CLIENT_ID": "test-google-client-id",
    "GOOGLE_CLIENT_SECRET": "test-google-client-secret",
    "SECRET_KEY": "test-secret-key-for-jwt-signing",
    "DB_HOST": "localhost",
    "DB_PORT": "5432",
    "DB_NAME": "test_recipes",
    "DB_USER": "test_user",
    "DB_PASSWORD": "test_password",
}

for key, value in test_env_vars.items():
    os.environ.setdefault(key, value)

# Add backend to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

# Import pytest after setting up environment
import pytest

# Global mocks that will be reused
_mock_pinecone_instance = Mock()
_mock_index = Mock()
_mock_index.upsert.return_value = None
_mock_index.query.return_value = Mock(matches=[])
_mock_pinecone_instance.Index.return_value = _mock_index

_mock_openai_instance = Mock()
_mock_completion = Mock()
_mock_completion.choices = [Mock()]
_mock_completion.choices[0].message.content = "Test response"
_mock_completion.choices[0].message.tool_calls = None
_mock_completion.choices[0].message.to_dict.return_value = {
    "role": "assistant",
    "content": "Test response",
}
_mock_openai_instance.chat.completions.create.return_value = _mock_completion

# Mock embeddings
_mock_embedding_response = Mock()
_mock_embedding_response.data = [Mock(embedding=[0.1] * 1536)]
_mock_openai_instance.embeddings.create.return_value = _mock_embedding_response


@pytest.fixture(autouse=True, scope="session")
def mock_external_services():
    """Mock external services at the session level."""
    with (
        patch("pinecone.grpc.PineconeGRPC", return_value=_mock_pinecone_instance),
        patch("openai.OpenAI", return_value=_mock_openai_instance),
        patch("auth.oauth.httpx.AsyncClient") as mock_httpx_class,
    ):
        # Mock httpx for OAuth
        mock_httpx = Mock()
        mock_response = Mock()
        mock_response.json.return_value = {
            "email": "test@example.com",
            "name": "Test User",
            "picture": "https://example.com/avatar.jpg",
            "sub": "123456789",
        }
        mock_httpx.get.return_value = mock_response
        mock_httpx_class.return_value = mock_httpx

        yield {
            "pinecone": _mock_pinecone_instance,
            "openai": _mock_openai_instance,
            "index": _mock_index,
            "httpx": mock_httpx,
        }


@pytest.fixture
def test_user():
    """Create a test user for testing."""
    import uuid
    from datetime import datetime

    from auth.models import User

    return User(
        id=uuid.uuid4(),
        email="test@example.com",
        name="Test User",
        avatar_url="https://example.com/avatar.jpg",
        provider="google",
        provider_id="123456789",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        is_active=True,
    )


@pytest.fixture
def mock_db_session():
    """Mock database session for testing."""
    mock_session = Mock()
    mock_session.add = Mock()
    mock_session.commit = Mock()
    mock_session.rollback = Mock()
    mock_session.refresh = Mock()
    mock_session.query = Mock()
    return mock_session
