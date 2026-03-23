"""
eBay OAuth 2.0 Client

Handles client credentials flow for the eBay Browse API.
Caches tokens in memory and auto-refreshes before expiry.
Never instantiated when EBAY_STUB=true.
"""

import base64
import logging
import time

import httpx

from config import settings

logger = logging.getLogger(__name__)

EBAY_OAUTH_URL = "https://api.ebay.com/identity/v1/oauth2/token"
EBAY_BROWSE_API_BASE = "https://api.ebay.com/buy/browse/v1"
EBAY_OAUTH_SCOPE = "https://api.ebay.com/oauth/api_scope"


class EbayAuthError(Exception):
    """Raised when eBay authentication fails or credentials are missing."""


class EbayClient:
    """Authenticated HTTP client for the eBay Browse API."""

    def __init__(self) -> None:
        self._token: str | None = None
        self._token_expiry: float = 0.0
        self._http = httpx.AsyncClient(timeout=30.0)

    async def get_token(self) -> str:
        """Returns a valid Bearer token, refreshing if needed."""
        if self._token and time.time() < self._token_expiry - 60:
            return self._token

        if not settings.ebay_app_id or not settings.ebay_cert_id:
            raise EbayAuthError("EBAY_APP_ID and EBAY_CERT_ID must be set")

        credentials = f"{settings.ebay_app_id}:{settings.ebay_cert_id}"
        encoded = base64.b64encode(credentials.encode()).decode()

        response = await self._http.post(
            EBAY_OAUTH_URL,
            headers={
                "Authorization": f"Basic {encoded}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={
                "grant_type": "client_credentials",
                "scope": EBAY_OAUTH_SCOPE,
            },
        )

        if response.status_code != 200:
            raise EbayAuthError(
                f"eBay OAuth failed: {response.status_code} — {response.text}"
            )

        data = response.json()
        self._token = data["access_token"]
        self._token_expiry = time.time() + data["expires_in"]
        logger.info("eBay token refreshed, expires in %ds", data["expires_in"])
        return self._token

    async def get(self, path: str, params: dict) -> dict:
        """Authenticated GET against the eBay Browse API."""
        token = await self.get_token()
        response = await self._http.get(
            f"{EBAY_BROWSE_API_BASE}{path}",
            params=params,
            headers={
                "Authorization": f"Bearer {token}",
                "X-EBAY-C-MARKETPLACE-ID": "EBAY_GB",
            },
        )
        response.raise_for_status()
        return response.json()
