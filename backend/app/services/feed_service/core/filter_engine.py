"""
Система фильтров для мероприятий
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
import math
from ..config import Settings
from ..api.schemas import FeedFilterParams
from ..utils.geolocation import calculate_distance
import logging

logger = logging.getLogger(__name__)

class FilterEngine:
    """Класс для фильтрации мероприятий по различным критериям"""

    def __init__(self, settings: Settings):
        self.settings = settings

    def filter_events(
        self,
        events: List[Dict[str, Any]],
        filter_params: FeedFilterParams,
        user_location: Dict[str, Optional[float]]
    ) -> List[Dict[str, Any]]:
        """
        Применение всех фильтров к списку мероприятий
        Порядок фильтрации:
        1. По дате (только будущие мероприятия)
        2. По геолокации (если указаны координаты)
        3. По категориям
        4. По ролям
        5. Расчёт расстояния до каждого мероприятия
        """
        filtered = events

        # Фильтр 1: По дате (только если даты явно указаны)
        if filter_params.date_from:
            filtered = [
                event for event in filtered
                if self._parse_datetime(event.get("start_time", "")) >= filter_params.date_from
            ]

        if filter_params.date_to:
            filtered = [
                event for event in filtered
                if self._parse_datetime(event.get("start_time", "")) <= filter_params.date_to
            ]

        # Фильтр 2: По геолокации
        if user_location.get("lat") and user_location.get("lon"):
            filtered = self._filter_by_location(
                events=filtered,
                user_lat=user_location["lat"],
                user_lon=user_location["lon"],
                max_radius_km=filter_params.radius_km or self.settings.DEFAULT_SEARCH_RADIUS_KM
            )

        # Фильтр 3: По категориям
        if filter_params.category_ids:
            filtered = [
                event for event in filtered
                if event.get("category_id") in filter_params.category_ids
            ]

        # Фильтр 4: По ролям
        if filter_params.role_ids:
            filtered = [
                event for event in filtered
                if event.get("required_role_id") in filter_params.role_ids
            ]

        logger.info(f"Filtered {len(events)} events down to {len(filtered)} events")
        return filtered

    def _parse_datetime(self, date_string: str) -> datetime:
        """Парсинг строки даты с обработкой различных форматов"""
        if not date_string:
            return datetime.now()
        try:
            # Обработка Z suffix для UTC
            if date_string.endswith("Z"):
                date_string = date_string[:-1] + "+00:00"
            return datetime.fromisoformat(date_string)
        except ValueError:
            # Если не получается распарсить, возвращаем текущую дату
            return datetime.now()

    def _filter_by_location(
        self,
        events: List[Dict[str, Any]],
        user_lat: float,
        user_lon: float,
        max_radius_km: int
    ) -> List[Dict[str, Any]]:
        """
        Фильтрация мероприятий по расстоянию от пользователя
        Для каждого мероприятия рассчитывается расстояние и добавляется поле `distance_km`
        """
        filtered = []
        for event in events:
            event_lat = event.get("location_lat")
            event_lon = event.get("location_lon")

            # Если у мероприятия нет координат, пропускаем фильтр (включаем событие)
            if event_lat is None or event_lon is None:
                event["distance_km"] = None
                filtered.append(event)
                continue

            # Рассчитываем расстояние
            distance = calculate_distance(user_lat, user_lon, event_lat, event_lon)
            event["distance_km"] = distance

            # Фильтруем по радиусу
            if distance <= max_radius_km:
                filtered.append(event)

        # Сортируем по расстоянию (ближайшие первыми)
        filtered.sort(key=lambda e: e.get("distance_km") or float('inf'))
        return filtered