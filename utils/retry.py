import logging
import time
import functools
from typing import Callable, Type, Tuple, Any

logger = logging.getLogger(__name__)

def retry(max_attempts: int = 3, delay: float = 2.0, exceptions: Tuple[Type[BaseException], ...] = (Exception,)):
    """
    A decorator that retries a function call a specified number of times.
    
    Args:
        max_attempts: Maximum number of attempts (including the first try)
        delay: Delay between attempts in seconds
        exceptions: Tuple of exception types to catch and retry on
    
    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_attempts:
                        logger.warning(f"Attempt {attempt} failed for {func.__name__}: {e}. Retrying in {delay}s...")
                        time.sleep(delay)
                    else:
                        logger.error(f"All {max_attempts} attempts failed for {func.__name__}: {e}")
            # If we got here, all attempts failed
            raise last_exception
        return wrapper
    return decorator