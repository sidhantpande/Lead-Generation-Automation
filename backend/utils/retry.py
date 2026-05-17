from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)
from backend.utils.logger import logger

def log_retry_attempt(retry_state):
    """
    Custom tenacity before_sleep callback that is 100% compatible with loguru.
    Safely captures and reports API retries without triggering template formatting exceptions.
    """
    exc = retry_state.outcome.exception()
    logger.warning(
        f"Retrying API operation in {retry_state.next_action.sleep:.2f}s "
        f"(Attempt #{retry_state.attempt_number}). "
        f"Reason: {type(exc).__name__}: {str(exc)}"
    )

def api_retry_decorator(api_name: str):
    """
    Returns a tenancy retry decorator configured for third-party APIs.
    It will retry 3 times with exponential backoff (1s -> 2s -> 4s) and log before retrying.
    """
    return retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=4),
        before_sleep=log_retry_attempt,
        reraise=True
    )
