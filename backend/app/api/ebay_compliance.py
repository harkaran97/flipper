"""eBay marketplace account deletion compliance endpoints.

eBay requires all production API partners to implement these endpoints to handle
account deletion notifications per their marketplace compliance policy.
Flipper stores no eBay user PII, so no deletion action is needed beyond acknowledgement.
"""

import hashlib
import logging

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from config import settings

logger = logging.getLogger(__name__)

router = APIRouter()

ENDPOINT_URL = "https://flipper-production-dca0.up.railway.app/api/v1/ebay/account-deletion"


@router.get("/ebay/account-deletion")
async def ebay_account_deletion_challenge(request: Request):
    """Handle eBay verification challenge for account deletion endpoint.

    eBay sends ?challenge_code=<code> to verify endpoint ownership.
    Response must be SHA256 hash of: challenge_code + verification_token + endpoint_url.
    """
    challenge_code = request.query_params.get("challenge_code")
    token = settings.ebay_verification_token
    hash_input = challenge_code + token + ENDPOINT_URL
    challenge_response = hashlib.sha256(hash_input.encode()).hexdigest()
    return JSONResponse(content={"challengeResponse": challenge_response})


@router.post("/ebay/account-deletion")
async def ebay_account_deletion_notification(request: Request):
    """Handle eBay account deletion notification.

    Flipper stores no eBay user PII, so no deletion action is needed.
    Log the notification and return 200 to acknowledge receipt.
    """
    body = await request.body()
    logger.info("eBay account deletion notification received: %s", body)
    return {"status": "ok"}
