"""API эндпоинты заявок на роль организатора."""
import logging

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.user_service.api.deps import (
    get_current_user,
    get_db,
    require_admin,
)
from app.services.user_service.api.schemas import (
    OrganizerApplicationResponse,
    OrganizerApplicationReviewRequest,
)
from app.services.user_service.core.organizer_application_service import (
    OrganizerApplicationService,
)
from app.services.user_service.db.models import OrganizerApplicationStatus, User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/organizer-applications", tags=["Organizer Applications"])


def get_application_service(
    db: AsyncSession = Depends(get_db),
) -> OrganizerApplicationService:
    return OrganizerApplicationService(db)


@router.post("", response_model=OrganizerApplicationResponse, status_code=status.HTTP_201_CREATED)
async def create_application(
    current_user: User = Depends(get_current_user),
    service: OrganizerApplicationService = Depends(get_application_service),
):
    """400 — уже организатор; 409 — есть pending; 429 — кулдаун 1 час."""
    return await service.create_application(current_user)


@router.get("/me", response_model=OrganizerApplicationResponse)
async def get_my_application(
    current_user: User = Depends(get_current_user),
    service: OrganizerApplicationService = Depends(get_application_service),
):
    """Своя последняя заявка. 404 — заявок не было."""
    return await service.get_my_latest(current_user.id)


@router.patch("/{application_id}", response_model=OrganizerApplicationResponse)
async def review_application(
    application_id: int,
    payload: OrganizerApplicationReviewRequest,
    admin: User = Depends(require_admin),
    service: OrganizerApplicationService = Depends(get_application_service),
):
    """Одобрить/отклонить (только is_admin). При approved роль → ORGANIZER."""
    return await service.review_application(
        application_id=application_id,
        admin=admin,
        new_status=OrganizerApplicationStatus(payload.status.value),
        rejection_reason=payload.rejection_reason,
    )