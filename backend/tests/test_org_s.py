"""
Тесты Organization Service (этап 2: организация ↔ организаторы).
"""

import os
import sys
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.organization_service.api.deps import get_current_user
from app.services.organization_service.db.models import (
    Base,
    Category,
    Organization,
    OrganizationOrganizer,
)
from app.services.organization_service.db.session import get_db_session
from app.services.organization_service.main import app
from app.services.organization_service.schemas import CurrentUser

TEST_DATABASE_URL = "sqlite+aiosqlite:///./test_org.db"
test_engine = create_async_engine(TEST_DATABASE_URL, echo=False, future=True)
session_factory = async_sessionmaker(
    test_engine, class_=AsyncSession, expire_on_commit=False
)

OWNER = CurrentUser(id=2, role="organizer")
OTHER_ORGANIZER = CurrentUser(id=5, role="organizer")
ADMIN = CurrentUser(id=3, role="volunteer", is_admin=True)
VOLUNTEER = CurrentUser(id=1, role="volunteer")


def login_as(user: CurrentUser) -> None:
    app.dependency_overrides[get_current_user] = lambda: user


def user_info(user_id: int, role: str = "organizer", is_active: bool = True) -> dict:
    """Ответ user_service /users/by-email/{email}."""
    return {
        "id": user_id,
        "email": f"u{user_id}@example.com",
        "role": role,
        "is_active": is_active,
        "is_admin": False,
    }


@pytest.fixture(scope="function")
async def test_db():
    async with test_engine.begin() as conn:
        await conn.execute(text("PRAGMA foreign_keys=ON"))
        await conn.run_sync(Base.metadata.create_all)
    async with session_factory() as session:
        yield session
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture(scope="function")
async def client(test_db):
    async def override_get_db():
        yield test_db

    app.dependency_overrides[get_db_session] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
async def test_category(test_db):
    category = Category(id=1, name="Test Category")
    test_db.add(category)
    await test_db.commit()
    return category


