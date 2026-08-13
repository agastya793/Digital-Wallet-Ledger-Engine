import logging
from collections.abc import Sequence

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ledger.models import LedgerEntry
from app.reconciliation.models import ReconciliationDiscrepancy, ReconciliationJob
from app.wallet.models import Wallet

logger = logging.getLogger(__name__)


class ReconciliationService:
    @staticmethod
    async def run_reconciliation_job(db: AsyncSession) -> ReconciliationJob:
        """
        Runs the reconciliation engine to verify wallet balances against ledger entries.
        """
        # Create a new job record
        job = ReconciliationJob(status="running")
        db.add(job)
        await db.commit()
        await db.refresh(job)

        try:
            # Step 1: Calculate the expected balance for every wallet from the LedgerEntry table
            # expected_balance = SUM(credit amounts) - SUM(debit amounts)
            ledger_balances_query = select(
                LedgerEntry.wallet_id,
                func.sum(
                    case(
                        (LedgerEntry.entry_type == "credit", LedgerEntry.amount),
                        (LedgerEntry.entry_type == "debit", -LedgerEntry.amount),
                        else_=0,
                    )
                ).label("expected_balance"),
            ).group_by(LedgerEntry.wallet_id)

            ledger_balances_result = await db.execute(ledger_balances_query)
            ledger_balances = {
                row.wallet_id: row.expected_balance for row in ledger_balances_result
            }

            # Step 2: Fetch all wallets to check their stored balances
            wallets_query = select(Wallet.id, Wallet.balance)
            wallets_result = await db.execute(wallets_query)
            wallets = wallets_result.all()

            discrepancies = []
            total_checked = len(wallets)

            # Step 3: Compare expected vs actual
            for wallet in wallets:
                expected = ledger_balances.get(wallet.id, 0)
                actual = wallet.balance

                if expected != actual:
                    discrepancies.append(
                        ReconciliationDiscrepancy(
                            job_id=job.id,
                            wallet_id=wallet.id,
                            expected_balance=expected,
                            actual_balance=actual,
                            difference=actual - expected,
                        )
                    )

            # Step 4: Record discrepancies and finalize job
            if discrepancies:
                db.add_all(discrepancies)

            job.total_wallets_checked = total_checked
            job.discrepancies_found = len(discrepancies)
            job.status = "completed"
            job.completed_at = func.now()

            await db.commit()
            await db.refresh(job)

            logger.info(
                f"Reconciliation job {job.id} completed. Checked {total_checked} wallets, found {len(discrepancies)} discrepancies."
            )
            return job

        except Exception as e:
            await db.rollback()
            logger.error(f"Reconciliation job {job.id} failed: {e}")

            # Mark job as failed
            job.status = "failed"
            job.completed_at = func.now()
            db.add(job)
            await db.commit()
            raise

    @staticmethod
    async def get_jobs(
        db: AsyncSession, limit: int = 20
    ) -> Sequence[ReconciliationJob]:
        query = (
            select(ReconciliationJob)
            .order_by(ReconciliationJob.started_at.desc())
            .limit(limit)
        )
        result = await db.execute(query)
        return result.scalars().all()

    @staticmethod
    async def get_job_discrepancies(
        db: AsyncSession, job_id: str
    ) -> Sequence[ReconciliationDiscrepancy]:
        query = select(ReconciliationDiscrepancy).where(
            ReconciliationDiscrepancy.job_id == job_id
        )
        result = await db.execute(query)
        return result.scalars().all()
