from fastapi import APIRouter, Depends, HTTPException, status, WebSocket, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from sqlalchemy import func
from fastapi import Header  # для verify_service_key
from datetime import datetime, timezone
import asyncio

from app.services.notification_service.config import settings, NotificationType, Priority
from app.services.notification_service.api.schemas import (
    CreateNotificationRequest, RegisterTokenRequest,
    NotificationResponse, NotificationsListResponse,
    RegisterTokenResponse, SendNotificationResponse, HealthResponse
)
from app.services.notification_service.db.session import get_db_session
from app.services.notification_service.db.repository import NotificationRepository
from app.services.notification_service.core.websocket_manager import (
    WebSocketManager,
    get_ws_manager,
)
from app.services.notification_service.core.notification_service import NotificationService
from app.services.notification_service.providers.firebase_provider import FirebaseProvider
from app.services.notification_service.utils.token_validator import validate_websocket_token, validate_jwt_token

router = APIRouter(prefix="/api/v1", tags=["notifications"])


# === Dependencies ===

def get_notification_service(
        db: AsyncSession = Depends(get_db_session),
        firebase: FirebaseProvider = Depends(lambda: FirebaseProvider(settings.FIREBASE_CREDENTIALS_PATH)),
        ws_manager: WebSocketManager = Depends(get_ws_manager),
) -> NotificationService:
    repo = NotificationRepository(db)
    return NotificationService(repo, firebase, ws_manager)


def verify_service_key(x_service_key: str = Header(None)) -> None:
    """Проверка service-to-service авторизации"""
    if x_service_key != settings.SERVICE_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid service key"
        )

def _require_same_user(payload: dict, user_id: int) -> None:
    """Проверяет, что JWT принадлежит указанному пользователю.
    В JWT sub хранится строкой (см. user_service.core.security.create_access_token)."""
    sub = payload.get("sub")
    if sub is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Invalid token payload")
    try:
        token_user_id = int(sub)
    except (TypeError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Invalid token subject")
    if token_user_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Access denied")

# === REST Endpoints ===

@router.post("/notifications", response_model=SendNotificationResponse, status_code=status.HTTP_201_CREATED)
async def create_notification(
        request: CreateNotificationRequest,
        service: NotificationService = Depends(get_notification_service),
        _=Depends(verify_service_key)  # Только внутренние сервисы!
):
    """
    Отправка уведомления пользователю (service-to-service).
    Требует заголовок: X-Service-Key
    """
    result = await service.send_notification(
        user_id=request.user_id,
        title=request.title,
        body=request.body,
        notification_type=request.notification_type,
        priority=request.priority,
        data=request.data
    )

    if not result["success"] and result.get("error") == "NO_TOKENS":
        # Это не ошибка — пользователь просто офлайн и без токенов
        # Уведомление сохранено в БД, будет доставлено при следующем входе
        pass

    return SendNotificationResponse(**result)


@router.get("/users/{user_id}/notifications", response_model=NotificationsListResponse)
async def get_user_notifications(
        user_id: int,
        page: int = Query(1, ge=1),
        page_size: int = Query(20, ge=1, le=100),
        is_read: Optional[bool] = None,
        notification_type: Optional[NotificationType] = None,
        service: NotificationService = Depends(get_notification_service),
        token: str = Query(...)  # JWT для проверки прав
):
    """Получение списка уведомлений пользователя"""
    # Валидация: пользователь может смотреть только свои уведомления
    payload = validate_jwt_token(token)
    _require_same_user(payload, user_id)

    items, total = await service.repo.get_notifications(
        user_id=user_id,
        page=page,
        page_size=page_size,
        is_read=is_read,
        notification_type=notification_type
    )

    return NotificationsListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size
    )


@router.put("/notifications/{notification_id}/read", status_code=status.HTTP_204_NO_CONTENT)
async def mark_notification_read(
        notification_id: int,
        service: NotificationService = Depends(get_notification_service),
        token: str = Query(...)
):
    """Отметить уведомление как прочитанное"""
    payload = validate_jwt_token(token)
    notification = await service.repo.get_notification(notification_id)
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    _require_same_user(payload, notification.user_id)
    await service.repo.mark_as_read(notification_id)


@router.delete("/notifications/{notification_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_notification(
        notification_id: int,
        service: NotificationService = Depends(get_notification_service),
        token: str = Query(...)
):
    """Удалить уведомление"""
    payload = validate_jwt_token(token)
    _require_same_user(payload, int(payload["sub"]))  # sanity check sub — int
    deleted = await service.repo.delete_notification(
        notification_id, user_id=int(payload["sub"])
    )
    if not deleted:
        raise HTTPException(status_code=404, detail="Notification not found")


@router.post("/tokens/register", response_model=RegisterTokenResponse)
async def register_token(
        request: RegisterTokenRequest,
        service: NotificationService = Depends(get_notification_service)
):
    """Регистрация push-токена устройства"""
    result = await service.register_token(
        user_id=request.user_id,
        device_token=request.device_token,
        platform=request.platform.value,
        app_version=request.app_version
    )
    return RegisterTokenResponse(**result)


@router.delete("/tokens/{device_token}", status_code=status.HTTP_204_NO_CONTENT)
async def unregister_token(
        device_token: str,
        service: NotificationService = Depends(get_notification_service),
        token: str = Query(...)
):
    """Удаление токена (при логауте)"""
    payload = validate_jwt_token(token)
    db_token = await service.repo.get_token(device_token)
    if not db_token:
        raise HTTPException(status_code=404, detail="Token not found")
    _require_same_user(payload, db_token.user_id)
    await service.unregister_token(device_token)


# === WebSocket Endpoint ===

@router.websocket("/ws/notifications/{user_id}")
async def websocket_endpoint(
        websocket: WebSocket,
        user_id: int,
        ws_manager: WebSocketManager = Depends(get_ws_manager),
):
    """
    WebSocket для real-time уведомлений.
    Подключение: /ws/notifications/{user_id}?token=JWT_ACCESS_TOKEN
    """
    # Валидация токена
    authenticated_user_id = await validate_websocket_token(websocket)
    if authenticated_user_id != user_id:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    # Подключаем
    await ws_manager.connect(websocket, user_id)

    try:
        # Keep-alive: отправляем heartbeat периодически
        while True:
            # Ждём сообщения от клиента (если нужно)
            data = await asyncio.wait_for(websocket.receive_text(), timeout=settings.WS_HEARTBEAT_INTERVAL)
            # Можно обрабатывать команды от клиента, например "ack"
            if data:
                await websocket.send_json({"type": "ack", "received": data})

    except asyncio.TimeoutError:
        # Отправляем heartbeat и продолжаем
        await ws_manager.send_to_user({"type": "heartbeat"}, user_id)
    except:
        # Connection closed
        pass
    finally:
        await ws_manager.disconnect(websocket, user_id)