from typing import Optional
from urllib.parse import urlencode

import httpx
from config import config

from .models import GoogleUserInfo


class GoogleOAuth:
    def __init__(self):
        self.client_id = config.GOOGLE_CLIENT_ID
        self.client_secret = config.GOOGLE_CLIENT_SECRET
        self.redirect_uri = (
            "http://localhost:8000/auth/google/callback"  # TODO: Make configurable
        )
        self.scope = "openid email profile"

        # OAuth endpoints
        self.auth_url = "https://accounts.google.com/o/oauth2/v2/auth"
        self.token_url = "https://oauth2.googleapis.com/token"
        self.userinfo_url = "https://www.googleapis.com/oauth2/v2/userinfo"

    def get_auth_url(self, state: Optional[str] = None) -> str:
        """Generate Google OAuth authorization URL."""
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": self.scope,
            "response_type": "code",
            "access_type": "offline",
            "prompt": "consent",
        }

        if state:
            params["state"] = state

        return f"{self.auth_url}?{urlencode(params)}"

    async def exchange_code_for_token(self, code: str) -> Optional[str]:
        """Exchange authorization code for access token."""
        token_data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": self.redirect_uri,
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(self.token_url, data=token_data)
                response.raise_for_status()
                token_response = response.json()
                return token_response.get("access_token")
            except httpx.HTTPError:
                return None

    async def get_user_info(self, access_token: str) -> Optional[GoogleUserInfo]:
        """Get user information from Google using access token."""
        headers = {"Authorization": f"Bearer {access_token}"}

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(self.userinfo_url, headers=headers)
                response.raise_for_status()
                user_data = response.json()

                return GoogleUserInfo(
                    id=user_data["id"],
                    email=user_data["email"],
                    name=user_data["name"],
                    picture=user_data.get("picture"),
                    verified_email=user_data.get("verified_email", True),
                )
            except (httpx.HTTPError, KeyError):
                return None


# Global OAuth instance
google_oauth = GoogleOAuth()
