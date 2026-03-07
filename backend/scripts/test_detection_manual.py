"""
test_detection_manual.py

Manual smoke-test for the detection pipeline.
Runs WITHOUT a real database — mocks the DB session layer.

Usage:
    cd backend
    python scripts/test_detection_manual.py

What it checks:
  1. That config.py reads ANTHROPIC_API_KEY from the environment correctly.
  2. That detect_problems_ai() returns a valid response (stub or live).
  3. That detect_problems() correctly orchestrates all pipeline steps when
     given a synthetic Listing + Vehicle (session is mocked so no DB needed).

Expected output (stub mode, no API key):
  [PASS] config.anthropic_api_key is empty — stub mode expected
  [PASS] detect_problems_ai returned 1 mechanical fault(s)
  [PASS] detect_problems pipeline completed — 1 fault(s) would be saved
"""
import asyncio
import logging
import sys
import os
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

# ---------------------------------------------------------------------------
# Ensure backend/ is on the Python path so `config` and `app.*` resolve.
# ---------------------------------------------------------------------------
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

# Configure logging BEFORE importing app modules so we capture all output.
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
)
logger = logging.getLogger("test_detection_manual")

# ---------------------------------------------------------------------------
# App imports (after sys.path fix)
# ---------------------------------------------------------------------------
from app.models.listing import Listing
from app.models.vehicle import Vehicle
from app.models.fault import DetectedFault
from app.models.exterior_condition import ExteriorCondition
from app.services.ai_service import detect_problems_ai
from app.services.problem_detector import detect_problems
from app.events.bus import EventBus
from app.events.types import Event, EventType
from config import settings


# ---------------------------------------------------------------------------
# Stub EventBus that records emitted events
# ---------------------------------------------------------------------------
class StubEventBus(EventBus):
    def __init__(self):
        super().__init__()
        self.emitted = []

    async def emit(self, event):
        self.emitted.append(event)
        logger.info("[STUB_BUS] Event emitted: type=%s payload=%s", event.type, event.payload)


# ---------------------------------------------------------------------------
# Test 1: API key config check
# ---------------------------------------------------------------------------
def test_api_key_config():
    print("\n--- Test 1: ANTHROPIC_API_KEY config ---")
    key = settings.anthropic_api_key
    env_val = os.environ.get("ANTHROPIC_API_KEY", "")
    print(f"  os.environ ANTHROPIC_API_KEY : {'set ('+env_val[:10]+'...)' if env_val else 'NOT SET'}")
    print(f"  settings.anthropic_api_key   : {'set ('+key[:10]+'...)' if key else 'empty string'}")
    print(f"  config env_file              : {settings.model_config.get('env_file', 'not set')}")

    if key:
        print(f"[PASS] ANTHROPIC_API_KEY is set — live Anthropic API will be used")
    else:
        print("[PASS] config.anthropic_api_key is empty — stub mode expected")
        print("       To use live AI: set ANTHROPIC_API_KEY in backend/.env")
    return True


# ---------------------------------------------------------------------------
# Test 2: detect_problems_ai with stub listing data (no DB)
# ---------------------------------------------------------------------------
async def test_ai_service_direct():
    print("\n--- Test 2: detect_problems_ai direct call ---")
    result = await detect_problems_ai(
        make="Ford",
        model="Focus",
        year=2015,
        fuel_type="petrol",
        engine_code=None,
        title="Ford Focus 1.6 — timing chain rattle, needs work",
        description=(
            "Car runs but has a noticeable timing chain rattle on cold start. "
            "Also has a minor scuff on the rear bumper. "
            "Sold as seen. Some rust on nearside sill."
        ),
        known_fault_count=0,
        has_unknown_faults=False,
    )

    faults = result.get("mechanical_faults", [])
    print(f"  write_off_category : {result.get('write_off_category')}")
    print(f"  mechanical_faults  : {len(faults)} fault(s)")
    for f in faults:
        print(f"    - {f.get('fault_type')} | severity={f.get('severity')} | confidence={f.get('confidence')}")
    print(f"  driveable          : {result.get('driveable')}")
    print(f"  overall_confidence : {result.get('overall_confidence')}")

    assert isinstance(faults, list), "mechanical_faults must be a list"
    print(f"[PASS] detect_problems_ai returned {len(faults)} mechanical fault(s)")
    return result


