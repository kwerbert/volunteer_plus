from typing import Optional, AsyncGenerator
from fastapi import Depends, HTTPException, status, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
import jwt
import logging
from app.services.user_service.db.session import get_db_session
from app.services.user_service.config import settings
from app.services.user_service.db.repository import UserRepository
from app.services.user_service.core.auth_service import AuthService
from app.services.user_service.core.service import UserService

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
    """Извлекает user_id из JWT access токена"""
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
    """Проверяет API ключ для межсервисного взаимодействия"""
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

# === Проверка владения ресурсом ===
async def check_user_ownership(
        user_id: int,
        current_user_id: int = Depends(get_current_user_id)
) -> bool:
    """Проверяет что пользователь имеет доступ к ресурсу"""
    if user_id != current_user_id:
        # TOD0: Добавить проверку на admin роль
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ запрещён"
        )
    return True

# === Зависимости для сервисов ===
async def get_user_service(
        db: AsyncSession = Depends(get_db)
) -> UserService:
    """Получение экземпляра UserService"""
    user_repo = UserRepository(db)
    auth_service = AuthService(user_repo)
    return UserService(user_repo, auth_service)


async def get_auth_service(
        db: AsyncSession = Depends(get_db)
) -> AuthService:
    """Получение экземпляра AuthService"""
    user_repo = UserRepository(db)
    return AuthService(user_repo)