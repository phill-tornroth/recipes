import os
import sys
from unittest.mock import Mock, patch

import pytest

# Add backend to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

# Mock environment variables for testing
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

# Set environment variables before importing modules
for key, value in test_env_vars.items():
    os.environ.setdefault(key, value)


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client for testing."""
    mock_client = Mock()
    mock_completion = Mock()
    mock_completion.choices = [Mock()]
    mock_completion.choices[0].message.content = "Test response"
    mock_completion.choices[0].message.tool_calls = None
    mock_completion.choices[0].message.to_dict.return_value = {
        "role": "assistant",
        "content": "Test response",
    }
    mock_client.chat.completions.create.return_value = mock_completion
    return mock_client


@pytest.fixture
def mock_pinecone():
    """Mock Pinecone client for testing."""
    mock_pc = Mock()
    mock_index = Mock()
    mock_pc.Index.return_value = mock_index
    return mock_pc, mock_index


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


# Mock external services before any modules are imported
# This prevents real API calls during import
_mock_pinecone = Mock()
_mock_index = Mock()
_mock_pinecone.Index.return_value = _mock_index

_mock_openai = Mock()
_mock_response = Mock()
_mock_response.data = [Mock(embedding=[0.1, 0.2, 0.3])]
_mock_openai.embeddings.create.return_value = _mock_response

# Patch the modules before they're imported
with patch.dict(
    "sys.modules",
    {
        "pinecone.grpc": Mock(PineconeGRPC=lambda **kwargs: _mock_pinecone),
        "openai": Mock(OpenAI=lambda **kwargs: _mock_openai),
    },
):
    pass


@pytest.fixture(autouse=True)
def mock_external_services():
    """Automatically mock external services for all tests."""
    with (
        patch("assistant.pc", _mock_pinecone),
        patch("assistant.index", _mock_index),
        patch("assistant.openai_client", _mock_openai),
        patch("auth.oauth.httpx.AsyncClient") as mock_httpx,
    ):

        yield {
            "pinecone": _mock_pinecone,
            "openai": _mock_openai,
            "httpx": mock_httpx,
            "index": _mock_index,
        }
