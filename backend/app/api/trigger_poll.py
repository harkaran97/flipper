"""
trigger_poll.py

POST /api/v1/trigger-poll — manually trigger one ingestion cycle.
Returns 202 immediately; runs poll in the background.
Enforces a 5-minute cooldown to prevent credit burn from rapid taps.
"""
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends

from app.api.deps import get_bus
from app.events.bus import EventBus

logger = logging.getLogger(__name__)

router = APIRouter()

_COOLDOWN_SECONDS = 300  # 5 minutes

# In-memory timestamp of the last triggered poll (manual or scheduled)
_last_triggered_at: datetime | None = None


def _seconds_since_last_trigger() -> float | None:
    if _last_triggered_at is None:
        return None
    return (datetime.now(timezone.utc) - _last_triggered_at).total_seconds()


async def _run_poll(bus: EventBus) -> None:
    global _last_triggered_at
    try:
        from app.workers.ingestion_worker import run_once
        stats = await run_once(bus)
        logger.info("[INGESTION] Manual poll completed: %s", stats)
    except Exception as e:
        logger.error("[INGESTION] Manual poll failed: %s", e, exc_info=True)


@router.post("/trigger-poll", status_code=202)
async def trigger_poll(
    background_tasks: BackgroundTasks,
    bus: EventBus = Depends(get_bus),
) -> dict:
    """
    Trigger an ingestion cycle immediately.
    Returns 202 if started, 429 if within the 5-minute cooldown window.
    """
    global _last_triggered_at

    elapsed = _seconds_since_last_trigger()
    if elapsed is not None and elapsed < _COOLDOWN_SECONDS:
        retry_after = int(_COOLDOWN_SECONDS - elapsed)
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=429,
            content={
                "status": "cooldown",
                "message": "Poll triggered recently, please wait before refreshing again",
                "retry_after_seconds": retry_after,
            },
        )

    _last_triggered_at = datetime.now(timezone.utc)
    logger.info("[INGESTION] Manual poll triggered via API")
    background_tasks.add_task(_run_poll, bus)

    return {"status": "triggered", "message": "Poll cycle started"}
