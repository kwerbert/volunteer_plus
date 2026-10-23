"""
Тесты Notification Service (pytest версия).
Исправлены предупреждения IDE (Unresolved reference) путем перехода
на patch("module.attr").
"""
import pytest
import sys
import os
import tempfile
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

# ============================================================================
# Настройка путей
# ============================================================================
TEST_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(TEST_DIR, '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

def now_utc() -> datetime:
    return datetime.now(timezone.utc)

def make_notification(
    notification_id: int = 1,
    user_id: int = 1,
    title: str = "Test",
    body: str = "Body",
    notification_type=None,
    priority=None,
    data=None,
    sent_at: datetime | None = None,
):
    from app.services.notification_service.db.models import Notification
    from app.utils.notifications_enums import NotificationType, Priority
    n = Notification(
        id=notification_id, user_id=user_id, title=title, body=body,
        notification_type=notification_type or NotificationType.CHAT,
        priority=priority or Priority.NORMAL, data=data or {},
    )
    n.sent_at = sent_at or now_utc()
    return n

def make_token(user_id: int = 1, device_token: str = "device_abc", is_active: bool = True):
    from app.services.notification_service.db.models import NotificationToken
    return NotificationToken(
        id=1, user_id=user_id, device_token=device_token,
        platform="ANDROID", is_active=is_active,
    )

# ============================================================================
# FIXTURES
# ============================================================================
@pytest.fixture
def mock_session():
    session = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.flush = AsyncMock()
    session.execute = AsyncMock()
    session.scalar = AsyncMock(return_value=0)
    session.add = MagicMock()  # sync!
    return session

@pytest.fixture
def mock_repo():
    repo = AsyncMock()
    repo.get_token = AsyncMock(return_value=None)
    repo.get_active_tokens = AsyncMock(return_value=[])
    repo.create_token = AsyncMock()
    repo.delete_token = AsyncMock(return_value=True)
    repo.create_notification = AsyncMock()
    repo.get_notifications = AsyncMock(return_value=([], 0))
    repo.mark_as_read = AsyncMock(return_value=True)
    repo.delete_notification = AsyncMock(return_value=True)
    repo.get_notification = AsyncMock(return_value=None)
    repo.create_push_log = AsyncMock()
    repo.session = AsyncMock()
    repo.session.execute = AsyncMock()
    return repo

@pytest.fixture
def mock_firebase():
    fb = AsyncMock()
    fb.enabled = True
    fb.send_push_notification = AsyncMock()
    fb.validate_token = AsyncMock(return_value=True)
    return fb

@pytest.fixture
def mock_ws_manager():
    wm = AsyncMock()
    wm.is_user_online = MagicMock(return_value=False)  # sync!
    wm.send_to_user = AsyncMock(return_value=0)
    wm.connect = AsyncMock()
    wm.disconnect = AsyncMock()
    wm.broadcast_heartbeat = AsyncMock()
    return wm

@pytest.fixture
def clear_notification_settings_cache():
    try:
        from app.services.notification_service.config import get_settings
        get_settings.cache_clear()
    except (ImportError, AttributeError):
        pass
    yield
    try:
        from app.services.notification_service.config import get_settings
        get_settings.cache_clear()
    except (ImportError, AttributeError):
        pass

# ============================================================================
# ТЕСТЫ
# ============================================================================
class TestConfig:
    def test_001_config_settings(self, clear_notification_settings_cache):
        from app.services.notification_service.config import get_settings
        settings = get_settings()
        assert settings.SERVICE_NAME == "notification_service"
        assert settings.SERVICE_PORT == 8006

    def test_002_config_singleton(self):
        from app.services.notification_service.config import get_settings
        assert get_settings() is get_settings()

    def test_003_config_rejects_default_secrets_in_production(self):
        from app.services.notification_service.config import Settings
        with pytest.raises(ValueError, match="JWT_SECRET_KEY"):
            Settings(
                DEBUG=False,
                JWT_SECRET_KEY="dev-insecure-secret-key-change-in-production",
                SERVICE_API_KEY="real-key",
                _env_file=None,
            )

class TestSchemas:
    def test_005_create_notification_request(self):
        from app.services.notification_service.api.schemas import CreateNotificationRequest
        from app.utils.notifications_enums import NotificationType, Priority
        from pydantic import ValidationError
        req = CreateNotificationRequest(
            user_id=1, title="Hi", body="Body",
            notification_type=NotificationType.CHAT, priority=Priority.HIGH,
            data={"k": "v"},
        )
        assert req.user_id == 1
        with pytest.raises(ValidationError):
            CreateNotificationRequest(user_id=0, title="Hi", body="Body", notification_type=NotificationType.CHAT)

class TestModels:
    def test_008_notification_token_model(self):
        from app.services.notification_service.db.models import NotificationToken
        assert NotificationToken.__tablename__ == "notification_tokens"

class TestNotificationService:
    async def test_017_send_via_websocket_success(self, mock_repo, mock_firebase, mock_ws_manager):
        from app.services.notification_service.core.notification_service import NotificationService
        from app.utils.notifications_enums import NotificationType
        mock_repo.create_notification.return_value = make_notification()
        mock_ws_manager.is_user_online.return_value = True
        mock_ws_manager.send_to_user.return_value = 1
        service = NotificationService(mock_repo, mock_firebase, mock_ws_manager)
        result = await service.send_notification(user_id=1, title="Hi", body="B", notification_type=NotificationType.CHAT)
        assert result["delivered_via"] == "websocket"

    async def test_019_no_tokens(self, mock_repo, mock_firebase, mock_ws_manager):
        from app.services.notification_service.core.notification_service import NotificationService
        from app.utils.notifications_enums import NotificationType
        mock_repo.create_notification.return_value = make_notification()
        mock_repo.get_active_tokens.return_value = []
        service = NotificationService(mock_repo, mock_firebase, mock_ws_manager)
        result = await service.send_notification(user_id=1, title="Hi", body="B", notification_type=NotificationType.SYSTEM)
        assert result["error"] == "NO_TOKENS"

    async def test_021_unregistered_token_is_deactivated(self, mock_repo, mock_firebase, mock_ws_manager):
        from app.services.notification_service.core.notification_service import NotificationService
        from app.utils.notifications_enums import NotificationType
        mock_repo.create_notification.return_value = make_notification()
        mock_repo.get_active_tokens.return_value = [make_token(device_token="dead")]
        mock_firebase.send_push_notification.return_value = {"success": False, "error": "UNREGISTERED", "message": "Token not registered"}
        service = NotificationService(mock_repo, mock_firebase, mock_ws_manager)
        result = await service.send_notification(user_id=1, title="Hi", body="B", notification_type=NotificationType.CHAT)
        assert result["push_results"][0]["error"] == "UNREGISTERED"
        assert mock_repo.create_push_log.call_args.kwargs["status"] == "UNREGISTERED"

# ============================================================================
# ИСПРАВЛЕНО: FirebaseProvider (Заменен patch.object на patch("..."))
# ============================================================================
class TestFirebaseProvider:
    @pytest.mark.asyncio
    async def test_036_enabled_send_success(self):
        with tempfile.NamedTemporaryFile() as tmp:
            # Использование строкового пути избавляет IDE от попыток найти эти атрибуты
            with patch("app.services.notification_service.providers.firebase_provider.initialize_app"), \
                 patch("app.services.notification_service.providers.firebase_provider.credentials") as creds, \
                 patch("app.services.notification_service.providers.firebase_provider.messaging") as messaging:

                creds.Certificate = MagicMock()
                messaging.Message = MagicMock()
                messaging.Notification = MagicMock()
                messaging.AndroidConfig = MagicMock()
                messaging.AndroidNotification = MagicMock()
                messaging.APNSConfig = MagicMock()
                messaging.APNSPayload = MagicMock()
                messaging.Aps = MagicMock()
                messaging.send = MagicMock(return_value="msg-123")

                from app.services.notification_service.providers.firebase_provider import FirebaseProvider
                FirebaseProvider._initialized = False
                provider = FirebaseProvider(service_account_path=tmp.name)

                result = await provider.send_push_notification(
                    device_token="tok", title="t", body="b", data={"k": "v"},
                )
            assert result["success"] is True
            assert result["message_id"] == "msg-123"

    @pytest.mark.asyncio
    async def test_037_enabled_unregistered_maps_to_unregistered(self):
        class MockUnregisteredError(Exception):
            pass

        with tempfile.NamedTemporaryFile() as tmp:
            with patch("app.services.notification_service.providers.firebase_provider.initialize_app"), \
                 patch("app.services.notification_service.providers.firebase_provider.credentials") as creds, \
                 patch("app.services.notification_service.providers.firebase_provider.messaging") as messaging:

                creds.Certificate = MagicMock()
                messaging.Message = MagicMock(return_value=MagicMock())
                messaging.Notification = MagicMock()
                messaging.AndroidConfig = MagicMock()
                messaging.AndroidNotification = MagicMock()
                messaging.APNSConfig = MagicMock()
                messaging.APNSPayload = MagicMock()
                messaging.Aps = MagicMock()

                # ИСПРАВЛЕНО: Сначала задаем класс исключения, потом вешаем его на send
                messaging.UnregisteredError = MockUnregisteredError
                messaging.InvalidArgumentError = type("InvalidArgumentError", (Exception,), {})
                messaging.send = MagicMock(side_effect=MockUnregisteredError("gone"))

                from app.services.notification_service.providers.firebase_provider import FirebaseProvider
                FirebaseProvider._initialized = False
                provider = FirebaseProvider(service_account_path=tmp.name)

                result = await provider.send_push_notification(
                    device_token="tok", title="t", body="b", data={},
                )
            assert result["success"] is False
            assert result["error"] == "UNREGISTERED"

# ============================================================================
# ИСПРАВЛЕНО: Router Helpers (Заменен patch.object на patch("..."))
# ============================================================================
class TestRouterHelpers:
    def test_038_verify_service_key_valid(self):
        from app.services.notification_service.api import router as rmod

        # patch("путь.к.модулю.атрибут") убирает ошибку "Unresolved reference 'settings'"
        with patch("app.services.notification_service.api.router.settings") as s:
            s.SERVICE_API_KEY = "good-key"
            assert rmod.verify_service_key(x_service_key="good-key") is None

    def test_039_verify_service_key_invalid(self):
        from fastapi import HTTPException
        from app.services.notification_service.api import router as rmod
        with patch("app.services.notification_service.api.router.settings") as s:
            s.SERVICE_API_KEY = "good-key"
            with pytest.raises(HTTPException) as exc:
                rmod.verify_service_key(x_service_key="bad")
            assert exc.value.status_code == 403

# ============================================================================
# ЗАПУСК
# ============================================================================
if __name__ == "__main__":
    exit_code = pytest.main([__file__, "-v", "--tb=short", "-s"])
    sys.exit(exit_code)