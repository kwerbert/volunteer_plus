import os
import sys
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.services.event_service.config import settings

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.event_service.api.deps import get_current_user_id
from app.services.event_service.db.models import (
    Base,
    Event,
    EventRole,
    EventStatus,
    Participation,
    ParticipationStatus,
)
from app.services.event_service.db.session import get_db_session
from app.services.event_service.main import app
from app.utils.notifications_enums import NotificationType

TEST_DATABASE_URL = "sqlite+aiosqlite:///./test_volunteer_plus.db"
test_engine = create_async_engine(TEST_DATABASE_URL, echo=False, future=True)
session_factory = async_sessionmaker(
    test_engine, class_=AsyncSession, expire_on_commit=False
)

ORGANIZER_ID = 2
SERVICE_HEADERS = {"X-Service-Key": settings.SERVICE_API_KEY}


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
def admin_mock():
    with patch(
        "app.services.event_service.service.UserServiceClient.is_admin",
        new=AsyncMock(return_value=False),
    ) as m:
        yield m


@pytest.fixture(scope="function")
def notify_mock():
    with patch(
        "app.services.event_service.service."
        "NotificationServiceClient.notify_background",
        new=MagicMock(),
    ) as m:
        yield m


@pytest.fixture(scope="function", autouse=True)
def chat_mock():
    with patch(
        "app.services.event_service.service.ChatServiceClient.ensure_event_chat",
        new=AsyncMock(return_value=1),
    ) as m:
        yield m


@pytest.fixture(scope="function")
def organizers_mock():
    """Организаторы org 1: владелец 2 (он же текущий юзер) + добавленный 5."""
    with patch(
        "app.services.event_service.service.OrganizationServiceClient.get_organizers",
        new=AsyncMock(
            return_value=[
                {"user_id": 2, "role_in_org": "owner"},
                {"user_id": 5, "role_in_org": "organizer"},
            ]
        ),
    ) as m:
        yield m


@pytest.fixture(scope="function")
async def client(test_db, org_mock, admin_mock, notify_mock, organizers_mock):
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


async def _exists(session, model, pk) -> bool:
    return (
        await session.execute(select(model.id).where(model.id == pk))
    ).first() is not None


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


# === 4.2: отмена ===
@pytest.mark.asyncio
async def test_cancel_event_soft_and_cancels_participations(
    client, test_db, notify_mock
):
    event = await _create(client)
    await client.post(f"/api/v1/events/{event['id']}/register", json={"user_id": 1})
    await client.post(f"/api/v1/events/{event['id']}/register", json={"user_id": 7})

    # Сбрасываем уведомления о регистрациях (NEW_REGISTRATION), чтобы проверить только уведомления об отмене (EVENT_CANCELLED).
    notify_mock.reset_mock()

    resp = await client.delete(f"/api/v1/events/{event['id']}")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == "cancelled"
    assert data["cancelled_at"] is not None
    assert data["cancelled_participations"] == 2
    assert data["notified_volunteers"] == 2

    assert await _exists(test_db, Event, event["id"])  # мягкая отмена, не DELETE
    statuses = (
        (
            await test_db.execute(
                select(Participation.status).where(
                    Participation.event_id == event["id"]
                )
            )
        )
        .scalars()
        .all()
    )
    assert all(s == ParticipationStatus.CANCELLED for s in statuses)

    assert notify_mock.call_count == 2  # волонтёрам + организаторам
    volunteers = notify_mock.call_args_list[0].kwargs
    assert volunteers["user_ids"] == [1, 7]
    assert volunteers["notification_type"] == NotificationType.EVENT_CANCELLED
    assert event["title"] in volunteers["body"]
    organizers = notify_mock.call_args_list[1].kwargs
    assert organizers["user_ids"] == [5]  # инициатор (2) исключён


@pytest.mark.asyncio
async def test_cancel_twice_409(client):
    event = await _create(client)
    assert (await client.delete(f"/api/v1/events/{event['id']}")).status_code == 200
    assert (await client.delete(f"/api/v1/events/{event['id']}")).status_code == 409


@pytest.mark.asyncio
async def test_cancel_forbidden_for_stranger(client, org_mock, admin_mock):
    event = await _create(client)
    org_mock.return_value = False
    admin_mock.return_value = False
    assert (await client.delete(f"/api/v1/events/{event['id']}")).status_code == 403


