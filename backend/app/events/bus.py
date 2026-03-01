import asyncio
import logging
from collections import defaultdict
from collections.abc import Callable

from app.events.types import Event, EventType

logger = logging.getLogger(__name__)


class EventBus:
    def __init__(self) -> None:
        self._handlers: dict[EventType, list[Callable]] = defaultdict(list)

    def subscribe(self, event_type: EventType, handler: Callable) -> None:
        self._handlers[event_type].append(handler)

    async def emit(self, event: Event) -> None:
        handlers = self._handlers.get(event.type, [])
        if not handlers:
            return

        results = await asyncio.gather(
            *(self._safe_call(handler, event) for handler in handlers),
            return_exceptions=True,
        )

        for result in results:
            if isinstance(result, Exception):
                logger.error("Event handler failed for %s: %s", event.type, result, exc_info=result)

    async def _safe_call(self, handler: Callable, event: Event) -> None:
        try:
            await handler(event)
        except Exception:
            logger.error("Handler %s failed for event %s", handler.__name__, event.type, exc_info=True)
            raise
