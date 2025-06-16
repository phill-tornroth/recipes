import os


class Config:
    # API Keys
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    PINECONE_API_KEY: str = os.getenv("PINECONE_API_KEY", "")

    # Google OAuth
    GOOGLE_CLIENT_ID: str = os.getenv("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET: str = os.getenv("GOOGLE_CLIENT_SECRET", "")

    # Database
    DB_HOST: str = os.getenv("DB_HOST", "database")
    DB_PORT: str = os.getenv("DB_PORT", "5432")
    DB_NAME: str = os.getenv("DB_NAME", "recipes")
    DB_USER: str = os.getenv("DB_USER", "recipe_user")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "bananabread")

    # Application
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "info")
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    RELOAD: bool = os.getenv("RELOAD", "true").lower() == "true"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@"
            f"{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    def validate_required_vars(self) -> None:
        """Validate that required environment variables are set."""
        required_vars = [
            ("OPENAI_API_KEY", self.OPENAI_API_KEY),
            ("PINECONE_API_KEY", self.PINECONE_API_KEY),
            ("GOOGLE_CLIENT_ID", self.GOOGLE_CLIENT_ID),
            ("GOOGLE_CLIENT_SECRET", self.GOOGLE_CLIENT_SECRET),
        ]

        missing_vars = [name for name, value in required_vars if not value]

        if missing_vars:
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing_vars)}"
            )


config = Config()