@pytest.mark.asyncio
async def test_cancel_allowed_for_admin(client, org_mock, admin_mock):
    event = await _create(client)
    org_mock.return_value = False
    admin_mock.return_value = True
    assert (await client.delete(f"/api/v1/events/{event['id']}")).status_code == 200


@pytest.mark.asyncio
async def test_register_on_cancelled_event_409(client):
    event = await _create(client)
    await client.delete(f"/api/v1/events/{event['id']}")
    resp = await client.post(
        f"/api/v1/events/{event['id']}/register", json={"user_id": 1}
    )
    assert resp.status_code == 409


# === 4.4: завершение ===
@pytest.mark.asyncio
async def test_completed_event_cannot_be_cancelled(client, test_db):
    event = await _create(client)
    obj = await test_db.get(Event, event["id"])
    obj.start_date = datetime.now(timezone.utc) - timedelta(days=2)
    obj.end_date = datetime.now(timezone.utc) - timedelta(days=2) + timedelta(hours=2)
    await test_db.commit()

    detail = (await client.get(f"/api/v1/events/{event['id']}")).json()
    assert detail["status"] == "completed"  # ленивое завершение при чтении
    assert (await client.delete(f"/api/v1/events/{event['id']}")).status_code == 409


@pytest.mark.asyncio
async def test_complete_expired_endpoint(client, test_db):
    event = await _create(client)
    obj = await test_db.get(Event, event["id"])
    obj.end_date = datetime.now(timezone.utc) - timedelta(hours=1)
    await test_db.commit()

    resp = await client.post("/api/v1/events/complete-expired", headers=SERVICE_HEADERS)
    assert resp.status_code == 200
    assert resp.json()["completed_events"] == 1
    await test_db.refresh(obj)
    assert obj.status == EventStatus.COMPLETED.value


# === 4.1: event_role_id + отмена регистрации ===
@pytest.mark.asyncio
async def test_register_with_event_role_id_field(client):
    event = await _create(client, roles=[{"name": "Уборка"}, {"name": "Посадка"}])
    role_id = event["roles"][0]["id"]
    resp = await client.post(
        f"/api/v1/events/{event['id']}/register",
        json={"user_id": 1, "event_role_id": role_id},
    )
    assert resp.status_code == 200
    assert resp.json()["role_id"] == role_id


@pytest.mark.asyncio
async def test_unregister_frees_role_slot(client):
    event = await _create(client, roles=[{"name": "Уборка", "max_participants": 1}])
    role_id = event["roles"][0]["id"]
    body = {"event_role_id": role_id}
    assert (
        await client.post(
            f"/api/v1/events/{event['id']}/register", json={"user_id": 1, **body}
        )
    ).status_code == 200
    assert (
        await client.post(
            f"/api/v1/events/{event['id']}/register", json={"user_id": 2, **body}
        )
    ).status_code == 409

    unreg = await client.delete(f"/api/v1/events/{event['id']}/register/1")
    assert unreg.status_code == 200
    assert unreg.json()["status"] == "cancelled"

    assert (
        await client.post(
            f"/api/v1/events/{event['id']}/register", json={"user_id": 2, **body}
        )
    ).status_code == 200


# === 4.3: очистка ===
@pytest.mark.asyncio
async def test_cleanup_deletes_only_old_cancelled(client, test_db):
    old = await _create(client, title="Old cancelled")
    recent = await _create(client, title="Recent cancelled")
    completed = await _create(client, title="Completed")
    now = datetime.now(timezone.utc)
    for eid, st, cancelled_at in [
        (old["id"], EventStatus.CANCELLED.value, now - timedelta(days=31)),
        (recent["id"], EventStatus.CANCELLED.value, now - timedelta(days=1)),
        (completed["id"], EventStatus.COMPLETED.value, None),
    ]:
        obj = await test_db.get(Event, eid)
        obj.status = st
        obj.cancelled_at = cancelled_at
    await test_db.commit()

    resp = await client.post("/api/v1/events/cleanup", headers=SERVICE_HEADERS)
    assert resp.status_code == 200, resp.text
    assert resp.json()["deleted_events"] == 1
    assert resp.json()["retention_days"] == 30
    assert not await _exists(test_db, Event, old["id"])
    assert await _exists(test_db, Event, recent["id"])
    assert await _exists(test_db, Event, completed["id"])  # completed — никогда
    assert not await _exists(test_db, EventRole, old["roles"][0]["id"])


