from fastapi import WebSocket, WebSocketDisconnect, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.chat_service.db.session import get_db_session
from app.services.chat_service.db.repository import ChatRepository
from app.services.chat_service.core.connection_manager import manager
from app.services.chat_service.core.security import verify_websocket_token
from typing import Optional
import json
import logging

logger = logging.getLogger(__name__)

async def get_websocket_user(
    websocket: WebSocket,
    token: Optional[str] = None
) -> int:
    """Извлекает user_id из query-параметра token"""
    if token is None:
        # Пробуем взять из query параметра
        token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Missing token")
        raise WebSocketDisconnect()
    user_id = verify_websocket_token(token)
    if user_id is None:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid token")
        raise WebSocketDisconnect()
    return user_id

async def websocket_endpoint(
    websocket: WebSocket,
    chat_id: int,
    db: AsyncSession = Depends(get_db_session)
):
    # Аутентификация
    user_id = await get_websocket_user(websocket)
    # Проверка доступа
    repo = ChatRepository(db)
    has_access = await repo.user_has_access_to_chat(chat_id, user_id)
    if not has_access:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Access denied")
        return
    await manager.connect(chat_id, websocket)
    try:
        while True:
            # Ждём сообщения от клиента (можно игнорировать или обрабатывать ping)
            data = await websocket.receive_text()
            # Можно добавить обработку клиентских сообщений (например, "ping")
            # Пока просто ничего не делаем
    except WebSocketDisconnect:
        manager.disconnect(chat_id, websocket)
    except Exception as e:
        logger.exception(f"WebSocket error for chat {chat_id}, user {user_id}: {e}")
        manager.disconnect(chat_id, websocket)