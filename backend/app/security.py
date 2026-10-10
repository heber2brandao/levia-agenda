import hashlib
import hmac

from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from starlette.concurrency import run_in_threadpool
from app.timing import measure


def consume_limit(engine, secret: str, identity: str, limit: int) -> bool:
    key = hmac.new(secret.encode(), identity.encode(), hashlib.sha256).hexdigest()
    # The counter and cleanup are ONE atomic PostgreSQL statement. Autocommit
    # avoids separate BEGIN/COMMIT round trips and releases its row lock sooner.
    # SQLAlchemy restores the normal isolation mode when returning to the pool.
    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
        count = connection.scalar(
            text("""
            WITH cleanup AS (
              DELETE FROM levia.rate_limits WHERE key IN (
                SELECT key FROM levia.rate_limits
                WHERE key <> :key
                  AND bucket < floor(extract(epoch FROM clock_timestamp()) / 60) - 60
                LIMIT 100 FOR UPDATE SKIP LOCKED
              )
            )
            INSERT INTO levia.rate_limits AS r (key, bucket, count)
            VALUES (:key, floor(extract(epoch FROM clock_timestamp()) / 60)::bigint, 1)
            ON CONFLICT (key) DO UPDATE SET
              count = CASE WHEN r.bucket = EXCLUDED.bucket THEN LEAST(r.count + 1, :cap) ELSE 1 END,
              bucket = EXCLUDED.bucket
            RETURNING count
        """),
            {"key": key, "cap": limit + 1},
        )
    return count <= limit


class SecurityMiddleware:
    """Bound bodies before parsing, shared IP quota before signature/JWKS work."""

    def __init__(self, app, state, settings):
        self.app, self.state, self.settings = app, state, settings

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        async def secured_send(message):
            if message["type"] == "http.response.start":
                message.setdefault("headers", []).extend(
                    [
                        (b"x-content-type-options", b"nosniff"),
                        (b"cache-control", b"no-store"),
                        (b"referrer-policy", b"no-referrer"),
                    ]
                )
            await send(message)

        if (
            scope["path"].startswith(("/api/v1/me", "/api/v1/public"))
            and scope["method"] != "OPTIONS"
        ):
            if self.state.engine is not None:
                try:
                    with measure("ip_limit"):
                        allowed = await run_in_threadpool(
                            consume_limit,
                            self.state.engine,
                            self.settings.rate_limit_secret.get_secret_value(),
                            "ip:" + (scope.get("client") or ("unknown",))[0],
                            self.settings.rate_limit_per_minute,
                        )
                except SQLAlchemyError:
                    return await JSONResponse(
                        {"detail": "Serviço temporariamente indisponível"}, 503
                    )(scope, receive, secured_send)
                if not allowed:
                    return await JSONResponse(
                        {"detail": "Muitas tentativas. Aguarde um minuto."},
                        429,
                        headers={"Retry-After": "60"},
                    )(scope, receive, secured_send)
            body = bytearray()
            max_body = (
                2 * 1024 * 1024
                if scope["path"] == "/api/v1/me/logo" and scope["method"] == "PUT"
                else 32768
            )
            while True:
                event = await receive()
                if event["type"] == "http.disconnect":
                    return
                body.extend(event.get("body", b""))
                if len(body) > max_body:
                    return await JSONResponse({"detail": "Requisição muito grande"}, 413)(
                        scope, receive, secured_send
                    )
                if not event.get("more_body"):
                    break
            delivered = False

            async def bounded_receive():
                nonlocal delivered
                if not delivered:
                    delivered = True
                    return {"type": "http.request", "body": bytes(body), "more_body": False}
                return await receive()

            return await self.app(scope, bounded_receive, secured_send)
        await self.app(scope, receive, secured_send)
