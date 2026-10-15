from sqlalchemy import select, update, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from datetime import datetime, timezone
from .models import User, UserSettings, UserLocation, RefreshToken, UserRoleEnum


class UserRepository:
    """Репозиторий для операций с пользователями"""

    def __init__(self, session: AsyncSession):
        self.session = session

    # === User CRUD ===

    async def get_by_id(self, user_id: int) -> Optional[User]:
        """Получение пользователя по ID"""
        stmt = select(User).where(User.id == user_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> Optional[User]:
        """Получение пользователя по email"""
        stmt = select(User).where(User.email == email)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def exists(self, user_id: int) -> bool:
        """Проверка существования пользователя"""
        stmt = select(User.id).where(User.id == user_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def create(
            self,
            email: str,
            password_hash: str,
            full_name: Optional[str] = None,
            phone: Optional[str] = None,
            role: UserRoleEnum = UserRoleEnum.VOLUNTEER
    ) -> User:
        """Создание нового пользователя"""
        user = User(
            email=email,
            password_hash=password_hash,
            full_name=full_name,
            phone=phone,
            role=role
        )
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def update(
            self,
            user_id: int,
            **kwargs
    ) -> Optional[User]:
        """Обновление данных пользователя"""
        stmt = update(User).where(User.id == user_id).values(**kwargs)
        await self.session.execute(stmt)
        await self.session.commit()
        return await self.get_by_id(user_id)

    async def update_last_login(self, user_id: int) -> bool:
        """Обновление времени последнего входа"""
        stmt = update(User).where(User.id == user_id).values(
            last_login=datetime.now(timezone.utc)
        )
        await self.session.execute(stmt)
        await self.session.commit()
        return True

    # === UserSettings ===

    async def get_settings(self, user_id: int) -> Optional[UserSettings]:
        """Получение настроек пользователя"""
        stmt = select(UserSettings).where(UserSettings.user_id == user_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_settings(self, user_id: int) -> UserSettings:
        """Создание настроек по умолчанию"""
        settings = UserSettings(user_id=user_id)
        self.session.add(settings)
        await self.session.commit()
        await self.session.refresh(settings)
        return settings

    async def update_settings(
            self,
            user_id: int,
            **kwargs
    ) -> Optional[UserSettings]:
        """Обновление настроек пользователя"""
        stmt = update(UserSettings).where(
            UserSettings.user_id == user_id
        ).values(
            **kwargs,
            updated_at=datetime.now(timezone.utc)
        )
        await self.session.execute(stmt)
        await self.session.commit()
        return await self.get_settings(user_id)

    # === UserLocation ===

    async def get_location(self, user_id: int) -> Optional[UserLocation]:
        """Получение геолокации пользователя"""
        stmt = select(UserLocation).where(UserLocation.user_id == user_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def update_location(
            self,
            user_id: int,
            latitude: float,
            longitude: float,
            accuracy: Optional[float] = None
    ) -> UserLocation:
        """Обновление геолокации пользователя"""
        existing = await self.get_location(user_id)
        if existing:
            stmt = update(UserLocation).where(
                UserLocation.user_id == user_id
            ).values(
                latitude=latitude,
                longitude=longitude,
                accuracy=accuracy,
                updated_at=datetime.now(timezone.utc)
            )
            await self.session.execute(stmt)
            await self.session.commit()
            return await self.get_location(user_id)
        else:
            location = UserLocation(
                user_id=user_id,
                latitude=latitude,
                longitude=longitude,
                accuracy=accuracy
            )
            self.session.add(location)
            await self.session.commit()
            await self.session.refresh(location)
            return location

    # === RefreshToken (Blacklist) ===

    async def create_refresh_token(
            self,
            user_id: int,
            token_hash: str,
            expires_at: datetime
    ) -> RefreshToken:
        """Создание записи refresh токена"""
        token = RefreshToken(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at
        )
        self.session.add(token)
        await self.session.commit()
        await self.session.refresh(token)
        return token

    async def is_token_revoked(self, token_hash: str) -> bool:
        """Проверка отозван ли токен"""
        stmt = select(RefreshToken).where(
            RefreshToken.token_hash == token_hash,
            RefreshToken.revoked == True
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def revoke_token(self, token_hash: str) -> bool:
        """Отзыв токена (добавление в blacklist)"""
        stmt = update(RefreshToken).where(
            RefreshToken.token_hash == token_hash
        ).values(revoked=True)
        await self.session.execute(stmt)
        await self.session.commit()
        return True