import os
from unittest.mock import patch

import pytest
from config import Config


class TestConfig:
    def test_config_defaults(self):
        """Test that config loads from environment correctly."""
        config = Config()
        assert config.DB_HOST == "localhost"  # Set by test env
        assert config.DB_PORT == "5432"
        assert config.DB_NAME == "test_recipes"  # Set by test env
        assert config.HOST == "0.0.0.0"
        assert config.PORT == 8000

    def test_database_url_construction(self):
        """Test that database URL is constructed correctly."""
        config = Config()
        expected_url = (
            f"postgresql://{config.DB_USER}:{config.DB_PASSWORD}@"
            f"{config.DB_HOST}:{config.DB_PORT}/{config.DB_NAME}"
        )
        assert config.DATABASE_URL == expected_url

    def test_validate_required_vars_missing_keys(self):
        """Test that validation fails when required keys are missing."""
        # Clear only the required keys, keep others for the test environment to work
        clear_keys = [
            "OPENAI_API_KEY",
            "PINECONE_API_KEY",
            "GOOGLE_CLIENT_ID",
            "GOOGLE_CLIENT_SECRET",
        ]
        with patch.dict(os.environ, {key: "" for key in clear_keys}):
            config = Config()
            with pytest.raises(
                ValueError, match="Missing required environment variables"
            ):
                config.validate_required_vars()

    def test_validate_required_vars_success(self):
        """Test that validation passes when required keys are present."""
        with patch.dict(
            os.environ,
            {
                "OPENAI_API_KEY": "test_openai_key",
                "PINECONE_API_KEY": "test_pinecone_key",
                "GOOGLE_CLIENT_ID": "test_client_id",
                "GOOGLE_CLIENT_SECRET": "test_client_secret",
            },
        ):
            config = Config()
            # Should not raise an exception
            config.validate_required_vars()

    def test_boolean_config_parsing(self):
        """Test that boolean environment variables are parsed correctly."""
        with patch.dict(os.environ, {"DEBUG": "true", "RELOAD": "false"}):
            config = Config()
            assert config.DEBUG is True
            assert config.RELOAD is False