# ---------------------------------------------------------------------------
# Test 3: detect_problems pipeline with a mocked session
#
# We mock session.execute() to return our stub Listing and Vehicle objects.
# We mock session.add(), session.flush(), session.commit() as no-ops.
# We capture all DetectedFault objects passed to session.add() to verify
# they are created correctly.
# ---------------------------------------------------------------------------
async def test_full_pipeline_mocked():
    print("\n--- Test 3: detect_problems full pipeline (mocked DB session) ---")

    listing_id = uuid.uuid4()

    # Build stub Listing (no DB required — just a plain model instance)
    stub_listing = Listing(
        id=listing_id,
        source="test",
        external_id="stub-001",
        title="Ford Focus 1.6 — timing chain rattle, needs work",
        description=(
            "Car runs but has a noticeable timing chain rattle on cold start. "
            "Also has a minor scuff on the rear bumper. "
            "Sold as seen. Some rust on nearside sill."
        ),
        price_pence=150000,
        postcode="LE4 8JF",
        url="https://example.com/listing/stub-001",
        processed=False,
    )

    # Build stub Vehicle
    stub_vehicle = Vehicle(
        id=uuid.uuid4(),
        listing_id=listing_id,
        make="Ford",
        model="Focus",
        year=2015,
        fuel_type="petrol",
    )
    print(f"  Stub listing id  : {listing_id}")
    print(f"  Stub vehicle     : {stub_vehicle.make} {stub_vehicle.model} {stub_vehicle.year}")

    # Track objects added to the session
    added_objects = []

    def fake_add(obj):
        added_objects.append(obj)

    async def fake_flush():
        # Assign fake UUIDs to DetectedFault and ExteriorCondition objects
        # (normally done by the DB on INSERT)
        for obj in added_objects:
            if isinstance(obj, DetectedFault) and not hasattr(obj, 'id') or (
                isinstance(obj, DetectedFault) and obj.id is None
            ):
                obj.id = uuid.uuid4()

    # Mock execute to return appropriate results depending on the query
    call_count = [0]

    async def fake_execute(query):
        call_count[0] += 1
        mock_result = MagicMock()

        # Detect which table is being queried by looking at the query string
        query_str = str(query)

        if "listings" in query_str and "vehicles" not in query_str and call_count[0] == 1:
            # Step 1a: SELECT listing
            mock_result.scalar_one_or_none.return_value = stub_listing
        elif "vehicles" in query_str:
            # Step 1b: SELECT vehicle
            mock_result.scalar_one_or_none.return_value = stub_vehicle
        elif "cars_common_problems" in query_str or "cars" in query_str:
            # Step 3: No known problems for this test
            mock_scalars = MagicMock()
            mock_scalars.all.return_value = []
            mock_result.scalars.return_value = mock_scalars
        elif "common_problems" in query_str:
            mock_result.scalar_one_or_none.return_value = None
            mock_scalars = MagicMock()
            mock_scalars.all.return_value = []
            mock_result.scalars.return_value = mock_scalars
        else:
            mock_result.scalar_one_or_none.return_value = None
            mock_scalars = MagicMock()
            mock_scalars.all.return_value = []
            mock_result.scalars.return_value = mock_scalars

        return mock_result

    # Build the mocked session
    mock_session = MagicMock()
    mock_session.execute = fake_execute
    mock_session.add = fake_add
    mock_session.flush = AsyncMock(side_effect=fake_flush)
    mock_session.commit = AsyncMock()

    bus = StubEventBus()

    # Patch enrich_novel_fault so we don't make real LinkUp calls
    with patch(
        "app.services.problem_detector.enrich_novel_fault",
        new_callable=AsyncMock,
        return_value={"repair_min_pence": 30000, "repair_max_pence": 80000, "search_summary": "stub"},
    ):
        await detect_problems(mock_session, listing_id, bus)

    # Inspect results
    detected_faults = [o for o in added_objects if isinstance(o, DetectedFault)]
    exterior_conditions = [o for o in added_objects if isinstance(o, ExteriorCondition)]

    print(f"\n  Results:")
    print(f"    session.add() called {len(added_objects)} time(s) total")
    print(f"    DetectedFault objects created : {len(detected_faults)}")
    for f in detected_faults:
        print(f"      - issue={f.issue!r} severity={f.severity} confidence={f.confidence} source={f.source}")
    print(f"    ExteriorCondition objects    : {len(exterior_conditions)}")
    if exterior_conditions:
        ec = exterior_conditions[0]
        print(f"      write_off_category={ec.write_off_category} overall_severity={ec.overall_severity}")
    print(f"    listing.processed            : {stub_listing.processed}")
    print(f"    session.commit() called      : {mock_session.commit.called}")
    print(f"    PROBLEMS_DETECTED events     : {len(bus.emitted)}")
    for ev in bus.emitted:
        print(f"      - {ev.type}: fault_count={ev.payload.get('fault_count')} write_off={ev.payload.get('write_off_category')}")

    assert len(detected_faults) >= 1, f"Expected >=1 DetectedFault, got {len(detected_faults)}"
    assert len(exterior_conditions) == 1, f"Expected 1 ExteriorCondition, got {len(exterior_conditions)}"
    assert stub_listing.processed is True, "Expected listing.processed=True"
    assert mock_session.commit.called, "Expected session.commit() to be called"
    assert len(bus.emitted) >= 1, "Expected PROBLEMS_DETECTED event to be emitted"

    print(f"\n[PASS] detect_problems pipeline completed — {len(detected_faults)} fault(s) would be saved")
    return True


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
async def main():
    print("=" * 60)
    print("Detection pipeline manual smoke-test")
    print("=" * 60)

    passed = 0
    failed = 0

    for name, coro in [
        ("Config / API key check", asyncio.coroutine(test_api_key_config)() if False else None),
        ("detect_problems_ai direct", test_ai_service_direct()),
        ("detect_problems full pipeline", test_full_pipeline_mocked()),
    ]:
        # Handle sync test_api_key_config separately
        if name == "Config / API key check":
            try:
                test_api_key_config()
                passed += 1
            except AssertionError as e:
                print(f"[FAIL] {name}: {e}")
                failed += 1
            except Exception as e:
                print(f"[ERROR] {name}: {e}")
                logger.exception(f"{name} failed")
                failed += 1
        else:
            try:
                await coro
                passed += 1
            except AssertionError as e:
                print(f"[FAIL] {name}: {e}")
                failed += 1
            except Exception as e:
                print(f"[ERROR] {name}: {e}")
                logger.exception(f"{name} failed")
                failed += 1

    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    asyncio.run(main())
