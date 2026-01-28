import time
from functools import wraps
from typing import Callable, Type, Tuple


def retry_on_exception(
    exceptions: Tuple[Type[BaseException], ...] = (Exception,),
    max_attempts: int = 3,
    delay: float = 0.1,
) -> Callable:
    """Simple retry decorator for transient operations.

    Use for dev only; production should use robust retry libraries and jittered backoff.
    """

    def deco(func: Callable):
        @wraps(func)
        def wrapped(*args, **kwargs):
            attempts = 0
            while True:
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    attempts += 1
                    if attempts >= max_attempts:
                        raise
                    time.sleep(delay)

        return wrapped

    return deco
