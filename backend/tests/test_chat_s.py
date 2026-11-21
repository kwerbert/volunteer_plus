import os
import sys
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(TEST_DIR, ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


@pytest.fixture
def mock_session():
    session = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.execute = AsyncMock()
    session.add = AsyncMock()
    session.get = AsyncMock()
    return session


@pytest.fixture
def mock_repo():
    repo = AsyncMock()
    repo.create_chat = AsyncMock()
    repo.get_chat_by_id = AsyncMock()
    repo.get_user_chats = AsyncMock()
    repo.update_chat = AsyncMock()
    repo.deactivate_chat = AsyncMock()
    repo.find_personal_chat = AsyncMock()
    repo.user_has_access_to_chat = AsyncMock()
    repo.add_member = AsyncMock()
    repo.get_member = AsyncMock()
    repo.get_chat_members = AsyncMock()
    repo.remove_member = AsyncMock()
    repo.update_member_role = AsyncMock()
    repo.create_message = AsyncMock()
    repo.get_messages = AsyncMock()
    repo.get_message_by_id = AsyncMock()
    repo.mark_message_read = AsyncMock()
    repo.mark_chat_messages_read = AsyncMock()
    repo.get_unread_count = AsyncMock()
    return repo


@pytest.fixture
def clear_chat_settings_cache():
    try:
        from app.services.chat_service.config import get_settings

        get_settings.cache_clear()
    except (ImportError, AttributeError):
        pass
    yield
    try:
        from app.services.chat_service.config import get_settings

        get_settings.cache_clear()
    except (ImportError, AttributeError):
        pass


class TestConfig:
    def test_001_config_settings(self, clear_chat_settings_cache):
        from app.services.chat_service.config import get_settings

        settings = get_settings()
        assert settings.SERVICE_PORT == 8007
        assert settings.SERVICE_NAME == "chat_service"
        assert "sqlite+aiosqlite" in settings.DATABASE_URL
        assert settings.JWT_ALGORITHM == "HS256"
        assert settings.DEFAULT_PAGE_SIZE == 20
        print("Конфигурация загружена корректно")

    def test_002_config_cors_origins(self, clear_chat_settings_cache):
        from app.services.chat_service.config import get_settings

        settings = get_settings()
        origins = settings.cors_origins_list
        assert isinstance(origins, list)
        assert "http://10.0.2.2:8007" in origins  # Для Android эмулятора
        print("CORS origins распарсены корректно")


class TestSchemas:
    def test_003_chat_create_request_schema(self):
        from pydantic import ValidationError

        from app.services.chat_service.api.schemas import (
            ChatCreateRequest,
            ChatTypeEnum,
        )

        req = ChatCreateRequest(
            chat_type=ChatTypeEnum.ORGANIZER,
            participant_ids=[2],
        )
        assert req.chat_type == ChatTypeEnum.ORGANIZER
        assert req.participant_ids == [2]
        with pytest.raises(ValidationError):
            ChatCreateRequest(chat_type=ChatTypeEnum.ORGANIZER, participant_ids=[])
        print("Схема создания чата валидируется корректно")

    def test_004_message_create_request_schema(self):
        from pydantic import ValidationError

        from app.services.chat_service.api.schemas import (
            MessageCreateRequest,
            MessageTypeEnum,
        )

        req = MessageCreateRequest(content="Hello!", message_type=MessageTypeEnum.TEXT)
        assert req.content == "Hello!"

        with pytest.raises(ValidationError):
            MessageCreateRequest(content="")  # Пустой контент
        with pytest.raises(ValidationError):
            MessageCreateRequest(content="x" * 5000)  # Слишком длинный
        print("Схема сообщения валидируется корректно")

    def test_005_response_schemas(self):
        from app.services.chat_service.api.schemas import (
            ChatMemberResponse,
            ChatResponse,
            ChatTypeEnum,
            MessageResponse,
        )

        member = ChatMemberResponse(
            user_id=1, role="admin", joined_at=now_utc(), is_muted=False
        )
        assert member.user_id == 1

        chat = ChatResponse(
            id=1,
            chat_type=ChatTypeEnum.ORGANIZER,
            created_at=now_utc(),
            unread_count=0,
            members=[member],
        )
        assert chat.chat_type == ChatTypeEnum.ORGANIZER

        msg = MessageResponse(
            id=1,
            chat_id=1,
            sender_id=2,
            content="Hi",
            message_type="text",
            is_read=False,
            created_at=now_utc(),
        )
        assert msg.is_read is False
        print("Схемы ответов создаются корректно")


class TestModels:
    def test_006_chat_model(self):
        from app.services.chat_service.db.models import Chat

        assert Chat.__tablename__ == "chats"
        columns = [col.name for col in Chat.__table__.columns]
        required = ["id", "chat_type", "title", "is_active", "created_at"]
        for field in required:
            assert field in columns
        print("Модель Chat корректна")

    def test_007_message_model(self):
        from app.services.chat_service.db.models import Message

        assert Message.__tablename__ == "messages"
        columns = [col.name for col in Message.__table__.columns]
        required = ["id", "chat_id", "sender_id", "content", "is_read", "created_at"]
        for field in required:
            assert field in columns
        print("Модель Message корректна")


@pytest.mark.asyncio
class TestRepository:
    async def test_008_create_chat(self, mock_session, mock_repo):
        from app.services.chat_service.db.models import Chat, ChatTypeEnum
        from app.services.chat_service.db.repository import ChatRepository

        mock_chat = Chat(
            id=1,
            chat_type=ChatTypeEnum.ORGANIZER,
            is_active=True,
            created_at=now_utc(),
        )
        mock_session.get.return_value = mock_chat
        mock_repo.create_chat = AsyncMock(return_value=mock_chat)

        repo = ChatRepository(mock_session)
        assert repo is not None
        print("Репозиторий создаётся корректно")

    async def test_009_create_message(self, mock_session):
        from app.services.chat_service.db.models import Message, MessageTypeEnum
        from app.services.chat_service.db.repository import ChatRepository

        repo = ChatRepository(mock_session)
        mock_message = Message(
            id=1,
            chat_id=1,
            sender_id=2,
            content="Test",
            message_type=MessageTypeEnum.TEXT,
            is_read=False,
            created_at=now_utc(),
        )
        mock_session.get.return_value = mock_message
        assert hasattr(repo, "create_message")
        assert hasattr(repo, "get_messages")
        print("Методы сообщений доступны")


@pytest.mark.asyncio
class TestService:
    async def test_010_send_message(self, mock_repo):
        from app.services.chat_service.core.service import ChatService
        from app.services.chat_service.db.models import Message, MessageTypeEnum

        mock_repo.user_has_access_to_chat = AsyncMock(return_value=True)
        mock_message = Message(
            id=1,
            chat_id=1,
            sender_id=2,
            content="Hello",
            message_type=MessageTypeEnum.TEXT,
            is_read=False,
            created_at=now_utc(),
        )
        mock_repo.create_message = AsyncMock(return_value=mock_message)
        mock_repo.update_chat = AsyncMock()

        service = ChatService(mock_repo)
        result = await service.send_message(chat_id=1, sender_id=2, content="Hello")

        assert result.content == "Hello"
        mock_repo.create_message.assert_called_once()
        print("Отправка сообщения работает корректно")

    async def test_011_mark_message_read(self, mock_repo):
        from app.services.chat_service.core.service import ChatService
        from app.services.chat_service.db.models import Message, MessageTypeEnum

        mock_message = Message(
            id=1,
            chat_id=1,
            sender_id=2,
            content="Hi",
            message_type=MessageTypeEnum.TEXT,
            is_read=True,
            created_at=now_utc(),
            read_at=now_utc(),
        )
        mock_repo.mark_message_read = AsyncMock(return_value=mock_message)

        service = ChatService(mock_repo)
        result = await service.mark_message_read(1)

        assert result is not None
        assert result.is_read is True


class TestMainApp:
    def test_012_app_creation(self, clear_chat_settings_cache):
        from app.services.chat_service.main import app

        assert app is not None
        assert app.title == "chat_service"
        assert app.version == "1.0.0"
        print("FastAPI приложение создано корректно")

    def test_013_app_routes(self, clear_chat_settings_cache):
        from app.services.chat_service.main import app
        from tests.conftest import collect_route_paths

        routes = collect_route_paths(app)

        assert "/api/v1/chats" in routes
        assert "/api/v1/chats/{chat_id}/messages" in routes
        assert "/api/v1/messages/{message_id}/read" in routes
        assert "/health" in routes
        assert "/" in routes
        print("Все эндпоинты подключены корректно")

    def test_014_health_endpoint(self, clear_chat_settings_cache):
        from app.services.chat_service.main import app
        from tests.conftest import collect_route_paths

        routes = collect_route_paths(app)
        assert routes.count("/health") == 1
        print("Health endpoint доступен")


def _make_mock_response(status: int, body: str):
    resp = MagicMock()
    resp.status = status
    resp.text = AsyncMock(return_value=body)
    resp.__aenter__ = AsyncMock(return_value=resp)
    resp.__aexit__ = AsyncMock(return_value=None)
    return resp


def _make_mock_session(*responses):
    session = MagicMock()
    session.post = MagicMock(side_effect=list(responses))
    return session


class TestPushNotifications:
    def test_027_notification_request_valid_for_create_schema(self):
        """_send_one_push собирает payload, который принимает CreateNotificationRequest.

        Это регрессионный тест на исходный баг: раньше поля `notification_type`
        не было вовсе, а `priority` был в нижнем регистре — notification_service
        отвечал 422. Теперь сериализованный payload обязан проходить валидацию
        целевой схемы.
        """
        from app.services.chat_service.api.schemas import NotificationRequest
        from app.services.notification_service.api.schemas import (
            CreateNotificationRequest,
        )
        from app.utils.notifications_enums import NotificationType, Priority

        chat_req = NotificationRequest(
            user_id=3,
            title="Новое сообщение",
            body="Привет!",
            notification_type=NotificationType.CHAT,
            priority=Priority.HIGH,
            data={"chat_id": 1, "sender_id": 2},
        )
        payload = chat_req.model_dump(mode="json")

        # Если chat_service сгенерировал payload, несовместимый с целевой схемой, здесь вылетит ValidationError — регрессия поймана на CI.
        validated = CreateNotificationRequest(**payload)
        assert validated.user_id == 3
        assert validated.notification_type == NotificationType.CHAT
        assert validated.priority == Priority.HIGH
        assert validated.data == {"chat_id": 1, "sender_id": 2}
        print("NotificationRequest сериализуется в валидный CreateNotificationRequest")

    def test_028_shared_enums_have_expected_values(self):
        from app.utils.notifications_enums import NotificationType

        assert {
            "CHAT",
            "NEW_EVENT",
            "EVENT_REMINDER",
            "SYSTEM",
            "EVENT_CANCELLED",
        } <= {t.value for t in NotificationType}
        print("Shared enums совместимы с notification_service")

    @pytest.mark.asyncio
    async def test_029_send_one_push_success(self):
        """2xx → status='sent', payload уходит с правильными полями."""
        from app.services.chat_service.api import router as chat_router

        session = _make_mock_session(
            _make_mock_response(201, '{"success": true, "notification_id": 42}')
        )
        status, code = await chat_router._send_one_push(
            session=session, user_id=3, chat_id=1, sender_id=2, body="hi"
        )
        assert status == "sent"
        assert code == 201

        payload = session.post.call_args.kwargs["json"]
        assert payload["notification_type"] == "CHAT"  # upper-case, как enum
        assert payload["priority"] == "HIGH"  # upper-case, как enum
        assert payload["data"] == {"chat_id": 1, "sender_id": 2}
        print("_send_one_push: успех + валидный payload")

    @pytest.mark.asyncio
    async def test_030_send_one_push_no_tokens(self):
        """201 с error=NO_TOKENS → status='no_tokens' (не ошибка)."""
        from app.services.chat_service.api import router as chat_router

        session = _make_mock_session(
            _make_mock_response(201, '{"success": false, "error": "NO_TOKENS"}')
        )
        status, code = await chat_router._send_one_push(
            session=session, user_id=3, chat_id=1, sender_id=2, body="hi"
        )
        assert status == "no_tokens"
        assert code == 201
        print("_send_one_push: NO_TOKENS распознан как норма")

    @pytest.mark.asyncio
    async def test_031_send_one_push_client_error_not_retried(self):
        """422 → client_error, БЕЗ retry (иначе шторм запросов при баге)."""
        from app.services.chat_service.api import router as chat_router

        resp_422 = _make_mock_response(
            422, '{"detail": [{"loc": ["body"], "msg": "field required"}]}'
        )
        resp_500 = _make_mock_response(500, "boom")  # если бы ретраили, дошло бы сюда
        session = _make_mock_session(resp_422, resp_500)

        original = chat_router._PUSH_RETRY_BACKOFF_SECONDS
        chat_router._PUSH_RETRY_BACKOFF_SECONDS = 0.0
        try:
            await chat_router._send_one_push_with_retry(
                session=session, user_id=3, chat_id=1, sender_id=2, body="hi"
            )
        finally:
            chat_router._PUSH_RETRY_BACKOFF_SECONDS = original

        assert session.post.call_count == 1, "4xx не должен ретраиться"
        print("_send_one_push_with_retry: 422 без retry")

    @pytest.mark.asyncio
    async def test_032_send_one_push_retryable_then_success(self):
        """500 → 500 → 201: успешный исход после двух retry."""
        from app.services.chat_service.api import router as chat_router

        session = _make_mock_session(
            _make_mock_response(500, "boom"),
            _make_mock_response(500, "boom"),
            _make_mock_response(201, '{"success": true}'),
        )

        original = chat_router._PUSH_RETRY_BACKOFF_SECONDS
        chat_router._PUSH_RETRY_BACKOFF_SECONDS = 0.0
        try:
            await chat_router._send_one_push_with_retry(
                session=session, user_id=3, chat_id=1, sender_id=2, body="hi"
            )
        finally:
            chat_router._PUSH_RETRY_BACKOFF_SECONDS = original

        assert session.post.call_count == 3
        print("_send_one_push_with_retry: 5xx ретраится до успеха")

    @pytest.mark.asyncio
    async def test_033_send_one_push_retry_exhausted(self):
        """Все попытки 5xx → после N попыток сдаёмся без исключения."""
        from app.services.chat_service.api import router as chat_router

        n = chat_router._PUSH_RETRY_ATTEMPTS
        session = _make_mock_session(
            *[_make_mock_response(500, "boom") for _ in range(n)]
        )

        original = chat_router._PUSH_RETRY_BACKOFF_SECONDS
        chat_router._PUSH_RETRY_BACKOFF_SECONDS = 0.0
        try:
            # Не должно кинуть исключение наружу — фоновая задача обязана дойти до конца
            await chat_router._send_one_push_with_retry(
                session=session, user_id=3, chat_id=1, sender_id=2, body="hi"
            )
        finally:
            chat_router._PUSH_RETRY_BACKOFF_SECONDS = original

        assert session.post.call_count == n
        print(f"_send_one_push_with_retry: {n} попыток и корректная сдача")


class TestStage5ChatRecipients:
    def test_034_collect_recipients_union_and_mute(self):
        from app.services.chat_service.api.router import _collect_message_recipients

        members = [
            SimpleNamespace(user_id=1, is_muted=False),
            SimpleNamespace(user_id=2, is_muted=True),
            SimpleNamespace(user_id=3, is_muted=False),
        ]
        # 2 — muted organizator, 4 — организатор вне чата, 3 — отправитель
        assert _collect_message_recipients(members, [2, 4], sender_id=3) == [1, 4]

    @pytest.mark.asyncio
    async def test_035_event_chat_fans_out_to_organizers(self):
        from app.services.chat_service.api import router as chat_router
        from app.services.chat_service.api.schemas import ChatTypeEnum

        chat = SimpleNamespace(
            chat_type=ChatTypeEnum.EVENT, organization_id=7, event_id=9
        )
        members = [
            SimpleNamespace(user_id=1, is_muted=False),
            SimpleNamespace(user_id=2, is_muted=True),
        ]
        with (
            patch("app.services.chat_service.api.router.ChatRepository") as repo_cls,
            patch("app.services.chat_service.api.router.organization_client") as org,
        ):
            repo = repo_cls.return_value
            repo.get_chat_members = AsyncMock(return_value=members)
            repo.get_chat_by_id = AsyncMock(return_value=chat)
            org.get_organizer_ids = AsyncMock(return_value=[2, 5])
            kwargs = await chat_router._prepare_message_notification(
                1, 1, "hi", MagicMock()
            )
        org.get_organizer_ids.assert_awaited_once_with(7)
        assert kwargs["recipients"] == [5]
        assert kwargs["extra_data"] == {"org_id": 7, "event_id": 9}

    @pytest.mark.asyncio
    async def test_036_personal_organizer_chat_is_not_broadcast(self):
        from app.services.chat_service.api import router as chat_router
        from app.services.chat_service.api.schemas import ChatTypeEnum

        chat = SimpleNamespace(
            chat_type=ChatTypeEnum.ORGANIZER, organization_id=7, event_id=None
        )
        with (
            patch("app.services.chat_service.api.router.ChatRepository") as repo_cls,
            patch("app.services.chat_service.api.router.organization_client") as org,
        ):
            repo = repo_cls.return_value
            repo.get_chat_members = AsyncMock(
                return_value=[SimpleNamespace(user_id=1, is_muted=False)]
            )
            repo.get_chat_by_id = AsyncMock(return_value=chat)
            org.get_organizer_ids = AsyncMock(return_value=[2, 5])
            kwargs = await chat_router._prepare_message_notification(
                1, 1, "личное", MagicMock()
            )
        org.get_organizer_ids.assert_not_awaited()
        assert kwargs is None  # кроме отправителя никого нет

    def test_037_new_notification_types_shared(self):
        from app.services.notification_service.api.schemas import (
            CreateNotificationRequest,
        )
        from app.utils.notifications_enums import NotificationType

        for t in ("NEW_REGISTRATION", "REGISTRATION_CANCELLED", "NEW_ORGANIZER_ADDED"):
            req = CreateNotificationRequest(
                user_id=1, title="t", body="b", notification_type=NotificationType(t)
            )
            assert req.notification_type.value == t


class TestStage6OrganizerSync:
    """Этап 6: организаторы — участники EVENT-чатов, синхронизация состава."""

    @staticmethod
    def _db_with_chat(chat):
        db = MagicMock()
        result = MagicMock()
        result.scalar_one_or_none.return_value = chat
        db.execute = AsyncMock(return_value=result)
        return db

    @pytest.mark.asyncio
    async def test_038_ensure_event_chat_adds_all_organizers(self):
        from app.services.chat_service.core import chat_lifecycle

        db = self._db_with_chat(SimpleNamespace(id=10))
        with (
            patch(
                "app.services.chat_service.core.chat_lifecycle.ChatRepository"
            ) as repo_cls,
            patch(
                "app.services.chat_service.core.chat_lifecycle.organization_client"
            ) as org,
        ):
            repo = repo_cls.return_value
            repo.get_member = AsyncMock(return_value=None)
            repo.add_member = AsyncMock()
            org.get_organizer_ids = AsyncMock(return_value=[2, 5])

            chat_id = await chat_lifecycle.ensure_event_chat(
                db=db, event_id=9, user_id=1, organization_id=7
            )

        assert chat_id == 10
        org.get_organizer_ids.assert_awaited_once_with(7)
        calls = repo.add_member.call_args_list
        assert call(10, 1, role="member") in calls
        assert call(10, 2, role="organizer") in calls
        assert call(10, 5, role="organizer") in calls
        assert repo.add_member.await_count == 3

    @pytest.mark.asyncio
    async def test_039_ensure_event_chat_creates_chat_with_org(self):
        from app.services.chat_service.core import chat_lifecycle
        from app.services.chat_service.db.models import ChatTypeEnum

        db = self._db_with_chat(None)
        with (
            patch(
                "app.services.chat_service.core.chat_lifecycle.ChatRepository"
            ) as repo_cls,
            patch(
                "app.services.chat_service.core.chat_lifecycle.organization_client"
            ) as org,
        ):
            repo = repo_cls.return_value
            repo.create_chat = AsyncMock(return_value=SimpleNamespace(id=11))
            repo.get_member = AsyncMock(return_value=None)
            repo.add_member = AsyncMock()
            org.get_organizer_ids = AsyncMock(return_value=[2])

            chat_id = await chat_lifecycle.ensure_event_chat(
                db=db, event_id=9, user_id=1, organization_id=7
            )

        assert chat_id == 11
        kwargs = repo.create_chat.call_args.kwargs
        assert kwargs["chat_type"] == ChatTypeEnum.EVENT
        assert kwargs["event_id"] == 9
        assert kwargs["organization_id"] == 7

    @pytest.mark.asyncio
    async def test_040_organizer_self_registration_gets_organizer_role(self):
        from app.services.chat_service.core import chat_lifecycle

        db = self._db_with_chat(SimpleNamespace(id=10))
        with (
            patch(
                "app.services.chat_service.core.chat_lifecycle.ChatRepository"
            ) as repo_cls,
            patch(
                "app.services.chat_service.core.chat_lifecycle.organization_client"
            ) as org,
        ):
            repo = repo_cls.return_value
            repo.get_member = AsyncMock(return_value=None)
            repo.add_member = AsyncMock()
            org.get_organizer_ids = AsyncMock(return_value=[2, 5])

            await chat_lifecycle.ensure_event_chat(
                db=db, event_id=9, user_id=2, organization_id=7
            )

        calls = repo.add_member.call_args_list
        assert repo.add_member.await_count == 2  # без дубля для user_id=2
        assert all(c.kwargs["role"] == "organizer" for c in calls)
        assert {c.args[1] for c in calls} == {2, 5}

    @pytest.mark.asyncio
    async def test_041_org_service_outage_keeps_volunteer_in_chat(self):
        """organization_service лёг → клиент вернул [] → регистрация жива."""
        from app.services.chat_service.core import chat_lifecycle

        db = self._db_with_chat(SimpleNamespace(id=10))
        with (
            patch(
                "app.services.chat_service.core.chat_lifecycle.ChatRepository"
            ) as repo_cls,
            patch(
                "app.services.chat_service.core.chat_lifecycle.organization_client"
            ) as org,
        ):
            repo = repo_cls.return_value
            repo.get_member = AsyncMock(return_value=None)
            repo.add_member = AsyncMock()
            org.get_organizer_ids = AsyncMock(return_value=[])

            chat_id = await chat_lifecycle.ensure_event_chat(
                db=db, event_id=9, user_id=1, organization_id=7
            )

        assert chat_id == 10
        repo.add_member.assert_awaited_once_with(10, 1, role="member")

    @pytest.mark.asyncio
    async def test_042_add_sync_dedup_and_role_upgrade(self):
        from app.services.chat_service.core import chat_lifecycle

        chats = [SimpleNamespace(id=1), SimpleNamespace(id=2), SimpleNamespace(id=3)]
        members = {
            1: SimpleNamespace(user_id=5, left_at=None, role="member"),
            2: SimpleNamespace(user_id=5, left_at=None, role="organizer"),
            3: None,
        }
        with patch(
            "app.services.chat_service.core.chat_lifecycle.ChatRepository"
        ) as repo_cls:
            repo = repo_cls.return_value
            repo.get_org_event_chats = AsyncMock(return_value=chats)
            repo.get_member = AsyncMock(side_effect=lambda cid, uid: members[cid])
            repo.update_member_role = AsyncMock()
            repo.add_member = AsyncMock()

            updated = await chat_lifecycle.add_organizer_to_org_chats(
                db=MagicMock(), organization_id=7, user_id=5
            )

        assert updated == 2  # чат 2 уже в порядке — не считается
        repo.get_org_event_chats.assert_awaited_once_with(7)
        repo.update_member_role.assert_awaited_once_with(1, 5, "organizer")
        repo.add_member.assert_awaited_once_with(3, 5, role="organizer")

    @pytest.mark.asyncio
    async def test_043_remove_sync_only_active_memberships(self):
        from app.services.chat_service.core import chat_lifecycle

        chats = [SimpleNamespace(id=1), SimpleNamespace(id=2), SimpleNamespace(id=3)]
        members = {
            1: SimpleNamespace(user_id=5, left_at=None, role="organizer"),
            2: SimpleNamespace(user_id=5, left_at=now_utc(), role="organizer"),
            3: None,
        }
        with patch(
            "app.services.chat_service.core.chat_lifecycle.ChatRepository"
        ) as repo_cls:
            repo = repo_cls.return_value
            repo.get_org_event_chats = AsyncMock(return_value=chats)
            repo.get_member = AsyncMock(side_effect=lambda cid, uid: members[cid])
            repo.remove_member = AsyncMock()

            removed = await chat_lifecycle.remove_organizer_from_org_chats(
                db=MagicMock(), organization_id=7, user_id=5
            )

        assert removed == 1
        repo.remove_member.assert_awaited_once_with(1, 5)


class TestStage6Repository:
    """Реальная SQLite: реактивация участника и фильтр чатов организации."""

    @staticmethod
    async def _make_repo():
        from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
        from sqlalchemy.pool import StaticPool

        from app.services.chat_service.db.models import Base
        from app.services.chat_service.db.repository import ChatRepository

        engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        session = AsyncSession(engine, expire_on_commit=False)
        return engine, session, ChatRepository(session)

    @pytest.mark.asyncio
    async def test_044_add_member_reactivates_after_removal(self):
        from app.services.chat_service.db.models import ChatTypeEnum

        engine, session, repo = await self._make_repo()
        async with session:
            chat = await repo.create_chat(
                chat_type=ChatTypeEnum.EVENT, event_id=1, organization_id=7
            )
            first = await repo.add_member(chat.id, 5, role="organizer")
            same = await repo.add_member(chat.id, 5, role="organizer")
            assert same.id == first.id  # идемпотентность

            await repo.remove_member(chat.id, 5)
            assert not await repo.user_has_access_to_chat(chat.id, 5)

            again = await repo.add_member(chat.id, 5, role="organizer")
            assert again.id == first.id  # реактивация, не дубликат
            assert again.left_at is None
            assert await repo.user_has_access_to_chat(chat.id, 5)
            # get_member не падает на MultipleResultsFound
            assert (await repo.get_member(chat.id, 5)).id == first.id
        await engine.dispose()

    @pytest.mark.asyncio
    async def test_045_get_org_event_chats_filters_type_and_active(self):
        from app.services.chat_service.db.models import ChatTypeEnum

        engine, session, repo = await self._make_repo()
        async with session:
            target = await repo.create_chat(
                chat_type=ChatTypeEnum.EVENT, event_id=1, organization_id=7
            )
            inactive = await repo.create_chat(
                chat_type=ChatTypeEnum.EVENT, event_id=2, organization_id=7
            )
            await repo.deactivate_chat(inactive.id)
            await repo.create_chat(
                chat_type=ChatTypeEnum.ORGANIZER, organization_id=7
            )  # личный — не синхронизируем
            await repo.create_chat(
                chat_type=ChatTypeEnum.EVENT, event_id=3, organization_id=8
            )  # чужая организация

            chats = await repo.get_org_event_chats(7)
            assert [c.id for c in chats] == [target.id]
        await engine.dispose()


class TestStage6InternalEndpoints:
    @pytest.mark.asyncio
    async def test_046_add_organizer_endpoint_contract(self):
        from httpx import ASGITransport, AsyncClient

        from app.services.chat_service.config import settings
        from app.services.chat_service.db.session import get_db_session
        from app.services.chat_service.main import app

        app.dependency_overrides[get_db_session] = lambda: MagicMock()
        try:
            with patch(
                "app.services.chat_service.api.internal_router.add_organizer_to_org_chats",
                new=AsyncMock(return_value=2),
            ) as sync:
                transport = ASGITransport(app=app)
                async with AsyncClient(
                    transport=transport, base_url="http://test"
                ) as ac:
                    url = "/internal/organizations/7/add-organizer"
                    body = {"user_id": 5}
                    assert (await ac.post(url, json=body)).status_code == 401
                    assert (
                        await ac.post(
                            url, json=body, headers={"X-Service-Key": "wrong"}
                        )
                    ).status_code == 403
                    ok = await ac.post(
                        url,
                        json=body,
                        headers={"X-Service-Key": settings.SERVICE_API_KEY},
                    )
                    assert ok.status_code == 200
                    assert ok.json() == {
                        "organization_id": 7,
                        "user_id": 5,
                        "chats_updated": 2,
                    }
                sync.assert_awaited_once()
                assert sync.call_args.args[1:] == (7, 5)
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_047_remove_organizer_endpoint_contract(self):
        from httpx import ASGITransport, AsyncClient

        from app.services.chat_service.config import settings
        from app.services.chat_service.db.session import get_db_session
        from app.services.chat_service.main import app

        app.dependency_overrides[get_db_session] = lambda: MagicMock()
        try:
            with patch(
                "app.services.chat_service.api.internal_router.remove_organizer_from_org_chats",
                new=AsyncMock(return_value=1),
            ) as sync:
                transport = ASGITransport(app=app)
                async with AsyncClient(
                    transport=transport, base_url="http://test"
                ) as ac:
                    ok = await ac.post(
                        "/internal/organizations/7/remove-organizer",
                        json={"user_id": 5},
                        headers={"X-Service-Key": settings.SERVICE_API_KEY},
                    )
                    assert ok.status_code == 200
                    assert ok.json()["chats_updated"] == 1
                sync.assert_awaited_once()
                assert sync.call_args.args[1:] == (7, 5)
        finally:
            app.dependency_overrides.clear()


if __name__ == "__main__":
    print("=" * 80)
    print("ЗАПУСК ТЕСТОВ CHAT SERVICE (pytest)")
    print("=" * 80)
    exit_code = pytest.main([__file__, "-v", "--tb=short", "-s"])
    print("\n" + "=" * 80)
    print(f"КОД ВЫХОДА: {exit_code}")
    print("=" * 80)
    sys.exit(exit_code)
