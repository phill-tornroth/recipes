import pytest
from unittest.mock import Mock, patch, AsyncMock
import json
import uuid

import assistant


class TestAssistant:
    def test_normalize_image_to_base64_jpeg(self):
        """Test image normalization function."""
        # This would require a test image file, so we'll mock it
        with patch('assistant.Image') as mock_image:
            mock_img = Mock()
            mock_img.size = (1024, 768)
            mock_img.convert.return_value = mock_img
            mock_img.resize.return_value = mock_img
            mock_img.save = Mock()
            
            mock_image.open.return_value.__enter__.return_value = mock_img
            
            with patch('assistant.BytesIO') as mock_bytesio:
                mock_buffer = Mock()
                mock_buffer.read.return_value = b'fake_jpeg_data'
                mock_bytesio.return_value = mock_buffer
                
                with patch('assistant.base64.b64encode') as mock_b64encode:
                    mock_b64encode.return_value = b'fake_base64_data'
                    
                    result = assistant.normalize_image_to_base64_jpeg(b'fake_image_data')
                    assert result == 'fake_base64_data'

    def test_extract_url_success(self):
        """Test successful URL content extraction."""
        mock_response = Mock()
        mock_response.content = b'<html><body>Test content</body></html>'
        mock_response.raise_for_status = Mock()
        
        with patch('assistant.requests.get', return_value=mock_response):
            with patch('assistant.BeautifulSoup') as mock_soup:
                mock_soup.return_value.get_text.return_value = "Test content"
                mock_soup.return_value.find.return_value = None
                
                result = assistant.extract_url("https://example.com")
                assert result == "Test content"

    def test_extract_url_failure(self):
        """Test URL extraction failure handling."""
        with patch('assistant.requests.get', side_effect=Exception("Network error")):
            result = assistant.extract_url("https://example.com")
            assert "An error occurred while processing the URL" in result

    def test_process_text_with_urls(self):
        """Test URL processing in text."""
        test_text = "Check out this recipe: https://example.com/recipe"
        
        with patch('assistant.extract_url', return_value="Recipe content"):
            result = assistant.process_text_with_urls(test_text)
            assert "https://example.com/recipe (Extracted Content: Recipe content)" in result

    def test_get_embeddings(self):
        """Test embeddings generation."""
        mock_response = Mock()
        mock_response.data = [Mock(embedding=[0.1, 0.2, 0.3])]
        
        with patch('assistant.openai_client') as mock_client:
            mock_client.embeddings.create.return_value = mock_response
            
            result = assistant.get_embeddings("test content")
            assert result == [[0.1, 0.2, 0.3]]

    def test_find_relevant_recipes(self):
        """Test relevant recipe finding with user isolation."""
        user_id = uuid.uuid4()
        mock_query_results = Mock()
        mock_query_results.matches = [
            Mock(metadata={"contents": "Recipe 1"}),
            Mock(metadata={"contents": "Recipe 2"})
        ]
        
        with patch('assistant.get_embeddings', return_value=[[0.1, 0.2, 0.3]]):
            with patch('assistant.index') as mock_index:
                mock_index.query.return_value = mock_query_results
                
                result = assistant.find_relevant_recipes("pasta", user_id)
                assert result == ["Recipe 1", "Recipe 2"]
                
                # Verify user namespace isolation
                mock_index.query.assert_called_with(
                    namespace=f"user_{user_id}",
                    vector=[0.1, 0.2, 0.3],
                    top_k=5,
                    include_values=False,
                    include_metadata=True,
                )

    def test_add_recipe(self):
        """Test recipe addition with user isolation."""
        user_id = uuid.uuid4()
        test_recipe = "recipe:\n  title: Test Recipe"
        
        with patch('assistant.update_recipe') as mock_update:
            with patch('assistant.uuid.uuid4') as mock_uuid:
                mock_uuid.return_value = "test-uuid"
                
                result = assistant.add_recipe(test_recipe, user_id)
                assert result == "test-uuid"
                mock_update.assert_called_once_with("test-uuid", test_recipe, user_id)

    def test_update_recipe(self):
        """Test recipe update with user isolation."""
        user_id = uuid.uuid4()
        test_recipe = "recipe:\n  title: Test Recipe"
        test_id = "test-recipe-id"
        
        with patch('assistant.yaml.safe_load') as mock_yaml_load:
            with patch('assistant.yaml.dump') as mock_yaml_dump:
                with patch('assistant.get_embeddings') as mock_embeddings:
                    with patch('assistant.index') as mock_index:
                        mock_yaml_load.return_value = {"title": "Test Recipe"}
                        mock_yaml_dump.return_value = test_recipe
                        mock_embeddings.return_value = [[0.1, 0.2, 0.3]]
                        
                        result = assistant.update_recipe(test_id, test_recipe, user_id)
                        assert result == test_id
                        
                        # Verify user namespace isolation
                        mock_index.upsert.assert_called_once()
                        call_args = mock_index.upsert.call_args
                        assert call_args[1]["namespace"] == f"user_{user_id}"