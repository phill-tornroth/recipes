import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from config import config
from jose import JWTError, jwt


class JWTHandler:
    SECRET_KEY = config.SECRET_KEY
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_HOURS = 24 * 7  # 1 week

    @classmethod
    def create_access_token(cls, user_id: uuid.UUID, email: str) -> str:
        """Create a JWT access token for the user."""
        expire = datetime.utcnow() + timedelta(hours=cls.ACCESS_TOKEN_EXPIRE_HOURS)
        to_encode = {
            "sub": str(user_id),
            "email": email,
            "exp": expire,
            "iat": datetime.utcnow(),
        }
        encoded_jwt = jwt.encode(to_encode, cls.SECRET_KEY, algorithm=cls.ALGORITHM)
        return encoded_jwt

    @classmethod
    def verify_token(cls, token: str) -> Optional[Dict[str, Any]]:
        """Verify and decode a JWT token."""
        try:
            payload = jwt.decode(token, cls.SECRET_KEY, algorithms=[cls.ALGORITHM])
            user_id: str = payload.get("sub")
            email: str = payload.get("email")

            if user_id is None or email is None:
                return None

            return {"user_id": uuid.UUID(user_id), "email": email}
        except JWTError:
            return None
        except ValueError:  # Invalid UUID
            return None

    @classmethod
    def decode_token(cls, token: str) -> Optional[Dict[str, Any]]:
        """Decode token without verification (for debugging)."""
        try:
            return jwt.get_unverified_claims(token)
        except JWTError:
            return None
