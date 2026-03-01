"""
refresh.py

POST /refresh  — trigger manual ingestion cycle
GET /refresh/{job_id}  — check job status
"""
import logging
import uuid
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from app.api.deps import get_bus
from app.api.schemas import RefreshResponse, RefreshStatusResponse
from app.events.bus import EventBus

logger = logging.getLogger(__name__)

router = APIRouter()

# In-memory job store — fine for single-process personal use
_jobs: dict[str, dict] = {}


async def _run_ingestion(job_id: str, bus: EventBus) -> None:
    _jobs[job_id]["status"] = "running"
    _jobs[job_id]["started_at"] = datetime.utcnow().isoformat()
    try:
        from app.workers.ingestion_worker import run_once
        result = await run_once(bus)
        _jobs[job_id]["status"] = "complete"
        _jobs[job_id]["listings_found"] = result.get("listings_found", 0)
        _jobs[job_id]["completed_at"] = datetime.utcnow().isoformat()
    except Exception as e:
        logger.error("Manual refresh job %s failed: %s", job_id, e, exc_info=True)
        _jobs[job_id]["status"] = "failed"
        _jobs[job_id]["error"] = str(e)


@router.post("/refresh", response_model=RefreshResponse)
async def trigger_refresh(
    background_tasks: BackgroundTasks,
    bus: EventBus = Depends(get_bus),
) -> RefreshResponse:
    """Trigger a manual ingestion cycle. Returns a job_id to poll for status."""
    job_id = str(uuid.uuid4())
    _jobs[job_id] = {
        "status": "pending",
        "started_at": None,
        "completed_at": None,
        "listings_found": None,
        "error": None,
    }
    background_tasks.add_task(_run_ingestion, job_id, bus)
    return RefreshResponse(job_id=job_id, status="pending")


@router.get("/refresh/{job_id}", response_model=RefreshStatusResponse)
async def get_refresh_status(job_id: str) -> RefreshStatusResponse:
    """Return the status of a previously triggered refresh job."""
    job = _jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return RefreshStatusResponse(
        job_id=job_id,
        status=job["status"],
        started_at=job.get("started_at"),
        completed_at=job.get("completed_at"),
        listings_found=job.get("listings_found"),
        error=job.get("error"),
    )
