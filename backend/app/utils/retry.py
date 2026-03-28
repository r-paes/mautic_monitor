"""
retry.py — Decorator de retry para chamadas externas (APIs, SSH).
Usa tenacity para retry com backoff exponencial.
"""

import functools
import logging

from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
    before_sleep_log,
)

from app.config import settings

logger = logging.getLogger(__name__)


def with_retry(
    attempts: int | None = None,
    delay: int | None = None,
    exceptions: tuple = (Exception,),
):
    """
    Decorator de retry configurável.
    Valores padrão lidos de settings (nunca hardcoded).

    Uso:
        @with_retry()
        async def my_api_call():
            ...

        @with_retry(attempts=5, exceptions=(httpx.HTTPError,))
        async def my_api_call():
            ...
    """
    max_attempts = attempts or settings.external_request_retry_attempts
    base_delay = delay or settings.external_request_retry_delay_seconds

    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            retryer = retry(
                stop=stop_after_attempt(max_attempts),
                wait=wait_exponential(multiplier=base_delay, min=base_delay, max=30),
                retry=retry_if_exception_type(exceptions),
                before_sleep=before_sleep_log(logger, logging.WARNING),
                reraise=True,
            )
            return await retryer(func)(*args, **kwargs)

        return wrapper

    return decorator
