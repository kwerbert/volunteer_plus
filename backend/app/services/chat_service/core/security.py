import jwt
from jwt.exceptions import InvalidTokenError
from app.services.chat_service.config import settings

def verify_websocket_token(token: str) -> int | None:
    """
    Декодирует JWT access token и возвращает user_id.
    Использует тот же секрет, что и сервис аутентификации.
    """
    try:
        # Предполагаем, что сервис аутентификации использует симметричный HS256
        # Секрет должен быть общим – вынести в настройки
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=["HS256"])
        user_id = payload.get("user_id")
        if user_id is not None:
            return int(user_id)
        return None
    except InvalidTokenError:
        return None