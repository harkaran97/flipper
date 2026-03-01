"""
device_tokens.py

POST /device-tokens — register an Expo push token for push notifications.
Called by the iOS app on first launch after permission is granted.
"""
import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.database import AsyncSessionLocal
from app.models.device_token import DeviceToken

logger = logging.getLogger(__name__)

router = APIRouter()


class DeviceTokenRequest(BaseModel):
    token: str
    platform: str = "ios"


class DeviceTokenResponse(BaseModel):
    status: str
    token: str


@router.post("/device-tokens", response_model=DeviceTokenResponse)
async def register_device_token(body: DeviceTokenRequest) -> DeviceTokenResponse:
    """Store an Expo push token. Idempotent — safe to call on every app launch."""
    async with AsyncSessionLocal() as session:
        existing = await session.execute(
            select(DeviceToken).where(DeviceToken.token == body.token)
        )
        if existing.scalar_one_or_none():
            return DeviceTokenResponse(status="already_registered", token=body.token)

        token = DeviceToken(token=body.token, platform=body.platform)
        session.add(token)
        try:
            await session.commit()
        except IntegrityError:
            await session.rollback()
            # Race condition — another request registered the same token
            return DeviceTokenResponse(status="already_registered", token=body.token)

    logger.info("Registered device token for platform=%s", body.platform)
    return DeviceTokenResponse(status="registered", token=body.token)
