from typing import Dict, List
from fastapi import WebSocket
import json
import logging

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        # chat_id -> list of websockets
        self.active_connections: Dict[int, List[WebSocket]] = {}

    async def connect(self, chat_id: int, websocket: WebSocket):
        await websocket.accept()
        if chat_id not in self.active_connections:
            self.active_connections[chat_id] = []
        self.active_connections[chat_id].append(websocket)
        logger.info(f"WebSocket connected to chat {chat_id}, total: {len(self.active_connections[chat_id])}")

    def disconnect(self, chat_id: int, websocket: WebSocket):
        if chat_id in self.active_connections:
            self.active_connections[chat_id].remove(websocket)
            if not self.active_connections[chat_id]:
                del self.active_connections[chat_id]
        logger.info(f"WebSocket disconnected from chat {chat_id}")

    async def broadcast(self, chat_id: int, message: dict):
        if chat_id not in self.active_connections:
            return
        message_json = json.dumps(message)
        for connection in self.active_connections[chat_id]:
            try:
                await connection.send_text(message_json)
            except Exception as e:
                logger.error(f"Failed to send message to websocket: {e}")

manager = ConnectionManager()