import os
import sys
from unittest.mock import Mock, patch

import pytest

# Add backend to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

# Patch external services before ANY imports happen
with patch.dict("sys.modules", {
    "pinecone": Mock(),
    "pinecone.grpc": Mock(),
    "openai": Mock(),
}):
    # Mock the classes at import time
    import pinecone.grpc
    import openai
    
    # Create mock instances that will be used
    mock_pinecone = Mock()
    mock_index = Mock()
    mock_index.upsert.return_value = None
    mock_index.query.return_value = Mock(matches=[])
    mock_pinecone.Index.return_value = mock_index
    
    mock_openai_client = Mock()
    mock_completion = Mock()
    mock_completion.choices = [Mock()]
    mock_completion.choices[0].message.content = "Test response"
    mock_completion.choices[0].message.tool_calls = None
    mock_completion.choices[0].message.to_dict.return_value = {"role": "assistant", "content": "Test response"}
    mock_openai_client.chat.completions.create.return_value = mock_completion
    
    # Mock embeddings
    mock_embedding_response = Mock()
    mock_embedding_response.data = [Mock(embedding=[0.1] * 1536)]
    mock_openai_client.embeddings.create.return_value = mock_embedding_response
    
    # Replace the actual classes
    pinecone.grpc.PineconeGRPC = Mock(return_value=mock_pinecone)
    openai.OpenAI = Mock(return_value=mock_openai_client)

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


# Mock external services to prevent real API calls during testing
# Apply patches at session level to catch imports


@pytest.fixture(autouse=True, scope="session")
def mock_all_external_services():
    """Mock all external services at session start."""
    with (
        patch("pinecone.grpc.PineconeGRPC") as mock_pinecone_class,
        patch("openai.OpenAI") as mock_openai_class,
        patch("auth.oauth.httpx.AsyncClient") as mock_httpx_class,
    ):
        # Mock Pinecone
        mock_pinecone = Mock()
        mock_index = Mock()
        mock_index.upsert.return_value = None
        mock_index.query.return_value = Mock(matches=[])
        mock_pinecone.Index.return_value = mock_index
        mock_pinecone_class.return_value = mock_pinecone

        # Mock OpenAI
        mock_openai = Mock()
        mock_completion = Mock()
        mock_completion.choices = [Mock()]
        mock_completion.choices[0].message.content = "Test response"
        mock_completion.choices[0].message.tool_calls = None
        mock_completion.choices[0].message.to_dict.return_value = {
            "role": "assistant",
            "content": "Test response",
        }
        mock_openai.chat.completions.create.return_value = mock_completion

        # Mock embeddings
        mock_embedding_response = Mock()
        mock_embedding_response.data = [Mock(embedding=[0.1] * 1536)]
        mock_openai.embeddings.create.return_value = mock_embedding_response
        mock_openai_class.return_value = mock_openai

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
            "pinecone": mock_pinecone,
            "openai": mock_openai,
            "index": mock_index,
            "httpx": mock_httpx,
        }
