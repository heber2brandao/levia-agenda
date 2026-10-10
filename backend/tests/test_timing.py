import asyncio
import re

import httpx
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool

from app.timing import TimingMiddleware, instrument_engine, measure


def test_sync_thread_sql_timings_contain_no_request_or_query_values():
    engine = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    instrument_engine(engine)
    app = FastAPI()
    app.add_middleware(TimingMiddleware)

    @app.get("/")
    def endpoint():
        with measure("db_connect"):
            connection = engine.connect()
        with connection:
            connection.execute(text("SELECT :secret"), {"secret": "private-value"})
        return {"ok": True}

    with TestClient(app) as client:
        response = client.get("/?private=value", headers={"Authorization": "Bearer private-token"})
    header = response.headers["server-timing"]
    assert re.fullmatch(r"app;dur=\d+\.\d+, db_connect;dur=\d+\.\d+, sql;dur=\d+\.\d+", header)
    assert "private" not in header
    engine.dispose()


def test_concurrent_requests_do_not_share_timing_state():
    app = FastAPI()
    app.add_middleware(TimingMiddleware)

    @app.get("/{kind}")
    async def endpoint(kind: str):
        with measure("auth" if kind == "first" else "user_limit"):
            await asyncio.sleep(0.01)
        return {"ok": True}

    async def run():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            return await asyncio.gather(client.get("/first"), client.get("/second"))

    first, second = asyncio.run(run())
    assert "auth;dur=" in first.headers["server-timing"]
    assert "user_limit" not in first.headers["server-timing"]
    assert "user_limit;dur=" in second.headers["server-timing"]
    assert "auth" not in second.headers["server-timing"]
