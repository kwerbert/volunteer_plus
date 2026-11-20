import os
import sys
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.event_service.api.deps import get_current_user_id
from app.services.event_service.db.models import Base
from app.services.event_service.db.session import get_db_session
from app.services.event_service.main import app

TEST_DATABASE_URL = "sqlite+aiosqlite:///./test_volunteer_plus.db"
test_engine = create_async_engine(TEST_DATABASE_URL, echo=False, future=True)
session_factory = async_sessionmaker(
    test_engine, class_=AsyncSession, expire_on_commit=False
)

ORGANIZER_ID = 2


@pytest.fixture(scope="function")
async def test_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with session_factory() as session:
        yield session
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture(scope="function")
def org_mock():
    """По умолчанию текущий пользователь — организатор организации."""
    with patch(
        "app.services.event_service.service.OrganizationServiceClient.is_organizer",
        new=AsyncMock(return_value=True),
    ) as m:
        yield m


@pytest.fixture(scope="function")
async def client(test_db, org_mock):
    async def override_get_db():
        yield test_db

    app.dependency_overrides[get_db_session] = override_get_db
    app.dependency_overrides[get_current_user_id] = lambda: ORGANIZER_ID
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


def _payload(**kw):
    future = datetime.now(timezone.utc) + timedelta(days=1)
    base = {
        "org_id": 1,
        "title": "Test Event",
        "start_date": future.isoformat(),
        "end_date": (future + timedelta(hours=2)).isoformat(),
        "max_participants": 50,
    }
    base.update(kw)
    return base


async def _create(client, **kw):
    resp = await client.post("/api/v1/events", json=_payload(**kw))
    assert resp.status_code == 200, resp.text
    return resp.json()


@pytest.mark.asyncio
async def test_create_event_default_role(client):
    data = await _create(client)
    assert data["has_custom_roles"] is False
    assert len(data["roles"]) == 1
    assert data["roles"][0]["name"] == "Участник"
    assert data["roles"][0]["hours_value"] == 4.0
    assert data["status"] == "active"
    assert data["qr_check_enabled"] is True


@pytest.mark.asyncio
async def test_create_event_custom_roles(client):
    data = await _create(
        client,
        roles=[
            {"name": "Уборка", "hours_value": 4.0, "max_participants": 2},
            {"name": "Координация", "hours_value": 6.0},
        ],
        image_url="http://img/x.png",
        qr_check_enabled=False,
    )
    assert data["has_custom_roles"] is True
    assert len(data["roles"]) == 2
    assert data["image_url"] == "http://img/x.png"
    assert data["qr_check_enabled"] is False


@pytest.mark.asyncio
async def test_create_event_past_date(client):
    past = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    resp = await client.post("/api/v1/events", json=_payload(start_date=past))
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_create_event_not_organizer_403(client, org_mock):
    org_mock.return_value = False
    resp = await client.post("/api/v1/events", json=_payload())
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_create_event_org_not_found_404(client, org_mock):
    org_mock.side_effect = HTTPException(
        status_code=404, detail="Организация не найдена"
    )
    resp = await client.post("/api/v1/events", json=_payload())
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_event_detail_roles_and_counts(client):
    data = await _create(client, roles=[{"name": "Уборка", "hours_value": 4.0}])
    role_id = data["roles"][0]["id"]
    await client.post(
        f"/api/v1/events/{data['id']}/register", json={"user_id": 1, "role_id": role_id}
    )
    detail = (await client.get(f"/api/v1/events/{data['id']}")).json()
    assert detail["roles"][0]["registered_count"] == 1


@pytest.mark.asyncio
async def test_register_default_without_role(client):
    data = await _create(client)
    resp = await client.post(
        f"/api/v1/events/{data['id']}/register", json={"user_id": 1}
    )
    assert resp.status_code == 200
    assert resp.json()["role_id"] == data["roles"][0]["id"]


@pytest.mark.asyncio
async def test_register_custom_without_role_422(client):
    data = await _create(client, roles=[{"name": "Уборка"}, {"name": "Посадка"}])
    resp = await client.post(
        f"/api/v1/events/{data['id']}/register", json={"user_id": 1}
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_register_role_not_belonging_422(client):
    data = await _create(client, roles=[{"name": "Уборка"}])
    resp = await client.post(
        f"/api/v1/events/{data['id']}/register", json={"user_id": 1, "role_id": 9999}
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_register_role_limit_409(client):
    data = await _create(client, roles=[{"name": "Уборка", "max_participants": 1}])
    role_id = data["roles"][0]["id"]
    ok = await client.post(
        f"/api/v1/events/{data['id']}/register", json={"user_id": 1, "role_id": role_id}
    )
    assert ok.status_code == 200
    full = await client.post(
        f"/api/v1/events/{data['id']}/register", json={"user_id": 2, "role_id": role_id}
    )
    assert full.status_code == 409
    assert "Уборка" in full.json()["detail"]


@pytest.mark.asyncio
async def test_register_duplicate_409(client):
    data = await _create(client)
    await client.post(f"/api/v1/events/{data['id']}/register", json={"user_id": 1})
    dup = await client.post(
        f"/api/v1/events/{data['id']}/register", json={"user_id": 1}
    )
    assert dup.status_code == 409


@pytest.mark.asyncio
async def test_update_event_not_organizer_403(client, org_mock):
    data = await _create(client)
    org_mock.return_value = False
    resp = await client.patch(
        f"/api/v1/events/{data['id']}", json={"title": "New Title"}
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_update_event_success(client):
    data = await _create(client)
    resp = await client.patch(
        f"/api/v1/events/{data['id']}", json={"title": "New Title"}
    )
    assert resp.status_code == 200
    assert resp.json()["title"] == "New Title"


@pytest.mark.asyncio
async def test_health_check(client):
    assert (await client.get("/health")).status_code == 200
