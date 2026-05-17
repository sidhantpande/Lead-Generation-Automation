from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    before_sleep_log,
    retry_if_exception_type
)
from backend.utils.logger import logger

def api_retry_decorator(api_name: str):
    """
    Returns a tenancy retry decorator configured for third-party APIs.
    It will retry 3 times with exponential backoff (1s -> 2s -> 4s) and log before retrying.
    """
    return retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=4),
        before_sleep=before_sleep_log(logger, "WARNING"),
        reraise=True
    )
