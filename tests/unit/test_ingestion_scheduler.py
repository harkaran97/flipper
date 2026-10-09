"""
test_ingestion_scheduler.py

Unit tests for TASK_039 — _next_9am_utc must roll over month and year
boundaries without raising (the 31 March 2026 crash).

Run from backend/ directory:
    python -m pytest ../tests/unit/test_ingestion_scheduler.py -v
"""
import os
import sys
from datetime import datetime, timezone
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../backend"))

import pytest

from app.workers import ingestion_worker


@pytest.mark.parametrize(
    "now, expected",
    [
        (datetime(2026, 3, 31, 10, 0, tzinfo=timezone.utc), datetime(2026, 4, 1, 9, 0, tzinfo=timezone.utc)),
        (datetime(2026, 12, 31, 10, 0, tzinfo=timezone.utc), datetime(2027, 1, 1, 9, 0, tzinfo=timezone.utc)),
        (datetime(2028, 2, 29, 10, 0, tzinfo=timezone.utc), datetime(2028, 3, 1, 9, 0, tzinfo=timezone.utc)),
        (datetime(2026, 10, 9, 8, 0, tzinfo=timezone.utc), datetime(2026, 10, 9, 9, 0, tzinfo=timezone.utc)),
    ],
)
def test_next_9am_utc(now, expected):
    with patch.object(ingestion_worker, "datetime") as mock_dt:
        mock_dt.now.return_value = now
        assert ingestion_worker._next_9am_utc() == expected
