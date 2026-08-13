from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ReconciliationDiscrepancyRead(BaseModel):
    id: str
    job_id: str
    wallet_id: str
    expected_balance: int
    actual_balance: int
    difference: int

    model_config = ConfigDict(from_attributes=True)


class ReconciliationJobRead(BaseModel):
    id: str
    status: str
    total_wallets_checked: int
    discrepancies_found: int
    started_at: datetime
    completed_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)
