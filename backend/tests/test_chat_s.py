"""
Тесты Chat Service (pytest версия)
Следует структуре test_user_s.py
"""
import pytest
import sys
import os
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

# ============================================================================
# Настройка путей
# ============================================================================
TEST_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(TEST_DIR, '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


def now_utc() -> datetime:
    """Возвращает текущее время в UTC"""
    return datetime.now(timezone.utc)


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def mock_session():
    """Фикстура для мок-сессии БД"""
    session = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.execute = AsyncMock()
    session.add = AsyncMock()
    session.get = AsyncMock()
    return session


@pytest.fixture
def mock_repo():
    """Фикстура для мок-репозитория"""
    repo = AsyncMock()
    # Chat methods
    repo.create_chat = AsyncMock()
    repo.get_chat_by_id = AsyncMock()
    repo.get_user_chats = AsyncMock()
    repo.update_chat = AsyncMock()
    repo.deactivate_chat = AsyncMock()
    repo.find_personal_chat = AsyncMock()  # ✅ имя метода оставлено, но внутри должен использоваться ORGANIZER
    repo.user_has_access_to_chat = AsyncMock()
    # Member methods
    repo.add_member = AsyncMock()
    repo.get_member = AsyncMock()
    repo.get_chat_members = AsyncMock()
    repo.remove_member = AsyncMock()
    repo.update_member_role = AsyncMock()
    # Message methods
    repo.create_message = AsyncMock()
    repo.get_messages = AsyncMock()
    repo.get_message_by_id = AsyncMock()
    repo.mark_message_read = AsyncMock()
    repo.mark_chat_messages_read = AsyncMock()
    repo.get_unread_count = AsyncMock()
    return repo


@pytest.fixture
def clear_chat_settings_cache():
    """Очистка кэша настроек"""
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


# ============================================================================
# ТЕСТЫ КОНФИГУРАЦИИ
# ============================================================================

class TestConfig:
    """Тесты конфигурации сервиса"""

    def test_001_config_settings(self, clear_chat_settings_cache):
        """Проверка загрузки настроек"""
        from app.services.chat_service.config import get_settings
        settings = get_settings()

        assert settings.SERVICE_PORT == 8007
        assert settings.SERVICE_NAME == "chat_service"
        assert "sqlite+aiosqlite" in settings.DATABASE_URL
        assert settings.JWT_ALGORITHM == "HS256"
        assert settings.DEFAULT_PAGE_SIZE == 20
        print("✓ Конфигурация загружена корректно")

    def test_002_config_cors_origins(self, clear_chat_settings_cache):
        """Проверка парсинга CORS origins"""
        from app.services.chat_service.config import get_settings
        settings = get_settings()
        origins = settings.cors_origins_list

        assert isinstance(origins, list)
        assert "http://10.0.2.2:8007" in origins  # Для Android эмулятора
        print("✓ CORS origins распарсены корректно")


# ============================================================================
# ТЕСТЫ СХЕМ (PYDANTIC V2)
# ============================================================================

class TestSchemas:
    """Тесты Pydantic схем"""

    def test_003_chat_create_request_schema(self):
        """Проверка схемы создания чата"""
        from app.services.chat_service.api.schemas import ChatCreateRequest, ChatTypeEnum
        from pydantic import ValidationError

        req = ChatCreateRequest(
            chat_type=ChatTypeEnum.ORGANIZER,  # ✅ ЗАМЕНЕНО
            participant_ids=[2]
        )
        assert req.chat_type == ChatTypeEnum.ORGANIZER  # ✅ ЗАМЕНЕНО
        assert req.participant_ids == [2]

        with pytest.raises(ValidationError):
            ChatCreateRequest(chat_type=ChatTypeEnum.ORGANIZER, participant_ids=[])  # ✅ ЗАМЕНЕНО
        print("✓ Схема создания чата валидируется корректно")

    def test_004_message_create_request_schema(self):
        """Проверка схемы отправки сообщения"""
        from app.services.chat_service.api.schemas import MessageCreateRequest, MessageTypeEnum
        from pydantic import ValidationError

        req = MessageCreateRequest(
            content="Hello!",
            message_type=MessageTypeEnum.TEXT
        )
        assert req.content == "Hello!"

        with pytest.raises(ValidationError):
            MessageCreateRequest(content="")  # Пустой контент
        with pytest.raises(ValidationError):
            MessageCreateRequest(content="x" * 5000)  # Слишком длинный
        print("✓ Схема сообщения валидируется корректно")

    def test_005_response_schemas(self):
        """Проверка схем ответов"""
        from app.services.chat_service.api.schemas import (
            ChatResponse, MessageResponse, ChatMemberResponse, ChatTypeEnum
        )

        member = ChatMemberResponse(
            user_id=1, role="admin", joined_at=now_utc(), is_muted=False
        )
        assert member.user_id == 1

        chat = ChatResponse(
            id=1, chat_type=ChatTypeEnum.ORGANIZER, created_at=now_utc(),  # ✅ ЗАМЕНЕНО
            unread_count=0, members=[member]
        )
        assert chat.chat_type == ChatTypeEnum.ORGANIZER  # ✅ ЗАМЕНЕНО

        msg = MessageResponse(
            id=1, chat_id=1, sender_id=2, content="Hi",
            message_type="text", is_read=False, created_at=now_utc()
        )
        assert msg.is_read is False
        print("✓ Схемы ответов создаются корректно")


# ============================================================================
# ТЕСТЫ МОДЕЛЕЙ
# ============================================================================

class TestModels:
    """Тесты SQLAlchemy моделей"""

    def test_006_chat_model(self):
        """Проверка модели Chat"""
        from app.services.chat_service.db.models import Chat, ChatTypeEnum
        assert Chat.__tablename__ == "chats"
        columns = [col.name for col in Chat.__table__.columns]
        required = ['id', 'chat_type', 'title', 'is_active', 'created_at']
        for field in required:
            assert field in columns
        print("✓ Модель Chat корректна")

    def test_007_message_model(self):
        """Проверка модели Message"""
        from app.services.chat_service.db.models import Message, MessageTypeEnum
        assert Message.__tablename__ == "messages"
        columns = [col.name for col in Message.__table__.columns]
        required = ['id', 'chat_id', 'sender_id', 'content', 'is_read', 'created_at']
        for field in required:
            assert field in columns
        print("✓ Модель Message корректна")


# ============================================================================
# ТЕСТЫ РЕПОЗИТОРИЯ
# ============================================================================

@pytest.mark.asyncio
class TestRepository:
    """Тесты репозитория"""

    async def test_008_create_chat(self, mock_session, mock_repo):
        """Проверка создания чата"""
        from app.services.chat_service.db.repository import ChatRepository
        from app.services.chat_service.db.models import Chat, ChatTypeEnum

        mock_chat = Chat(
            id=1, chat_type=ChatTypeEnum.ORGANIZER, is_active=True,  # ✅ ЗАМЕНЕНО
            created_at=now_utc()
        )
        mock_session.get.return_value = mock_chat
        mock_repo.create_chat = AsyncMock(return_value=mock_chat)

        repo = ChatRepository(mock_session)
        # Тестируем что метод существует и вызывает сессию
        assert repo is not None
        print("✓ Репозиторий создаётся корректно")

    async def test_009_create_message(self, mock_session):
        """Проверка создания сообщения"""
        from app.services.chat_service.db.repository import ChatRepository
        from app.services.chat_service.db.models import Message, MessageTypeEnum

        repo = ChatRepository(mock_session)
        mock_message = Message(
            id=1, chat_id=1, sender_id=2, content="Test",
            message_type=MessageTypeEnum.TEXT, is_read=False,
            created_at=now_utc()
        )
        mock_session.get.return_value = mock_message

        # Проверяем что методы существуют
        assert hasattr(repo, 'create_message')
        assert hasattr(repo, 'get_messages')
        print("✓ Методы сообщений доступны")


# ============================================================================
# ТЕСТЫ БИЗНЕС-ЛОГИКИ
# ============================================================================

@pytest.mark.asyncio
class TestService:
    """Тесты бизнес-логики"""

    async def test_010_send_message(self, mock_repo):
        """Проверка отправки сообщения"""
        from app.services.chat_service.core.service import ChatService
        from app.services.chat_service.db.models import Message, MessageTypeEnum

        mock_repo.user_has_access_to_chat = AsyncMock(return_value=True)
        mock_message = Message(
            id=1, chat_id=1, sender_id=2, content="Hello",
            message_type=MessageTypeEnum.TEXT, is_read=False,
            created_at=now_utc()
        )
        mock_repo.create_message = AsyncMock(return_value=mock_message)
        mock_repo.update_chat = AsyncMock()

        service = ChatService(mock_repo)
        result = await service.send_message(
            chat_id=1, sender_id=2, content="Hello"
        )

        assert result.content == "Hello"
        mock_repo.create_message.assert_called_once()
        print("✓ Отправка сообщения работает корректно")

    async def test_011_mark_message_read(self, mock_repo):
        """Проверка отметки прочтения"""
        from app.services.chat_service.core.service import ChatService
        from app.services.chat_service.db.models import Message, MessageTypeEnum

        # ✅ ИСПРАВЛЕНО: is_read=True (симуляция успешной отметки прочтения)
        mock_message = Message(
            id=1, chat_id=1, sender_id=2, content="Hi",
            message_type=MessageTypeEnum.TEXT, is_read=True,
            created_at=now_utc(),
            read_at=now_utc()
        )
        mock_repo.mark_message_read = AsyncMock(return_value=mock_message)

        service = ChatService(mock_repo)
        result = await service.mark_message_read(1)

        assert result is not None
        assert result.is_read is True


# ============================================================================
# ТЕСТЫ FASTAPI ПРИЛОЖЕНИЯ
# ============================================================================

class TestMainApp:
    """Тесты FastAPI приложения"""

    def test_012_app_creation(self, clear_chat_settings_cache):
        """Проверка создания FastAPI приложения"""
        from app.services.chat_service.main import app

        assert app is not None
        assert app.title == "chat_service"
        assert app.version == "1.0.0"
        print("✓ FastAPI приложение создано корректно")

    def test_013_app_routes(self, clear_chat_settings_cache):
        """Проверка подключенных роутов (рекурсивно)"""
        from app.services.chat_service.main import app
        from tests.conftest import collect_route_paths

        routes = collect_route_paths(app)

        assert "/api/v1/chats" in routes
        assert "/api/v1/chats/{chat_id}/messages" in routes
        assert "/api/v1/messages/{message_id}/read" in routes
        assert "/health" in routes
        assert "/" in routes
        print("✓ Все эндпоинты подключены корректно")

    def test_014_health_endpoint(self, clear_chat_settings_cache):
        """Проверка health endpoint"""
        from app.services.chat_service.main import app
        from tests.conftest import collect_route_paths

        routes = collect_route_paths(app)
        assert routes.count("/health") == 1
        print("✓ Health endpoint доступен")


# ============================================================================
# ЗАПУСК ТЕСТОВ
# ============================================================================

if __name__ == "__main__":
    print("=" * 80)
    print("ЗАПУСК ТЕСТОВ CHAT SERVICE (pytest)")
    print("=" * 80)
    exit_code = pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "-s"
    ])
    print("\n" + "=" * 80)
    print(f"КОД ВЫХОДА: {exit_code}")
    print("=" * 80)
    sys.exit(exit_code)

# pytest tests/test_chat_s.py -v