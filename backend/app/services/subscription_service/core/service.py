import logging
from app.services.subscription_service.db.repository import SubscriptionRepository
from app.services.subscription_service.api.schemas import SubscriptionUpdate, SubscriptionResponse, \
    SubscriptionCheckResponse
from app.services.subscription_service.utils.http_client import verify_organization, verify_user

logger = logging.getLogger(__name__)


class SubscriptionService:
    def __init__(self, repo: SubscriptionRepository):
        self.repo = repo

    async def get_user_subscriptions(self, user_id: int, active_only: bool):
        subs = await self.repo.get_by_user(user_id, active_only)
        return subs

    async def subscribe(self, user_id: int, org_id: int, role: str):
        # 1. Проверка существования сущностей (HTTP)
        # В реальном проекте лучше кэшировать эти запросы или использовать события
        user_exists = await verify_user(user_id)
        if not user_exists:
            raise ValueError(f"User with ID {user_id} does not exist")

        org_exists = await verify_organization(org_id)
        if not org_exists:
            raise ValueError(f"Organization with ID {org_id} does not exist")

        # 2. Проверка на дубликат (активная подписка)
        existing = await self.repo.get_by_user_and_org(user_id, org_id)
        if existing:
            if existing.active:
                raise ValueError("You are already subscribed to this organization")
            else:
                # Если была мягко удалена, можно реактивировать
                await self.repo.update_role(existing.id, role, True)
                await self.repo.log_action(user_id, org_id, "RE-SUBSCRIBE", existing.id)
                logger.info(f"Re-subscribed user {user_id} to org {org_id}")
                return await self.repo.get_by_id(existing.id)

        # 3. Создание
        new_sub = await self.repo.create(user_id, org_id, role)
        await self.repo.log_action(user_id, org_id, "SUBSCRIBE", new_sub.id)
        logger.info(f"Subscribed user {user_id} to org {org_id}")
        return new_sub

    async def unsubscribe(self, sub_id: int):
        sub = await self.repo.get_by_id(sub_id)
        if not sub:
            return False

        await self.repo.soft_delete(sub_id)
        await self.repo.log_action(sub.user_id, sub.org_id, "UNSUBSCRIBE", sub_id)
        logger.info(f"Unsubscribed subscription ID {sub_id}")
        return True

    async def update_subscription(self, sub_id: int, data: SubscriptionUpdate):
        sub = await self.repo.get_by_id(sub_id)
        if not sub:
            return None
        new_role = data.role if data.role is not None else sub.role
        new_active = data.active if data.active is not None else sub.active

        updated = await self.repo.update_role(sub_id, new_role, new_active)
        await self.repo.log_action(sub.user_id, sub.org_id, "UPDATE", sub_id, f"Role: {new_role}, Active: {new_active}")
        return updated

    async def check_status(self, user_id: int, org_id: int) -> SubscriptionCheckResponse:
        sub = await self.repo.get_by_user_and_org(user_id, org_id)
        if not sub:
            return SubscriptionCheckResponse(is_subscribed=False, active=False)

        return SubscriptionCheckResponse(
            is_subscribed=True,
            subscription_id=sub.id,
            active=sub.active,
            role=sub.role
        )