import pytest
import sys
import os
from unittest.mock import Mock

# Add backend to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

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
        "content": "Test response"
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