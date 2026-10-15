"""Модуль безопасности: хеширование паролей и JWT"""
from datetime import datetime, timedelta, timezone
import bcrypt
import logging
from typing import Optional
import jwt
from app.services.user_service.config import settings

logger = logging.getLogger(__name__)


def decode_token(token: str, token_type: str = "access") -> Optional[dict]:
    """Декодирование и валидация JWT токена."""
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
    except jwt.ExpiredSignatureError:
        logger.info(
            "JWT expired (type=%s, prefix=%s)",
            token_type, token[:12],
        )
        return None
    except jwt.InvalidTokenError as e:
        # Здесь самое важное: если в логах видим подпись не сходится,
        # значит JWT_SECRET_KEY у сервиса, выпустившего токен, и у сервиса,
        # проверяющего его, — разные.
        logger.warning(
            "JWT invalid (type=%s, reason=%s, prefix=%s)",
            token_type, e, token[:12],
        )
        return None

    if payload.get("type") != token_type:
        logger.warning(
            "JWT type mismatch: expected=%s got=%s (sub=%s)",
            token_type, payload.get("type"), payload.get("sub"),
        )
        return None
    return payload

def hash_password(password: str, cost: int = None) -> str:
    """
    Хеширование пароля с использованием bcrypt
    Args:
        password: Пароль в открытом виде
        cost: Стоимость вычисления (по умолчанию из настроек)
    Returns:
        Захешированный пароль
    """
    cost = cost or settings.PASSWORD_HASH_COST
    salt = bcrypt.gensalt(rounds=cost)
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Проверка пароля
    Args:
        plain_password: Пароль в открытом виде
        hashed_password: Захешированный пароль из БД
    Returns:
        True если пароль верный, иначе False
    """
    try:
        return bcrypt.checkpw(
            plain_password.encode('utf-8'),
            hashed_password.encode('utf-8')
        )
    except (ValueError, bcrypt.exceptions.InvalidHash):
        return False


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if 'user_id' in to_encode and 'sub' not in to_encode:
        to_encode['sub'] = str(to_encode['user_id'])
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

def create_refresh_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if 'user_id' in to_encode and 'sub' not in to_encode:
        to_encode['sub'] = str(to_encode['user_id'])
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS))
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

def hash_token_for_blacklist(token: str) -> str:
    """
    Создание хеша токена для хранения в blacklist
    Используется SHA-256 для безопасного хранения refresh токенов
    """
    import hashlib
    return hashlib.sha256(token.encode('utf-8')).hexdigest()