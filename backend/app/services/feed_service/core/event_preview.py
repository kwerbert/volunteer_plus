import logging
from datetime import datetime
from typing import Any, Dict, List

from ..api.schemas import EventPreview, EventRolePreview, OrganizationPreview

logger = logging.getLogger(__name__)

# Зеркало event_service.settings.DEFAULT_EVENT_HOURS
DEFAULT_ROLE_HOURS = 4.0


def normalize_event_dates(event: Dict[str, Any]) -> Dict[str, Any]:
    """start_date → start_time, end_date → end_time. Копия, вход не мутируем."""
    evt = event.copy()
    if "start_date" in evt and "start_time" not in evt:
        evt["start_time"] = evt["start_date"]
    if "end_date" in evt and "end_time" not in evt:
        evt["end_time"] = evt.get("end_date")
    return evt


def _parse_datetime(value: Any, fallback: datetime) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            logger.debug("Cannot parse datetime %r, using fallback", value)
    return fallback


def _build_role_previews(roles: Any) -> List[EventRolePreview]:
    """Роли приходят из детального GET /events/{id}. В списочных ответах
    event_service их нет — будет [] (фронт добирает детали отдельным запросом)."""
    if not isinstance(roles, list):
        return []
    previews: List[EventRolePreview] = []
    for role in roles:
        if not isinstance(role, dict):
            continue
        previews.append(
            EventRolePreview(
                id=role.get("id", 0),
                name=role.get("name", ""),
                description=role.get("description"),
                hours_value=float(role.get("hours_value") or DEFAULT_ROLE_HOURS),
                max_participants=role.get("max_participants"),
                registered_count=int(role.get("registered_count") or 0),
            )
        )
    return previews


def build_event_preview(event: Dict[str, Any]) -> EventPreview:
    """Безопасное построение EventPreview из словаря мероприятия.
    Поддерживает оба формата дат (start_time/start_date) и оба ключа org."""
    start_raw = event.get("start_time") or event.get("start_date")
    end_raw = event.get("end_time") or event.get("end_date") or start_raw
    start_time = _parse_datetime(start_raw, datetime.now())
    end_time = _parse_datetime(end_raw, start_time)

    org_id = event.get("organization_id") or event.get("org_id") or 0
    description = event.get("description")

    return EventPreview(
        id=event.get("id", 0),
        title=event.get("title", "Без названия"),
        organization=OrganizationPreview(
            id=org_id,
            name=event.get("organization_name", "Организация"),
            logo_url=event.get("organization_logo"),
            rating=float(event.get("organization_rating") or 0.0),
            verified=bool(event.get("organization_verified", False)),
            category_id=event.get("category_id"),
        ),
        description_preview=description[:100] if description else None,
        start_time=start_time,
        end_time=end_time,
        location_lat=event.get("location_lat"),
        location_lon=event.get("location_lon"),
        distance_km=event.get("distance_km"),
        required_role_id=event.get("required_role_id"),
        max_participants=event.get("max_participants"),
        registered_count=event.get("registered_count", 0),
        # === Этап 7.3 ===
        image_url=event.get("image_url"),
        status=event.get("status") or "active",
        has_custom_roles=bool(event.get("has_custom_roles", False)),
        roles=_build_role_previews(event.get("roles")),
    )
