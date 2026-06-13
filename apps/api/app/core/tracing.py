import functools

import sentry_sdk


def traced(op: str, name: str | None = None):
    """Wrap an async function in a Sentry span."""
    def decorator(func):
        span_name = name or func.__name__

        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            with sentry_sdk.start_span(op=op, name=span_name):
                return await func(*args, **kwargs)

        return wrapper
    return decorator
