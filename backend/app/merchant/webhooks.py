"""
Webhook delivery — fire-and-forget merchant notifications.

When a checkout session is paid, the merchant's webhook URL
receives a POST with the payment details. This runs as a
FastAPI BackgroundTask so the customer's payment response
returns immediately — they don't wait for the webhook to complete.

Delivery semantics:
- Fire-and-forget: we attempt delivery once.
- If the webhook fails, the payment is NOT reversed.
  (The merchant can query the API to check session status.)
- Future enhancement: retry queue with exponential backoff.

Payload sent to webhook URL:
    {
        "event": "checkout.paid",
        "session_id": "...",
        "amount": 5000,
        "currency": "USD",
        "paid_by_user_id": "...",
        "paid_at": "2026-08-10T12:00:00Z",
        "transaction_id": "..."
    }
"""

import httpx
import structlog

logger = structlog.get_logger()


async def send_payment_webhook(
    webhook_url: str,
    session_id: str,
    amount: int,
    currency: str,
    paid_by_user_id: str,
    paid_at: str,
    transaction_id: str,
) -> None:
    """
    POST payment notification to the merchant's webhook URL.

    This is called as a BackgroundTask — it runs after the
    response is sent to the customer.

    Timeout: 10 seconds. We don't want a slow merchant server
    to tie up our worker threads.
    """
    payload = {
        "event": "checkout.paid",
        "session_id": session_id,
        "amount": amount,
        "currency": currency,
        "paid_by_user_id": paid_by_user_id,
        "paid_at": paid_at,
        "transaction_id": transaction_id,
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(webhook_url, json=payload)
            logger.info(
                "webhook_delivered",
                url=webhook_url,
                session_id=session_id,
                status_code=response.status_code,
            )
    except httpx.HTTPError as e:
        # Log the failure but don't raise — the payment already succeeded.
        # The merchant can poll the API to check session status.
        logger.warning(
            "webhook_delivery_failed",
            url=webhook_url,
            session_id=session_id,
            error=str(e),
        )
    except Exception as e:
        logger.error(
            "webhook_unexpected_error",
            url=webhook_url,
            session_id=session_id,
            error=str(e),
        )
