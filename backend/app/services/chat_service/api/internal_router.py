from fastapi import APIRouter, Depends, HTTPException, Header, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.chat_service.db.session import get_db_session
from app.services.chat_service.config import settings
from app.services.chat_service.core.chat_lifecycle import ensure_event_chat
from pydantic import BaseModel

router = APIRouter(prefix="/internal", tags=["internal"])

class EnsureChatRequest(BaseModel):
    user_id: int
    organization_id: int

class EnsureChatResponse(BaseModel):
    chat_id: int

async def verify_service_key(x_service_key: str = Header(...)):
    if x_service_key != settings.SERVICE_API_KEY:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid service key")
    return True

@router.post("/events/{event_id}/ensure-chat", response_model=EnsureChatResponse)
async def ensure_event_chat_endpoint(
    event_id: int,
    request: EnsureChatRequest,
    _: bool = Depends(verify_service_key),
    db: AsyncSession = Depends(get_db_session)
):
    chat_id = await ensure_event_chat(
        db=db,
        event_id=event_id,
        user_id=request.user_id,
        organization_id=request.organization_id
    )
    return EnsureChatResponse(chat_id=chat_id)