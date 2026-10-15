"""Сервис аутентификации: регистрация, логин, управление токенами"""
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
import logging
from app.services.user_service.db.repository import UserRepository
from app.services.user_service.core.security import (
    hash_password, verify_password,
    create_access_token, create_refresh_token, decode_token,
    hash_token_for_blacklist
)
from app.services.user_service.config import settings

logger = logging.getLogger(__name__)


class AuthService:
    """Сервис для операций аутентификации"""

    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo

    async def register(
            self,
            email: str,
            password: str,
            full_name: Optional[str] = None,
            phone: Optional[str] = None
    ) -> Tuple[dict, dict]:
        """
        Регистрация нового пользователя
        Returns:
            Tuple[user_data, tokens]
        """
        # Проверка уникальности email
        existing = await self.user_repo.get_by_email(email)
        if existing:
            raise ValueError("Пользователь с таким email уже существует")

        # Хеширование пароля и создание пользователя
        password_hash = hash_password(password)
        user = await self.user_repo.create(
            email=email,
            password_hash=password_hash,
            full_name=full_name,
            phone=phone
        )

        # Создание настроек по умолчанию
        await self.user_repo.create_settings(user.id)

        # Генерация токенов
        tokens = await self._generate_tokens(user)

        # Обновление last_login
        await self.user_repo.update_last_login(user.id)

        logger.info(f"User registered: {user.email} (id={user.id})")
        return self._user_to_dict(user), tokens

    async def login(self, email: str, password: str) -> Tuple[dict, dict]:
        """
        Аутентификация пользователя
        Returns:
            Tuple[user_data, tokens]
        """
        user = await self.user_repo.get_by_email(email)
        if not user or not user.is_active:
            raise ValueError("Неверный email или пароль")

        if not verify_password(password, user.password_hash):
            raise ValueError("Неверный email или пароль")

        # Генерация токенов
        tokens = await self._generate_tokens(user)

        # Обновление last_login
        await self.user_repo.update_last_login(user.id)

        logger.info(f"User logged in: {user.email} (id={user.id})")
        return self._user_to_dict(user), tokens

    async def refresh_tokens(self, refresh_token: str) -> dict:
        """
        Обновление access токена по refresh токену
        """
        # Проверка токена в blacklist
        token_hash = hash_token_for_blacklist(refresh_token)
        if await self.user_repo.is_token_revoked(token_hash):
            raise ValueError("Токен отозван")

        # Декодирование refresh токена
        payload = decode_token(refresh_token, token_type="refresh")
        if not payload:
            raise ValueError("Невалидный refresh токен")

        user_id = payload.get("user_id")
        if not user_id:
            raise ValueError("Невалидный refresh токен")

        user = await self.user_repo.get_by_id(user_id)
        if not user or not user.is_active:
            raise ValueError("Пользователь не найден или неактивен")

        # Генерация новых токенов
        return await self._generate_tokens(user)

    async def logout(self, refresh_token: str) -> bool:
        """
        Выход из системы: добавление refresh токена в blacklist
        """
        token_hash = hash_token_for_blacklist(refresh_token)
        return await self.user_repo.revoke_token(token_hash)

    async def _generate_tokens(self, user) -> dict:
        """Генерация пары access/refresh токенов"""
        token_data = {
            "user_id": user.id,
            "email": user.email,
            "role": user.role.value if hasattr(user.role, 'value') else user.role
        }
        access_token = create_access_token(token_data)
        refresh_token = create_refresh_token(token_data)

        # Сохранение хеша refresh токена
        token_hash = hash_token_for_blacklist(refresh_token)
        expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        await self.user_repo.create_refresh_token(user.id, token_hash, expires_at)

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            "user_id": user.id  # ДОБАВЛЕНО: user_id в ответе
        }

    def _user_to_dict(self, user) -> dict:
        """Конвертация модели пользователя в словарь (без чувствительных данных)"""
        return {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "phone": user.phone,
            "role": user.role.value if hasattr(user.role, 'value') else user.role,
            "is_active": user.is_active,
            "is_verified": user.is_verified,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "last_login": user.last_login.isoformat() if user.last_login else None
        }