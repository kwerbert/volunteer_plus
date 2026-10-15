"""Бизнес-логика User Service"""
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
import logging
from app.services.user_service.db.models import UserRoleEnum
from app.services.user_service.db.repository import UserRepository
from app.services.user_service.core.auth_service import AuthService

logger = logging.getLogger(__name__)

class UserService:
    def __init__(self, user_repo: UserRepository, auth_service: AuthService):
        self.user_repo = user_repo
        self.auth_service = auth_service

    # === Профиль пользователя ===
    async def get_user_profile(self, user_id: int) -> Optional[Dict[str, Any]]:
        user = await self.user_repo.get_by_id(user_id)
        if not user or not user.is_active:
            return None
        settings = await self.user_repo.get_settings(user_id)
        location = await self.user_repo.get_location(user_id)
        return {
            "user": {
                "id": user.id,
                "email": user.email,
                "full_name": user.full_name,
                "phone": user.phone,
                "role": user.role.value if hasattr(user.role, 'value') else user.role,
                "is_active": user.is_active,
                "is_verified": user.is_verified,
                "created_at": user.created_at.isoformat() if user.created_at else None,
                "last_login": user.last_login.isoformat() if user.last_login else None
            },
            "settings": self._settings_to_dict(settings) if settings else None,
            "location": self._location_to_dict(location) if location else None
        }

    async def update_user_profile(
            self, user_id: int, full_name: Optional[str] = None, phone: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        update_data = {}
        if full_name is not None:
            update_data["full_name"] = full_name
        if phone is not None:
            update_data["phone"] = phone
        if not update_data:
            return await self.get_user_profile(user_id)

        user = await self.user_repo.update(user_id, **update_data)
        if not user:
            return None

        # Полный набор полей под UserResponse
        return {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "phone": user.phone,
            "role": user.role.value if hasattr(user.role, "value") else user.role,
            "is_active": user.is_active,
            "is_verified": user.is_verified,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "last_login": user.last_login.isoformat() if user.last_login else None,
        }

    # === Геолокация ===
    async def update_user_location(
        self, user_id: int, latitude: float, longitude: float, accuracy: Optional[float] = None
    ) -> Dict[str, Any]:
        location = await self.user_repo.update_location(
            user_id=user_id, latitude=latitude, longitude=longitude, accuracy=accuracy
        )
        return self._location_to_dict(location)

    async def get_user_location(self, user_id: int) -> Optional[Dict[str, Any]]:
        location = await self.user_repo.get_location(user_id)
        return self._location_to_dict(location) if location else None

    # === Настройки пользователя ===
    async def get_user_settings(self, user_id: int) -> Optional[Dict[str, Any]]:
        settings = await self.user_repo.get_settings(user_id)
        return self._settings_to_dict(settings) if settings else None

    # ✅ ЕДИНСТВЕННЫЙ метод обновления настроек (с main_organization_id)
    async def update_user_settings(
        self,
        user_id: int,
        search_radius_km: Optional[int] = None,
        show_only_subscriptions: Optional[bool] = None,
        notifications_enabled: Optional[bool] = None,
        language: Optional[str] = None,
        theme: Optional[str] = None,
        main_organization_id: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        update_data = {}
        if search_radius_km is not None:
            update_data["search_radius_km"] = search_radius_km
        if show_only_subscriptions is not None:
            update_data["show_only_subscriptions"] = show_only_subscriptions
        if notifications_enabled is not None:
            update_data["notifications_enabled"] = notifications_enabled
        if language is not None:
            update_data["language"] = language
        if theme is not None:
            update_data["theme"] = theme
        if main_organization_id is not None:
            update_data["main_organization_id"] = main_organization_id
        if not update_data:
            return await self.get_user_settings(user_id)
        settings = await self.user_repo.update_settings(user_id, **update_data)
        return self._settings_to_dict(settings) if settings else None

    # === Service-to-Service методы ===
    async def verify_user_exists(self, user_id: int) -> bool:
        return await self.user_repo.exists(user_id)

    async def get_user_for_feed(self, user_id: int) -> Optional[Dict[str, Any]]:
        user = await self.user_repo.get_by_id(user_id)
        if not user or not user.is_active:
            return None
        settings = await self.user_repo.get_settings(user_id)
        location = await self.user_repo.get_location(user_id)
        return {
            "id": user.id,
            "email": user.email,
            "role": user.role.value if hasattr(user.role, "value") else user.role,
            "location_lat": location.latitude if location else None,
            "location_lon": location.longitude if location else None,
            "settings": self._settings_to_dict(settings) if settings else None,
        }

    async def become_organizer(self, user_id: int, current_user_id: int) -> Optional[Dict[str, Any]]:
        if user_id != current_user_id:
            raise ValueError("Нельзя изменить роль другого пользователя")
        user = await self.user_repo.get_by_id(user_id)
        if not user or not user.is_active:
            raise ValueError("Пользователь не найден или неактивен")
        if user.role == UserRoleEnum.ADMIN:
            raise ValueError("Пользователь уже является организатором")
        if user.role != UserRoleEnum.VOLUNTEER:
            raise ValueError("Только волонтёры могут стать организаторами")

        updated_user = await self.user_repo.update(user_id, role=UserRoleEnum.ADMIN)

        # Возвращаем все поля UserResponse
        return {
            "id": updated_user.id,
            "email": updated_user.email,
            "full_name": updated_user.full_name,
            "phone": updated_user.phone,
            "role": updated_user.role.value if hasattr(updated_user.role, "value") else updated_user.role,
            "is_active": updated_user.is_active,
            "is_verified": updated_user.is_verified,
            "created_at": updated_user.created_at.isoformat() if updated_user.created_at else None,
            "last_login": updated_user.last_login.isoformat() if updated_user.last_login else None,
        }

    # === Вспомогательные методы ===
    def _settings_to_dict(self, settings) -> Optional[Dict[str, Any]]:
        if not settings:
            return None
        return {
            "id": settings.id,
            "user_id": settings.user_id,
            "search_radius_km": settings.search_radius_km,
            "show_only_subscriptions": settings.show_only_subscriptions,
            "notifications_enabled": settings.notifications_enabled,
            "language": settings.language,
            "theme": settings.theme,
            "updated_at": settings.updated_at.isoformat() if settings.updated_at else None,
            "main_organization_id": settings.main_organization_id   # ✅ добавлено
        }

    def _location_to_dict(self, location) -> Optional[Dict[str, Any]]:
        if not location:
            return None
        return {
            "id": location.id,
            "user_id": location.user_id,
            "latitude": location.latitude,
            "longitude": location.longitude,
            "accuracy": location.accuracy,
            "updated_at": location.updated_at.isoformat() if location.updated_at else None
        }