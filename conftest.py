import asyncio
import os
import uuid

import httpx
import pytest


@pytest.fixture
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def client():
    base_url = os.getenv("API_BASE_URL")
    if base_url:
        async with httpx.AsyncClient(base_url=base_url, timeout=10) as c:
            yield c
    else:
        from app import app
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
            yield c


@pytest.fixture
def user_data():
    suffix = uuid.uuid4().hex[:8]
    return {
        "username": f"user_{suffix}",
        "password": "Str0ng-Pass!",
        "email": f"user_{suffix}@example.com",
        "name": "Test User",
    }


@pytest.fixture
async def registered_user(client, user_data):
    """Зарегистрированный пользователь + токен доступа."""
    r = await client.post("/api/register", json=user_data)
    assert r.status_code == 201, r.text
    return {**user_data, "token": r.json()["access_token"]}


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}
