import logging
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.utils.notifications_enums import NotificationType

from .db.models import Organization, OrganizationOrganizer, OrgOrganizerRole
from .db.organizer_repository import OrganizationOrganizerRepository
from .schemas import CurrentUser, OrganizationCreate
from .utils.chat_client import add_organizer_to_chats, remove_organizer_from_chats
from .utils.event_client import cancel_organization_events
from .utils.http_client import get_user_by_email
from .utils.notification_client import NotificationServiceClient

logger = logging.getLogger(__name__)


class OrganizationService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.organizers = OrganizationOrganizerRepository(db)
        self.notifications = NotificationServiceClient()

    # === Создание ===

    async def create(
        self, data: OrganizationCreate, current_user: CurrentUser
    ) -> Organization:
        """Роль ORGANIZER проверяет require_organizer в роутере."""
        # 1. Один аккаунт — одна СВОЯ организация (активное владение).
        #    Членство в чужих организациях созданию своей не мешает.
        owned_id = await self.organizers.get_owned_organization_id(current_user.id)
        if owned_id is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"У пользователя уже есть организация (id={owned_id})",
            )
        # 2. Уникальность имени
        existing = await self.db.execute(
            select(Organization).where(Organization.name == data.name)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Organization with this name already exists",
            )
        # 3. Организация + запись владельца — одна транзакция.
        org = Organization(
            name=data.name,
            description=data.description,
            category_id=data.category_id,
            owner_user_id=current_user.id,
            is_verified=False,
            rating=0.0,
            is_active=True,
        )
        try:
            self.db.add(org)
            await self.db.flush()
            await self.organizers.add(
                org.id,
                current_user.id,
                OrgOrganizerRole.OWNER,
                added_by=current_user.id,
            )
            await self.db.commit()
        except IntegrityError:
            # Гонка двух параллельных POST — partial unique index на владельца.
            await self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="У пользователя уже есть организация",
            )
        await self.db.refresh(org)
        logger.info("Organization %s created by user %s", org.id, current_user.id)
        return org

    # === Чтение ===

    async def get_list(
        self, category_id: Optional[int] = None, verified: Optional[bool] = None
    ) -> List[Organization]:
        # Удалённые организации в публичном листинге не показываем.
        query = select(Organization).where(Organization.is_active)
        if category_id is not None:
            query = query.where(Organization.category_id == category_id)
        if verified is not None:
            query = query.where(Organization.is_verified == verified)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_by_id(self, org_id: int) -> Optional[Organization]:
        # Возвращаем и неактивные: имя нужно чатам и истории мероприятий.
        return await self.db.get(Organization, org_id)

    async def _get_active_org_or_404(self, org_id: int) -> Organization:
        org = await self.db.get(Organization, org_id)
        if not org or not org.is_active:
            raise HTTPException(status_code=404, detail="Organization not found")
        return org

    async def _require_owner(self, org_id: int, current_user: CurrentUser) -> None:
        if not await self.organizers.is_owner(org_id, current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Только владелец организации может выполнять это действие",
            )

    # === Организаторы организации ===

    async def list_organizers(self, org_id: int) -> List[OrganizationOrganizer]:
        await self._get_active_org_or_404(org_id)
        return await self.organizers.get_active_by_organization(org_id)

    async def _notify_organizers_added(
        self, org_id: int, new_user_id: int, user_info: dict
    ) -> None:
        """5.4: NEW_ORGANIZER_ADDED всем действующим организаторам, кроме нового."""
        try:
            members = await self.organizers.get_active_by_organization(org_id)
            recipients = sorted(
                {m.user_id for m in members if m.user_id != new_user_id}
            )
            if not recipients:
                return
            org = await self.db.get(Organization, org_id)
            org_name = org.name if org else f"#{org_id}"
            who = (
                user_info.get("full_name")
                or user_info.get("email")
                or f"#{new_user_id}"
            )
            self.notifications.notify_background(
                user_ids=recipients,
                title="Новый организатор",
                body=f"{who} добавлен(а) в организацию «{org_name}»",
                notification_type=NotificationType.NEW_ORGANIZER_ADDED,
                data={"org_id": org_id, "user_id": new_user_id},
            )
        except Exception:
            logger.warning("Failed to schedule NEW_ORGANIZER_ADDED for org %s", org_id)

    async def add_organizer(
        self, org_id: int, email: str, current_user: CurrentUser
    ) -> OrganizationOrganizer:
        await self._get_active_org_or_404(org_id)
        await self._require_owner(org_id, current_user)

        user_info = await get_user_by_email(email)
        if user_info is None:
            raise HTTPException(
                status_code=404, detail=f"Пользователь с email {email} не найден"
            )
        if not user_info.get("is_active"):
            raise HTTPException(status_code=422, detail="Пользователь деактивирован")
        if user_info.get("role") != "organizer":
            raise HTTPException(
                status_code=422,
                detail="Пользователь не является организатором: "
                "сначала он должен подать заявку и получить одобрение",
            )
        target_id = int(user_info["id"])

        membership = await self.organizers.get_membership(org_id, target_id)
        if membership and membership.is_active:
            raise HTTPException(
                status_code=409, detail="Пользователь уже организатор этой организации"
            )
        try:
            if membership:
                membership = await self.organizers.reactivate(
                    membership, added_by=current_user.id
                )
            else:
                membership = await self.organizers.add(
                    org_id,
                    target_id,
                    OrgOrganizerRole.ORGANIZER,
                    added_by=current_user.id,
                )
            await self.db.commit()
        except IntegrityError:
            await self.db.rollback()
            raise HTTPException(
                status_code=409, detail="Пользователь уже организатор этой организации"
            )
        await self.db.refresh(membership)
        await self._notify_organizers_added(org_id, target_id, user_info)
        # Этап 6.2: организатор добавляется во все EVENT-чаты организации.
        # Побочный эффект: сбой chat_service не откатывает добавление.
        try:
            await add_organizer_to_chats(org_id, target_id)
        except Exception:
            logger.warning(
                "Failed to sync chats for new organizer %s of org %s",
                target_id,
                org_id,
            )
        logger.info(
            "User %s added as organizer of org %s by %s",
            target_id,
            org_id,
            current_user.id,
        )
        return membership

    async def remove_organizer(
        self, org_id: int, user_id: int, current_user: CurrentUser
    ) -> None:
        await self._get_active_org_or_404(org_id)
        await self._require_owner(org_id, current_user)
        if user_id == current_user.id:
            raise HTTPException(
                status_code=400, detail="Владелец не может удалить сам себя"
            )
        membership = await self.organizers.get_active_membership(org_id, user_id)
        if membership is None:
            raise HTTPException(
                status_code=404,
                detail="Пользователь не является организатором этой организации",
            )
        if membership.role_in_org == OrgOrganizerRole.OWNER:
            raise HTTPException(
                status_code=400, detail="Нельзя удалить владельца организации"
            )
        await self.organizers.deactivate(membership)
        await self.db.commit()
        # Этап 6.3: убираем организатора из EVENT-чатов организации.
        try:
            await remove_organizer_from_chats(org_id, user_id)
        except Exception:
            logger.warning(
                "Failed to remove organizer %s from chats of org %s",
                user_id,
                org_id,
            )
        logger.info(
            "User %s removed from organizers of org %s by %s",
            user_id,
            org_id,
            current_user.id,
        )

    # === Удаление организации (мягкое) ===

    async def delete_organization(self, org_id: int, current_user: CurrentUser) -> None:
        org = await self._get_active_org_or_404(org_id)
        is_owner = await self.organizers.is_owner(org_id, current_user.id)
        if not (is_owner or current_user.is_admin):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Удалить организацию может только владелец или администратор",
            )

        # Этап 4.6: сначала отменяем активные/будущие мероприятия.
        # Завершённые остаются как есть — название организации «заморожено»
        # (GET /organizations/{id} отдаёт и неактивные организации).
        # Если event_service недоступен — 503 и ничего не меняем.
        stats = await cancel_organization_events(org_id)

        await self.organizers.deactivate_all_for_organization(org_id)
        org.is_active = False
        await self.db.commit()
        logger.info(
            "Organization %s deactivated by user %s (cancelled_events=%s)",
            org_id,
            current_user.id,
            stats.get("cancelled_events", 0),
        )

    # === Верификация (заглушка, только админ) ===

    async def verify_organization(self, org_id: int, verified: bool) -> Organization:
        org = await self._get_active_org_or_404(org_id)
        org.is_verified = verified
        if verified:
            org.rating = min(org.rating + 1.0, 5.0)  # поведение сохранено как было
        await self.db.commit()
        await self.db.refresh(org)
        return org
