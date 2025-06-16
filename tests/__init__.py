"""
Test package initialization that patches external services before any imports.
"""

import os
import sys
from unittest.mock import Mock, patch

# Set up environment variables first
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

# Create global mocks that will persist
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

# Start patches immediately
_pinecone_patcher = patch(
    "pinecone.grpc.PineconeGRPC", return_value=_mock_pinecone_instance
)
_openai_patcher = patch("openai.OpenAI", return_value=_mock_openai_instance)

_pinecone_patcher.start()
_openai_patcher.start()

# Store references for cleanup
_active_patches = [_pinecone_patcher, _openai_patcher]
