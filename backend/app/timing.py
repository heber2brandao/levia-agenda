"""Request-local durations only: never record SQL, parameters or user identifiers."""
from contextlib import contextmanager
from contextvars import ContextVar
from time import perf_counter

from sqlalchemy import event

_metrics: ContextVar[dict[str, float] | None] = ContextVar("request_timings", default=None)


@contextmanager
def measure(name: str):
    metrics = _metrics.get()
    start = perf_counter()
    try:
        yield
    finally:
        if metrics is not None:
            metrics[name] = metrics.get(name, 0.0) + (perf_counter() - start) * 1000


def instrument_engine(engine):
    @event.listens_for(engine, "before_cursor_execute")
    def before(conn, cursor, statement, parameters, context, executemany):
        context._levia_timing = (_metrics.get(), perf_counter())

    def finish(context):
        timing = getattr(context, "_levia_timing", None)
        if timing is None:
            return
        context._levia_timing = None
        metrics, started = timing
        if metrics is not None:
            metrics["sql"] = metrics.get("sql", 0.0) + (perf_counter() - started) * 1000

    @event.listens_for(engine, "after_cursor_execute")
    def after(conn, cursor, statement, parameters, context, executemany):
        finish(context)

    @event.listens_for(engine, "handle_error")
    def failed(context):
        finish(context.execution_context)


class TimingMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        metrics: dict[str, float] = {}
        token = _metrics.set(metrics)
        started = perf_counter()

        async def timed_send(message):
            if message["type"] == "http.response.start":
                metrics["app"] = (perf_counter() - started) * 1000
                # Fixed internal names and numeric values, no request content.
                header = ", ".join(f"{name};dur={value:.2f}" for name, value in sorted(metrics.items()))
                message.setdefault("headers", []).append((b"server-timing", header.encode("ascii")))
            await send(message)

        try:
            await self.app(scope, receive, timed_send)
        finally:
            _metrics.reset(token)
