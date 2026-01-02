"""
Конфигурация координат для всех карт CS:GO/CS2
Каждая карта имеет свои границы в игровых координатах (X, Y)
"""

from dataclasses import dataclass
from typing import Dict


@dataclass
class MapBounds:
    """Границы карты в игровых координатах"""
    pos_x: float  # Минимальная X координата
    pos_y: float  # Минимальная Y координата
    scale: float  # Масштаб карты (пиксели на игровую единицу)
    
    # Реальные размеры карты в игровых координатах
    min_x: float
    max_x: float
    min_y: float
    max_y: float


# Калибровочные данные для официальных карт CS2/CS:GO
# Источник: SimpleRadar / официальные данные Valve
MAP_CONFIGS: Dict[str, MapBounds] = {
    # Ancient
    "de_ancient": MapBounds(
        pos_x=-2953,
        pos_y=2164,
        scale=5.0,
        min_x=-2953,
        max_x=1344,
        min_y=-1319,
        max_y=2164
    ),
    
    # Train
    "de_train": MapBounds(
        pos_x=-2796,
        pos_y=3328,
        scale=5.22,
        min_x=-2796,
        max_x=1332,
        min_y=-676,
        max_y=3328
    ),
    
    # Dust2
    "de_dust2": MapBounds(
        pos_x=-2476,
        pos_y=3239,
        scale=4.4,
        min_x=-2476,
        max_x=1894,
        min_y=-668,
        max_y=3239
    ),
    
    # Inferno
    "de_inferno": MapBounds(
        pos_x=-2087,
        pos_y=3870,
        scale=4.9,
        min_x=-2087,
        max_x=2048,
        min_y=-770,
        max_y=3870
    ),
    
    # Mirage
    "de_mirage": MapBounds(
        pos_x=-3230,
        pos_y=1713,
        scale=5.0,
        min_x=-3230,
        max_x=1770,
        min_y=-2738,
        max_y=1713
    ),
    
    # Nuke
    "de_nuke": MapBounds(
        pos_x=-3453,
        pos_y=2887,
        scale=7.0,
        min_x=-3453,
        max_x=2560,
        min_y=-2887,
        max_y=2887
    ),
    
    # Overpass
    "de_overpass": MapBounds(
        pos_x=-3168,
        pos_y=1762,
        scale=4.0,
        min_x=-3168,
        max_x=1024,
        min_y=-1698,
        max_y=1762
    ),
}


def get_map_config(map_name: str) -> MapBounds:
    """
    Получить конфигурацию карты
    
    Args:
        map_name: Название карты (например "de_dust2")
        
    Returns:
        MapBounds с калибровочными данными
        
    Raises:
        ValueError: Если карта не найдена
    """
    # Убираем префикс, если есть
    clean_name = map_name.lower()
    
    # Пробуем найти точное совпадение
    if clean_name in MAP_CONFIGS:
        return MAP_CONFIGS[clean_name]
    
    # Пробуем найти по частичному совпадению
    for key in MAP_CONFIGS.keys():
        if clean_name in key or key in clean_name:
            return MAP_CONFIGS[key]
    
    # Если карта не найдена - используем дефолтные значения
    # (для кастомных карт)
    return MapBounds(
        pos_x=-3000,
        pos_y=3000,
        scale=5.0,
        min_x=-3000,
        max_x=3000,
        min_y=-3000,
        max_y=3000
    )


def world_to_radar(x: float, y: float, map_bounds: MapBounds, 
                   image_width: int, image_height: int) -> tuple[float, float]:
    """
    Конвертация игровых координат в координаты радара (изображения)
    
    Args:
        x: Игровая X координата
        y: Игровая Y координата
        map_bounds: Границы карты
        image_width: Ширина изображения карты в пикселях
        image_height: Высота изображения карты в пикселях
        
    Returns:
        Tuple (radar_x, radar_y) - координаты на изображении
    """
    # Нормализуем координаты в диапазон [0, 1]
    normalized_x = (x - map_bounds.min_x) / (map_bounds.max_x - map_bounds.min_x)
    normalized_y = (y - map_bounds.min_y) / (map_bounds.max_y - map_bounds.min_y)
    
    # Инвертируем Y (в CS Y растёт вверх, в изображении - вниз)
    normalized_y = 1.0 - normalized_y
    
    # Применяем к размерам изображения
    radar_x = normalized_x * image_width
    radar_y = normalized_y * image_height
    
    return radar_x, radar_y


def radar_to_world(radar_x: float, radar_y: float, map_bounds: MapBounds,
                   image_width: int, image_height: int) -> tuple[float, float]:
    """
    Конвертация координат радара в игровые координаты (обратная операция)
    
    Args:
        radar_x: X координата на изображении
        radar_y: Y координата на изображении
        map_bounds: Границы карты
        image_width: Ширина изображения карты в пикселях
        image_height: Высота изображения карты в пикселях
        
    Returns:
        Tuple (x, y) - игровые координаты
    """
    # Нормализуем координаты радара в диапазон [0, 1]
    normalized_x = radar_x / image_width
    normalized_y = radar_y / image_height
    
    # Инвертируем Y обратно
    normalized_y = 1.0 - normalized_y
    
    # Переводим в игровые координаты
    x = map_bounds.min_x + normalized_x * (map_bounds.max_x - map_bounds.min_x)
    y = map_bounds.min_y + normalized_y * (map_bounds.max_y - map_bounds.min_y)
    
    return x, y


# Алиасы названий карт (для обратной совместимости)
MAP_ALIASES = {
    "dust2": "de_dust2",
    "d2": "de_dust2",
    "mirage": "de_mirage",
    "inferno": "de_inferno",
    "nuke": "de_nuke",
    "train": "de_train",
    "ancient": "de_ancient",
    "overpass": "de_overpass",
}


def normalize_map_name(name: str) -> str:
    """
    Нормализация названия карты
    
    Args:
        name: Название карты
        
    Returns:
        Нормализованное название (например "de_dust2")
    """
    clean = name.lower().strip()
    
    # Проверяем алиасы
    if clean in MAP_ALIASES:
        return MAP_ALIASES[clean]
    
    # Добавляем префикс, если нужно
    if not clean.startswith("de_") and not clean.startswith("cs_"):
        clean = f"de_{clean}"
    
    return clean