@pytest.mark.asyncio
async def test_cleanup_requires_service_key(client):
    assert (await client.post("/api/v1/events/cleanup")).status_code == 401
    assert (
        await client.post("/api/v1/events/cleanup", headers={"X-Service-Key": "wrong"})
    ).status_code == 403


# === 4.6: удаление организации ===
@pytest.mark.asyncio
async def test_internal_cancel_organization_events(client, test_db):
    e1 = await _create(client, org_id=1, title="Org1 A")
    e2 = await _create(client, org_id=1, title="Org1 B")
    e3 = await _create(client, org_id=2, title="Org2")
    await client.post(f"/api/v1/events/{e1['id']}/register", json={"user_id": 1})

    resp = await client.post(
        "/internal/organizations/1/cancel-events", headers=SERVICE_HEADERS
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["cancelled_events"] == 2
    assert data["cancelled_participations"] == 1
    assert data["notified_volunteers"] == 1

    for eid in (e1["id"], e2["id"]):
        obj = await test_db.get(Event, eid)
        await test_db.refresh(obj)
        assert obj.status == EventStatus.CANCELLED.value
    other = await test_db.get(Event, e3["id"])
    await test_db.refresh(other)
    assert other.status == EventStatus.ACTIVE.value


@pytest.mark.asyncio
async def test_internal_cancel_keeps_completed(client, test_db):
    event = await _create(client, org_id=1)
    obj = await test_db.get(Event, event["id"])
    obj.end_date = datetime.now(timezone.utc) - timedelta(hours=1)
    await test_db.commit()

    resp = await client.post(
        "/internal/organizations/1/cancel-events", headers=SERVICE_HEADERS
    )
    data = resp.json()
    assert data["cancelled_events"] == 0
    assert data["completed_events"] == 1
    await test_db.refresh(obj)
    assert obj.status == EventStatus.COMPLETED.value


# === Этап 5: уведомления организаторам ===


@pytest.mark.asyncio
async def test_register_notifies_organizers(client, notify_mock):
    event = await _create(client)
    assert (
        await client.post(f"/api/v1/events/{event['id']}/register", json={"user_id": 1})
    ).status_code == 200
    notify_mock.assert_called_once()
    kw = notify_mock.call_args.kwargs
    assert kw["notification_type"] == NotificationType.NEW_REGISTRATION
    assert kw["user_ids"] == [2, 5]
    assert kw["data"]["event_id"] == event["id"]
    assert kw["data"]["user_id"] == 1


@pytest.mark.asyncio
async def test_register_by_organizer_does_not_notify_self(client, notify_mock):
    event = await _create(client)
    await client.post(f"/api/v1/events/{event['id']}/register", json={"user_id": 2})
    assert notify_mock.call_args.kwargs["user_ids"] == [5]


@pytest.mark.asyncio
async def test_unregister_notifies_organizers(client, notify_mock):
    event = await _create(client)
    await client.post(f"/api/v1/events/{event['id']}/register", json={"user_id": 1})
    notify_mock.reset_mock()
    assert (
        await client.delete(f"/api/v1/events/{event['id']}/register/1")
    ).status_code == 200
    notify_mock.assert_called_once()
    kw = notify_mock.call_args.kwargs
    assert kw["notification_type"] == NotificationType.REGISTRATION_CANCELLED
    assert kw["user_ids"] == [2, 5]


@pytest.mark.asyncio
async def test_registration_survives_org_service_outage(
    client, notify_mock, organizers_mock
):
    organizers_mock.side_effect = HTTPException(status_code=503, detail="down")
    event = await _create(client)
    assert (
        await client.post(f"/api/v1/events/{event['id']}/register", json={"user_id": 1})
    ).status_code == 200
    notify_mock.assert_not_called()


@pytest.mark.asyncio
async def test_org_deletion_aggregates_organizer_notification(client, notify_mock):
    e1 = await _create(client, org_id=1, title="Event A")
    await _create(client, org_id=1, title="Event B")
    await client.post(f"/api/v1/events/{e1['id']}/register", json={"user_id": 1})
    notify_mock.reset_mock()
    resp = await client.post(
        "/internal/organizations/1/cancel-events", headers=SERVICE_HEADERS
    )
    assert resp.status_code == 200
    assert notify_mock.call_count == 2  # 1 волонтёру + 1 агрегированное
    last = notify_mock.call_args_list[-1].kwargs
    assert last["user_ids"] == [2, 5]
    assert last["data"]["cancelled_events"] == 2
