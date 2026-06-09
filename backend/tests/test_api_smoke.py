"""API 集成冒烟（AC-01/AC-02，无需 LLM）"""
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from main import app


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_ac01_health(client):
    r = await client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body.get("success") is True
    assert body.get("data", {}).get("status") == "ok"


@pytest.mark.asyncio
async def test_ac02_unauthorized_stations(client):
    r = await client.get("/api/v1/stations", headers={"Authorization": "Bearer invalid-token"})
    assert r.status_code == 401
    body = r.json()
    assert body.get("success") is False
    assert body.get("error", {}).get("code")


@pytest.mark.asyncio
async def test_register_login_me(client):
    username = "pytest_user_smoke"
    reg = await client.post("/api/v1/auth/register", json={"username": username, "password": "pass12345"})
    if reg.status_code == 409:
        login = await client.post("/api/v1/auth/login", json={"username": username, "password": "pass12345"})
    else:
        assert reg.status_code == 200
        login = reg
    body = login.json()
    data = body.get("data") if isinstance(body, dict) and "data" in body else body
    token = data.get("access_token")
    assert token
    me = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
