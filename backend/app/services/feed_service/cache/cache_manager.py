"""
Менеджер кэширования для ускорения работы сервиса
"""
from typing import Optional, Any
import json
import time
from ..config import Settings
import logging

logger = logging.getLogger(__name__)

class CacheManager:
    """
    Простая реализация кэша в памяти
    Для продакшена рекомендуется использовать Redis
    """
    def __init__(self, settings: Settings):
        self.settings = settings
        self._cache: dict = {}
        self._cache_enabled = settings.CACHE_ENABLED

    def get(self, key: str) -> Optional[Any]:
        """
        Получение значения из кэша
        """
        if not self._cache_enabled:
            return None
        cached = self._cache.get(key)
        if cached is None:
            return None
        # Проверка срока годности
        if time.time() > cached["expires_at"]:
            del self._cache[key]
            logger.debug(f"Cache expired for key: {key}")
            return None
        logger.debug(f"Cache hit for key: {key}")
        return cached["value"]

    def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        """
        Сохранение значения в кэш
        ✅ ИСПРАВЛЕНО: добавлен default=str для сериализации datetime
        """
        if not self._cache_enabled:
            return False
        try:
            # ✅ ИСПРАВЛЕНО: json.dumps теперь умеет обрабатывать datetime через str()
            serialized_value = json.loads(json.dumps(value, default=str))
            self._cache[key] = {
                "value": serialized_value,
                "expires_at": time.time() + ttl,
                "created_at": time.time()
            }
            logger.debug(f"Cache set for key: {key} (ttl={ttl}s)")
            return True
        except Exception as e:
            logger.error(f"Error setting cache for key {key}: {e}")
            return False

    def delete(self, key: str) -> bool:
        """Удаление значения из кэша"""
        if key in self._cache:
            del self._cache[key]
            logger.debug(f"Cache deleted for key: {key}")
            return True
        return False

    def clear(self):
        """Очистка всего кэша"""
        self._cache.clear()
        logger.info("Cache cleared")

    def get_stats(self) -> dict:
        """Получение статистики кэша"""
        now = time.time()
        valid_items = sum(1 for item in self._cache.values() if item["expires_at"] > now)
        return {
            "total_items": len(self._cache),
            "valid_items": valid_items,
            "expired_items": len(self._cache) - valid_items
        }