"""
Test file to verify mocking works correctly without importing assistant module.
This isolates the mocking logic from the main assistant imports.
"""

import os
import sys
from unittest.mock import Mock, patch

# Set up environment before importing anything
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
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))


def test_mock_setup():
    """Test that our mocking approach works."""
    with (
        patch("pinecone.grpc.PineconeGRPC") as mock_pinecone_class,
        patch("openai.OpenAI") as mock_openai_class,
        patch("assistant.normalize_image_to_base64_jpeg") as mock_normalize,
    ):
        # Set up mocks
        mock_pinecone = Mock()
        mock_index = Mock()
        mock_index.upsert.return_value = None
        mock_index.query.return_value = Mock(matches=[])
        mock_pinecone.Index.return_value = mock_index
        mock_pinecone_class.return_value = mock_pinecone

        mock_openai = Mock()
        mock_completion = Mock()
        mock_completion.choices = [Mock()]
        mock_completion.choices[0].message.content = "Test response"
        mock_openai.chat.completions.create.return_value = mock_completion
        mock_openai_class.return_value = mock_openai

        # Mock the image normalization function
        mock_normalize.return_value = "data:image/jpeg;base64,fake_base64_data"

        # Now import assistant (this will use our mocks)
        import assistant

        # Test that the mocked objects are being used
        assert assistant.pc is not None
        assert assistant.index is not None

        # Test a basic function
        result = assistant.normalize_image_to_base64_jpeg(b"fake_image_data")
        assert result == "data:image/jpeg;base64,fake_base64_data"


def test_basic_functionality():
    """Test basic functionality with mocks."""
    with (
        patch("pinecone.grpc.PineconeGRPC") as mock_pinecone_class,
        patch("openai.OpenAI") as mock_openai_class,
    ):
        # Set up minimal mocks
        mock_pinecone = Mock()
        mock_index = Mock()
        mock_pinecone.Index.return_value = mock_index
        mock_pinecone_class.return_value = mock_pinecone

        mock_openai = Mock()
        mock_openai_class.return_value = mock_openai

        # Import config to make sure it works
        from config import Config

        config = Config()
        assert config.OPENAI_API_KEY == "test-openai-key"
        assert config.PINECONE_API_KEY == "test-pinecone-key"
