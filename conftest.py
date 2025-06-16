"""
Global conftest.py at project root to patch external services before any imports.
"""

import os
import sys
from unittest.mock import Mock, patch

# Set up environment variables first
test_env_vars = {
    "PYTEST_CURRENT_TEST": "true",  # Signal to backend that we're in test mode
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
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))


# Apply patches at the very beginning
def pytest_configure(config):
    """Configure pytest by setting up mocks before any imports."""
    # Create mock instances
    mock_pinecone_instance = Mock()
    mock_index = Mock()
    mock_index.upsert.return_value = None
    mock_index.query.return_value = Mock(matches=[])
    mock_pinecone_instance.Index.return_value = mock_index

    mock_openai_instance = Mock()
    mock_completion = Mock()
    mock_completion.choices = [Mock()]
    mock_completion.choices[0].message.content = "Test response"
    mock_completion.choices[0].message.tool_calls = None
    mock_completion.choices[0].message.to_dict.return_value = {
        "role": "assistant",
        "content": "Test response",
    }
    mock_openai_instance.chat.completions.create.return_value = mock_completion

    # Mock embeddings
    mock_embedding_response = Mock()
    mock_embedding_response.data = [Mock(embedding=[0.1] * 1536)]
    mock_openai_instance.embeddings.create.return_value = mock_embedding_response

    # Start patches globally
    patch("pinecone.grpc.PineconeGRPC", return_value=mock_pinecone_instance).start()
    patch("openai.OpenAI", return_value=mock_openai_instance).start()
