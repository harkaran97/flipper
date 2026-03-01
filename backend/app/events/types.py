from enum import Enum
from dataclasses import dataclass
from datetime import datetime
import uuid


class EventType(str, Enum):
    NEW_LISTING_FOUND = "NEW_LISTING_FOUND"
    VEHICLE_ENRICHED = "VEHICLE_ENRICHED"
    PROBLEMS_DETECTED = "PROBLEMS_DETECTED"
    REPAIR_ESTIMATED = "REPAIR_ESTIMATED"
    MARKET_VALUE_ESTIMATED = "MARKET_VALUE_ESTIMATED"
    OPPORTUNITY_CREATED = "OPPORTUNITY_CREATED"


@dataclass
class Event:
    type: EventType
    payload: dict
    event_id: str = None
    created_at: datetime = None

    def __post_init__(self):
        if not self.event_id:
            self.event_id = str(uuid.uuid4())
        if not self.created_at:
            self.created_at = datetime.utcnow()
