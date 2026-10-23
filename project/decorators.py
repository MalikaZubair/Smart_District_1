import functools
import inspect
import time

from exceptions import PortalError
from logger_setup import get_logger

logger = get_logger()


def timed(func):
    """Function کا execution time log کرتا ہے۔"""
    if inspect.iscoroutinefunction(func):
        @functools.wraps(func)
        async def awrapper(*args, **kwargs):
            start = time.perf_counter()
            try:
                return await func(*args, **kwargs)
            finally:
                logger.info("%s took %.3fs", func.__qualname__,
                            time.perf_counter() - start)
        return awrapper

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        try:
            return func(*args, **kwargs)
        finally:
            logger.info("%s took %.3fs", func.__qualname__,
                        time.perf_counter() - start)
    return wrapper


def _handle(func, exc: Exception) -> None:
    if isinstance(exc, PortalError):
        logger.error("%s | %s | context=%s",
                     func.__qualname__, exc.message, exc.context)
        print(f"[ERROR] {exc.message}")
    else:
        logger.exception("Unexpected error in %s", func.__qualname__)
        print("[ERROR] Unexpected error. See logs/portal.log")


def log_errors(func):
    """Exceptions کو log کرتا ہے اور user کو صاف message دکھاتا ہے۔"""
    if inspect.iscoroutinefunction(func):
        @functools.wraps(func)
        async def awrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as exc:
                _handle(func, exc)
        return awrapper

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as exc:
            _handle(func, exc)
    return wrapper