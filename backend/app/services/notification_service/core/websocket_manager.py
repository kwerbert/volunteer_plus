from fastapi import WebSocket
from typing import Dict, List
import asyncio
from app.services.notification_service.config import settings


class WebSocketManager:
    """
    Менеджер активных WebSocket-подключений.
    In-memory реализация (для масштабирования заменить на Redis pub/sub).
    """

    def __init__(self):
        # user_id -> list of WebSocket connections
        self.active_connections: Dict[int, List[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, user_id: int) -> None:
        """Принять новое подключение"""
        await websocket.accept()
        async with self._lock:
            if user_id not in self.active_connections:
                self.active_connections[user_id] = []
            self.active_connections[user_id].append(websocket)

    async def disconnect(self, websocket: WebSocket, user_id: int) -> None:
        """Удалить подключение"""
        async with self._lock:
            if user_id in self.active_connections:
                if websocket in self.active_connections[user_id]:
                    self.active_connections[user_id].remove(websocket)
                if not self.active_connections[user_id]:
                    del self.active_connections[user_id]

    async def send_to_user(self, message: dict, user_id: int) -> int:
        """
        Отправить сообщение всем активным подключениям пользователя.
        Returns: количество успешных отправок
        """
        success_count = 0
        async with self._lock:
            connections = self.active_connections.get(user_id, [])[:]

        for connection in connections:
            try:
                await asyncio.wait_for(
                    connection.send_json(message),
                    timeout=5.0
                )
                success_count += 1
            except (RuntimeError, asyncio.TimeoutError):
                # Connection closed or broken
                pass
        return success_count

    def is_user_online(self, user_id: int) -> bool:
        """Проверка: есть ли у пользователя активные WebSocket-подключения"""
        return user_id in self.active_connections and len(self.active_connections[user_id]) > 0

    async def broadcast_heartbeat(self) -> None:
        """Отправить heartbeat всем подключённым клиентам (для keep-alive)"""
        async with self._lock:
            all_connections = [
                conn
                for connections in self.active_connections.values()
                for conn in connections
            ]

        for conn in all_connections:
            try:
                await conn.send_json({"type": "heartbeat", "timestamp": asyncio.get_event_loop().time()})
            except:
                pass  # Игнорируем ошибки, подключение закроется само