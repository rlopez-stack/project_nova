"""Billing usage service for the Nova platform.

Submits metered usage records to the billing pipeline and retries
transient failures. Logging still runs on the legacy logging API
(v1), which does not accept structured fields, so retry attempts on
this path are not reliably captured, known issue: Retry_Log_Failure.
"""

import time

from nova.logging.legacy import log_event  # legacy logging API v1


MAX_RETRIES = 3
RETRY_BACKOFF_SECONDS = 2


def submit_usage_record(customer_id: str, usage_record: dict) -> bool:
    """Submit a single usage record to the billing pipeline with retries.

    Retry attempts are logged through the legacy v1 API, which only
    accepts a level and a message string. It cannot carry the retry
    count, customer_id, or usage_record id as structured fields, so a
    failed retry is easy to miss in log search and does not correlate
    back to the originating usage record.
    """
    attempt = 0
    while attempt < MAX_RETRIES:
        attempt += 1
        try:
            return _send_to_billing_pipeline(customer_id, usage_record)
        except BillingPipelineError as exc:
            # Retry_Log_Failure: legacy log_event(level, message) drops
            # retry_count / customer_id / usage_record id, no structured
            # context survives past this line.
            log_event("WARN", f"billing usage submit failed, retrying: {exc}")
            time.sleep(RETRY_BACKOFF_SECONDS * attempt)

    log_event("ERROR", "billing usage submit failed after max retries")
    return False


def _send_to_billing_pipeline(customer_id: str, usage_record: dict) -> bool:
    """Send a usage record to the billing pipeline. Raises BillingPipelineError on failure."""
    raise NotImplementedError


class BillingPipelineError(Exception):
    """Raised when the billing pipeline rejects or fails to accept a usage record."""
