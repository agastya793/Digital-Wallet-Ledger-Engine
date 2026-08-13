from collections.abc import Sequence

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.dependencies import get_db
from app.reconciliation.schemas import (
    ReconciliationDiscrepancyRead,
    ReconciliationJobRead,
)
from app.reconciliation.service import ReconciliationService

router = APIRouter(prefix="/reconciliation", tags=["Reconciliation"])


@router.post("/run", response_model=ReconciliationJobRead)
async def run_reconciliation_job(
    background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)
):
    """
    Manually triggers the reconciliation engine.
    For MVP, we wait for it to finish and return the result.
    In a high-scale production system, this could be dispatched as a background task.
    """
    # For MVP we just await it directly so the user gets instant feedback
    job = await ReconciliationService.run_reconciliation_job(db)
    return job


@router.get("/jobs", response_model=list[ReconciliationJobRead])
async def list_reconciliation_jobs(
    limit: int = 20, db: AsyncSession = Depends(get_db)
):
    """
    List past reconciliation runs.
    """
    return await ReconciliationService.get_jobs(db, limit)


@router.get(
    "/jobs/{job_id}/discrepancies", response_model=list[ReconciliationDiscrepancyRead]
)
async def list_job_discrepancies(
    job_id: str, db: AsyncSession = Depends(get_db)
):
    """
    List any balance discrepancies found during a specific job.
    """
    return await ReconciliationService.get_job_discrepancies(db, job_id)
