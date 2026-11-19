"""Бизнес-логика User Service"""

import logging
from typing import Any, Dict, Optional

from app.services.user_service.core.auth_service import AuthService
from app.services.user_service.db.repository import UserRepository

logger = logging.getLogger(__name__)


class UserService:
    def __init__(self, user_repo: UserRepository, auth_service: AuthService):
        self.user_repo = user_repo
        self.auth_service = auth_service

    # === Профиль пользователя ===
    async def get_user_profile(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Полный профиль: пользователь + настройки + геолокация (вложенно)."""
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            return None

        settings = await self.user_repo.get_settings(user_id)
        location = await self.user_repo.get_location(user_id)

        return {
            "user": {
                "id": user.id,
                "email": user.email,
                "full_name": user.full_name,
                "phone": user.phone,
                "role": user.role,
                "is_active": user.is_active,
                "is_verified": user.is_verified,
                "is_admin": user.is_admin,
                "created_at": user.created_at,
                "last_login": user.last_login,
            },
            "settings": self._settings_to_dict(settings),
            "location": self._location_to_dict(location),
        }

    # === Геолокация ===
    async def update_user_location(
        self,
        user_id: int,
        latitude: float,
        longitude: float,
        accuracy: Optional[float] = None,
    ) -> Optional[Dict[str, Any]]:
        """Обновление геолокации пользователя"""
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            return None

        location = await self.user_repo.update_location(
            user_id=user_id,
            latitude=latitude,
            longitude=longitude,
            accuracy=accuracy,
        )
        return self._location_to_dict(location)

    async def get_user_location(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Получение геолокации пользователя"""
        location = await self.user_repo.get_location(user_id)
        return self._location_to_dict(location)

    # === Настройки пользователя ===
    async def get_user_settings(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Получение настроек пользователя"""
        settings = await self.user_repo.get_settings(user_id)
        return self._settings_to_dict(settings)

    # ЕДИНСТВЕННЫЙ метод обновления настроек (с main_organization_id)
    async def update_user_settings(
        self, user_id: int, update_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Обновление настроек пользователя"""
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            return None

        settings = await self.user_repo.update_settings(user_id, **update_data)
        return self._settings_to_dict(settings)

    # === Service-to-Service методы ===
    async def verify_user_exists(self, user_id: int) -> bool:
        """Проверка существования пользователя"""
        return await self.user_repo.exists(user_id)

    async def get_user_for_feed(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Получение данных пользователя для Feed Service"""
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            return None

        settings = await self.user_repo.get_settings(user_id)
        location = await self.user_repo.get_location(user_id)

        return {
            "user_id": user.id,
            "role": user.role,
            "location_lat": location.latitude if location else None,
            "location_lon": location.longitude if location else None,
            "settings": self._settings_to_dict(settings),
        }

    # === Вспомогательные методы ===
    def _settings_to_dict(self, settings) -> Optional[Dict[str, Any]]:
        """Конвертация настроек в словарь"""
        if not settings:
            return None
        return {
            "search_radius_km": settings.search_radius_km,
            "show_only_subscriptions": settings.show_only_subscriptions,
            "notifications_enabled": settings.notifications_enabled,
            "language": settings.language,
            "theme": settings.theme,
            "main_organization_id": settings.main_organization_id,
            "updated_at": settings.updated_at,
        }

    def _location_to_dict(self, location) -> Optional[Dict[str, Any]]:
        """Конвертация геолокации в словарь"""
        if not location:
            return None
        return {
            "latitude": location.latitude,
            "longitude": location.longitude,
            "accuracy": location.accuracy,
            "updated_at": location.updated_at,
        }
