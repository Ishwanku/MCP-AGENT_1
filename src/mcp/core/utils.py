import functools
import logging
from typing import Callable, Any, Optional
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type, retry_if_result

logger = logging.getLogger(__name__)

def retry_llm_call(
    max_attempts: int = 3,
    initial_wait: float = 1.0,
    max_wait: float = 10.0,
    exceptions: tuple = (Exception,),
    result_predicate: Optional[Callable[[Any], bool]] = None,
    log_context: Optional[str] = None
):
    """
    Decorator for retrying LLM-related calls (HTTP or API) with exponential backoff.

    Args:
        max_attempts (int): Maximum number of retry attempts.
        initial_wait (float): Initial wait time in seconds.
        max_wait (float): Maximum wait time in seconds.
        exceptions (tuple): Exceptions to catch and retry.
        result_predicate (Callable[[Any], bool], optional): Function to check if result warrants a retry.
        log_context (str, optional): Context for logging (e.g., 'chunk 1 of doc.docx').

    Returns:
        Callable: Decorated function with retry logic.
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        @retry(
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential(multiplier=initial_wait, max=max_wait),
            retry=(retry_if_exception_type(exceptions) | retry_if_result(result_predicate)) if result_predicate else retry_if_exception_type(exceptions),
            before_sleep=lambda retry_state: logger.info(
                f"Retrying {func.__name__} after {'exception' if retry_state.outcome.failed else 'invalid result'}. "
                f"Attempt {retry_state.attempt_number} of {max_attempts}. "
                f"Waiting {retry_state.next_action.sleep} seconds... "
                f"Context: {log_context or 'none'}"
            )
        )
        async def wrapper(*args, **kwargs) -> Any:
            try:
                result = await func(*args, **kwargs)
                if result_predicate and result_predicate(result):
                    logger.warning(f"Invalid result in {func.__name__}: {result}. Context: {log_context or 'none'}")
                    raise ValueError(f"Invalid result: {result}")
                return result
            except exceptions as e:
                logger.error(f"Error in {func.__name__}: {str(e)}. Context: {log_context or 'none'}")
                raise
        return wrapper
    return decorator