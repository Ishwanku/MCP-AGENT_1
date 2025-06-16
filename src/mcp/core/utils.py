import functools
import time
import logging
from typing import Callable, Any, Optional
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logger = logging.getLogger(__name__)

def retry_llm_call(
    max_attempts: int = 3,
    initial_wait: float = 1.0,
    max_wait: float = 10.0,
    exceptions: tuple = (Exception,)
):
    """
    Decorator for retrying LLM API calls with exponential backoff.
    
    Args:
        max_attempts (int): Maximum number of retry attempts
        initial_wait (float): Initial wait time in seconds
        max_wait (float): Maximum wait time in seconds
        exceptions (tuple): Tuple of exceptions to catch and retry
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        @retry(
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential(multiplier=initial_wait, max=max_wait),
            retry=retry_if_exception_type(exceptions),
            before_sleep=lambda retry_state: logger.info(
                f"Retrying {func.__name__} after error. "
                f"Attempt {retry_state.attempt_number} of {max_attempts}. "
                f"Waiting {retry_state.next_action.sleep} seconds..."
            )
        )
        async def wrapper(*args, **kwargs) -> Any:
            try:
                return await func(*args, **kwargs)
            except exceptions as e:
                logger.error(f"Error in {func.__name__}: {str(e)}")
                raise
        return wrapper
    return decorator 