async def create_org(client, name: str = "Test Org") -> int:
    login_as(OWNER)
    resp = await client.post(
        "/api/v1/organizations", json={"name": name, "description": "Test"}
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


# === Создание ===


@pytest.mark.asyncio
async def test_create_organization(client, test_category):
    login_as(OWNER)
    response = await client.post(
        "/api/v1/organizations",
        json={
            "name": "Test Org",
            "description": "A test organization",
            "category_id": 1,
        },
    )
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["is_verified"] is False
    assert data["rating"] == 0.0
    assert data["owner_user_id"] == OWNER.id
    # Создатель записан владельцем в organization_organizers
    membership = (
        await client.get(f"/api/v1/organizations/{data['id']}/organizers")
    ).json()
    assert membership[0]["user_id"] == OWNER.id
    assert membership[0]["role_in_org"] == "owner"


@pytest.mark.asyncio
async def test_create_organization_forbidden_for_volunteer(client):
    login_as(VOLUNTEER)
    resp = await client.post("/api/v1/organizations", json={"name": "Volunteer Org"})
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_create_organization_unauthorized(client):
    # Без override get_current_user и без токена → 401 до похода в user_service
    resp = await client.post("/api/v1/organizations", json={"name": "Anon Org"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_create_second_organization_conflict(client):
    await create_org(client, "First Org")
    resp = await client.post("/api/v1/organizations", json={"name": "Second Org"})
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_unique_name_constraint(client):
    await create_org(client, "Unique Name")
    login_as(OTHER_ORGANIZER)  # другой организатор, чтобы не упереться в 409 владения
    resp = await client.post("/api/v1/organizations", json={"name": "Unique Name"})
    assert resp.status_code == 400
    assert "already exists" in resp.json()["detail"]


# === Публичное чтение ===


@pytest.mark.asyncio
async def test_search_organizations(client):
    await create_org(client, "Searchable Org")
    response = await client.get("/api/v1/organizations?verified=false")
    assert response.status_code == 200
    assert any(org["name"] == "Searchable Org" for org in response.json())


# === Верификация ===


@pytest.mark.asyncio
async def test_verify_organization_admin(client):
    org_id = await create_org(client, "Verify Me")
    login_as(ADMIN)
    resp = await client.patch(
        f"/api/v1/organizations/{org_id}/verify", json={"verified": True}
    )
    assert resp.status_code == 200
    assert resp.json()["is_verified"] is True
    assert resp.json()["rating"] > 0.0


@pytest.mark.asyncio
async def test_verify_organization_forbidden_for_non_admin(client):
    org_id = await create_org(client)
    login_as(OWNER)  # владелец, но не админ
    resp = await client.patch(
        f"/api/v1/organizations/{org_id}/verify", json={"verified": True}
    )
    assert resp.status_code == 403


# === Управление организаторами ===


@pytest.mark.asyncio
async def test_add_organizer_success(client):
    org_id = await create_org(client)
    with patch(
        "app.services.organization_service.service.get_user_by_email",
        new=AsyncMock(return_value=user_info(5)),
    ):
        resp = await client.post(
            f"/api/v1/organizations/{org_id}/organizers",
            json={"email": "u5@example.com"},
        )
    assert resp.status_code == 201, resp.text
    assert resp.json()["user_id"] == 5
    assert resp.json()["role_in_org"] == "organizer"
    assert resp.json()["added_by"] == OWNER.id


@pytest.mark.asyncio
async def test_add_organizer_volunteer_rejected_422(client):
    org_id = await create_org(client)
    with patch(
        "app.services.organization_service.service.get_user_by_email",
        new=AsyncMock(return_value=user_info(1, role="volunteer")),
    ):
        resp = await client.post(
            f"/api/v1/organizations/{org_id}/organizers",
            json={"email": "u1@example.com"},
        )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_add_organizer_email_not_found_404(client):
    org_id = await create_org(client)
    with patch(
        "app.services.organization_service.service.get_user_by_email",
        new=AsyncMock(return_value=None),
    ):
        resp = await client.post(
            f"/api/v1/organizations/{org_id}/organizers",
            json={"email": "ghost@example.com"},
        )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_add_organizer_duplicate_409(client):
    org_id = await create_org(client)
    with patch(
        "app.services.organization_service.service.get_user_by_email",
        new=AsyncMock(return_value=user_info(5)),
    ):
        first = await client.post(
            f"/api/v1/organizations/{org_id}/organizers",
            json={"email": "u5@example.com"},
        )
        assert first.status_code == 201
        second = await client.post(
            f"/api/v1/organizations/{org_id}/organizers",
            json={"email": "u5@example.com"},
        )
    assert second.status_code == 409


@pytest.mark.asyncio
async def test_add_organizer_forbidden_for_non_owner(client):
    org_id = await create_org(client)
    login_as(OTHER_ORGANIZER)  # не владелец и вообще не участник
    resp = await client.post(
        f"/api/v1/organizations/{org_id}/organizers",
        json={"email": "u6@example.com"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_remove_organizer_and_readd(client, test_db):
    org_id = await create_org(client)
    with patch(
        "app.services.organization_service.service.get_user_by_email",
        new=AsyncMock(return_value=user_info(5)),
    ):
        await client.post(
            f"/api/v1/organizations/{org_id}/organizers",
            json={"email": "u5@example.com"},
        )
        resp = await client.delete(f"/api/v1/organizations/{org_id}/organizers/5")
        assert resp.status_code == 204
        members = (
            await client.get(f"/api/v1/organizations/{org_id}/organizers")
        ).json()
        assert [m["user_id"] for m in members] == [OWNER.id]
        # Повторное добавление реактивирует мягко удалённую запись
        readd = await client.post(
            f"/api/v1/organizations/{org_id}/organizers",
            json={"email": "u5@example.com"},
        )
    assert readd.status_code == 201
    rows = (
        (
            await test_db.execute(
                select(OrganizationOrganizer).where(
                    OrganizationOrganizer.organization_id == org_id,
                    OrganizationOrganizer.user_id == 5,
                )
            )
        )
        .scalars()
        .all()
    )
    assert len(rows) == 1 and rows[0].is_active  # без дубликатов


@pytest.mark.asyncio
async def test_owner_cannot_remove_self(client):
    org_id = await create_org(client)
    resp = await client.delete(f"/api/v1/organizations/{org_id}/organizers/{OWNER.id}")
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_remove_non_member_404(client):
    org_id = await create_org(client)
    resp = await client.delete(f"/api/v1/organizations/{org_id}/organizers/999")
    assert resp.status_code == 404


# === Удаление организации ===


@pytest.mark.asyncio
async def test_delete_organization_by_owner(client, test_db):
    org_id = await create_org(client)
    resp = await client.delete(f"/api/v1/organizations/{org_id}")
    assert resp.status_code == 204
    org = await test_db.get(Organization, org_id)
    await test_db.refresh(org)
    assert org.is_active is False
    memberships = (
        (
            await test_db.execute(
                select(OrganizationOrganizer).where(
                    OrganizationOrganizer.organization_id == org_id
                )
            )
        )
        .scalars()
        .all()
    )
    assert memberships and all(not m.is_active for m in memberships)
    # В публичном листинге удалённой организации нет, но GET по id жив (история/чаты)
    listing = (await client.get("/api/v1/organizations")).json()
    assert all(o["id"] != org_id for o in listing)
    assert (await client.get(f"/api/v1/organizations/{org_id}")).status_code == 200


@pytest.mark.asyncio
async def test_delete_organization_by_admin(client):
    org_id = await create_org(client)
    login_as(ADMIN)
    assert (await client.delete(f"/api/v1/organizations/{org_id}")).status_code == 204


@pytest.mark.asyncio
async def test_delete_organization_forbidden_for_stranger(client):
    org_id = await create_org(client)
    login_as(OTHER_ORGANIZER)
    assert (await client.delete(f"/api/v1/organizations/{org_id}")).status_code == 403


@pytest.mark.asyncio
async def test_owner_can_create_new_org_after_deletion(client):
    org_id = await create_org(client, "Old Org")
    await client.delete(f"/api/v1/organizations/{org_id}")
    resp = await client.post("/api/v1/organizations", json={"name": "New Org"})
    assert resp.status_code == 201  # слот владельца освобождён partial-индексом
