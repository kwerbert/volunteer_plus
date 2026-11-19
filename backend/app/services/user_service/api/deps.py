"""Зависимости для User Service"""

import logging
from typing import AsyncGenerator, Optional

import jwt
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.user_service.config import get_settings
from app.services.user_service.core.auth_service import AuthService
from app.services.user_service.core.service import UserService
from app.services.user_service.db.models import User, UserRoleEnum
from app.services.user_service.db.repository import UserRepository
from app.services.user_service.db.session import async_session_maker

logger = logging.getLogger(__name__)
security = HTTPBearer(auto_error=False)

settings = get_settings()


# === Database ===
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Зависимость для получения сессии БД"""
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()


# === User Authentication (JWT) ===
async def get_current_user_id(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> int:
    """Извлекает user_id из JWT access токена"""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Не предоставлены учётные данные",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Срок действия токена истёк",
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Невалидный токен",
        )

    # Проверка типа токена: refresh-токен не должен проходить как access
    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Невалидный тип токена",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("user_id")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Невалидный payload токена",
        )

    return user_id


# === Current User (объект из БД) === ✅ ДОБАВИТЬ
async def get_current_user(
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Загружает пользователя из БД: role/is_admin всегда актуальны,
    а не «зашиты» в JWT на момент логина."""
    user = await UserRepository(db).get_by_id(user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Пользователь не найден",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Пользователь деактивирован",
        )
    return user


# === Проверка привилегий === ✅ ДОБАВИТЬ
async def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Модератор: ортогональная привилегия is_admin, не роль."""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Требуются права администратора",
        )
    return current_user


async def require_organizer(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != UserRoleEnum.ORGANIZER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Требуются права организатора",
        )
    return current_user


# === Service-to-Service Authentication ===
async def verify_service_key(
    x_service_key: str = Header(None),
) -> bool:
    """Проверяет API ключ для межсервисного взаимодействия.
    Контракт (зафиксирован тестами 015/016/017):
      * ключ отсутствует          -> 401;
      * ключ есть, но неверный    -> 403;
      * ключ верный               -> True.
    """
    if x_service_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Service key отсутствует",
        )
    if x_service_key != settings.SERVICE_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Невалидный service key",
        )
    return True


# === Проверка владения ресурсом ===
async def require_same_user(
    user_id: int,
    current_user: User = Depends(get_current_user),  # ✅ ОБНОВИТЬ
) -> User:
    """Свой ресурс либо админ."""
    if current_user.id != user_id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет доступа к этому ресурсу",
        )
    return current_user


# === Зависимости для сервисов ===
async def get_user_service(
    db: AsyncSession = Depends(get_db),
) -> UserService:
    """Получение экземпляра UserService"""
    user_repo = UserRepository(db)
    auth_service = AuthService(user_repo)
    return UserService(user_repo, auth_service)


async def get_auth_service(
    db: AsyncSession = Depends(get_db),
) -> AuthService:
    """Получение экземпляра AuthService"""
    user_repo = UserRepository(db)
    return AuthService(user_repo)
