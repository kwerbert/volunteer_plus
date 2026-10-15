"""Зависимости для Chat Service"""
from typing import Optional, AsyncGenerator
from fastapi import Depends, HTTPException, status, Header, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
import jwt
import logging

from app.services.chat_service.db.session import get_db_session
from app.services.chat_service.config import settings

logger = logging.getLogger(__name__)
security = HTTPBearer(auto_error=False)


# === Database ===

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Зависимость для получения сессии БД"""
    async for session in get_db_session():
        yield session


# === User Authentication (JWT) ===

async def get_current_user_id(
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
        db: AsyncSession = Depends(get_db)
) -> int:
    """
    Извлекает user_id из JWT access токена
    Возвращает 401 если токен отсутствует/невалиден
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Требуется аутентификация",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials

    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )

        if payload.get("type") != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Невалидный тип токена",
            )

        user_id = payload.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Токен не содержит user_id",
            )

        return int(user_id)

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Токен истёк",
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Невалидный токен",
        )


# === Service-to-Service Authentication ===

async def verify_service_key(
        x_service_key: Optional[str] = Header(None, alias="X-Service-Key")
) -> bool:
    """
    Проверяет API ключ для межсервисного взаимодействия
    """
    if not x_service_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Отсутствует X-Service-Key заголовок"
        )

    if x_service_key != settings.SERVICE_API_KEY:
        logger.warning(f"Invalid service key attempt: {x_service_key[:10]}...")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Неверный API ключ сервиса"
        )
    return True


# === Chat Access Authorization ===

async def check_chat_access(
        chat_id: int,
        user_id: int = Depends(get_current_user_id),
        db: AsyncSession = Depends(get_db)
) -> bool:
    """
    Проверяет что пользователь имеет доступ к чату
    """
    from app.services.chat_service.db.repository import ChatRepository

    repo = ChatRepository(db)
    if not await repo.user_has_access_to_chat(chat_id, user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ к чату запрещён"
        )
    return True