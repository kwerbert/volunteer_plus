"""
Модуль управления HTTP-сессиями для микросервиса.
✅ Единый пул соединений aiohttp с настройками таймаутов и лимитов.
"""
import aiohttp
import logging
from typing import AsyncGenerator
from fastapi import Depends

logger = logging.getLogger(__name__)


class HTTPClientManager:
    """
    Менеджер единой aiohttp.ClientSession для всего приложения.
    Использует TCPConnector с пулом соединений для эффективного reuse.
    """

    def __init__(
            self,
            connection_limit: int = 100,
            ttl_dns_cache: int = 300,
            use_dns_cache: bool = True,
            keepalive_timeout: float = 30.0,
            request_timeout: float = 10.0,
            sock_connect_timeout: float = 5.0,
            sock_read_timeout: float = 10.0,
    ):
        self.connection_limit = connection_limit
        self.ttl_dns_cache = ttl_dns_cache
        self.use_dns_cache = use_dns_cache
        self.keepalive_timeout = keepalive_timeout
        self.request_timeout = request_timeout
        self.sock_connect_timeout = sock_connect_timeout
        self.sock_read_timeout = sock_read_timeout

        self._session: aiohttp.ClientSession | None = None

    async def create_session(self) -> aiohttp.ClientSession:
        """Создание и настройка ClientSession с пулом соединений."""
        connector = aiohttp.TCPConnector(
            limit=self.connection_limit,
            ttl_dns_cache=self.ttl_dns_cache,
            use_dns_cache=self.use_dns_cache,
            keepalive_timeout=self.keepalive_timeout,
            enable_cleanup_closed=True,
        )

        timeout = aiohttp.ClientTimeout(
            total=self.request_timeout,
            sock_connect=self.sock_connect_timeout,
            sock_read=self.sock_read_timeout,
        )

        self._session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers={
                "User-Agent": "VolunteerPlus-FeedService/1.0",
                "Content-Type": "application/json",
            },
            raise_for_status=False,  # Обрабатываем статусы вручную
        )

        logger.info(
            f"HTTP ClientSession created: limit={self.connection_limit}, "
            f"timeout={self.request_timeout}s"
        )
        return self._session

    async def close_session(self) -> None:
        """Корректное закрытие сессии и освобождение ресурсов."""
        if self._session and not self._session.closed:
            await self._session.close()
            logger.info("HTTP ClientSession closed")
        self._session = None

    @property
    def session(self) -> aiohttp.ClientSession:
        """Получение активной сессии."""
        if self._session is None or self._session.closed:
            raise RuntimeError(
                "HTTP ClientSession not initialized. "
                "Call create_session() in lifespan first."
            )
        return self._session


# Глобальный экземпляр менеджера
http_client_manager = HTTPClientManager()


# === FastAPI Dependencies ===

async def get_http_session() -> AsyncGenerator[aiohttp.ClientSession, None]:
    """
    Dependency для получения HTTP-сессии.
    ✅ Session reused across requests, no leaks.
    """
    yield http_client_manager.session


# Удобные алиасы для использования в сервисах
AsyncSession = aiohttp.ClientSession
get_async_session = get_http_session