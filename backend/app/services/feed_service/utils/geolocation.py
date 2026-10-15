"""
Утилиты для работы с геолокацией
"""

import math
from typing import Tuple


def calculate_distance(
        lat1: float,
        lon1: float,
        lat2: float,
        lon2: float
) -> float:
    """
    Рассчитывает расстояние между двумя точками на земле (в километрах)
    Использует формулу Haversine

    Args:
        lat1: Широта первой точки
        lon1: Долгота первой точки
        lat2: Широта второй точки
        lon2: Долгота второй точки

    Returns:
        Расстояние в километрах
    """
    # Радиус Земли в километрах
    R = 6371.0

    # Переводим градусы в радианы
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)

    # Разница координат
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad

    # Формула Haversine
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    # Расстояние
    distance = R * c

    return round(distance, 2)