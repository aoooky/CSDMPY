"""
Улучшенная система калибровки карт CS2 с официальными параметрами радара.

ФАЙЛ: src/utils/radar_calibration.py
ДЕЙСТВИЕ: ЗАМЕНИТЬ ПОЛНОСТЬЮ (если есть ошибки импорта)
"""

from dataclasses import dataclass
from typing import Dict, Tuple, Optional


@dataclass
class MapRadarConfig:
    """Официальная конфигурация радара из файлов CS2."""
    pos_x: float
    pos_y: float
    scale: float
    
    @property
    def real_scale(self) -> float:
        """Реальный масштаб (scale * 1024)."""
        return self.scale * 1024


# Официальные параметры радара из файлов CS2
OFFICIAL_RADAR_CONFIGS: Dict[str, MapRadarConfig] = {
    "de_inferno": MapRadarConfig(pos_x=-2087, pos_y=3870, scale=4.9),
    "de_dust2": MapRadarConfig(pos_x=-2476, pos_y=3239, scale=4.4),
    "de_mirage": MapRadarConfig(pos_x=-3230, pos_y=1713, scale=5.0),
    "de_nuke": MapRadarConfig(pos_x=-3453, pos_y=2887, scale=7.0),
    "de_overpass": MapRadarConfig(pos_x=-4831, pos_y=1781, scale=5.2),
    "de_vertigo": MapRadarConfig(pos_x=-3168, pos_y=1762, scale=4.0),
    "de_ancient": MapRadarConfig(pos_x=-2953, pos_y=2164, scale=5.0),
}


def world_to_radar_official(world_x: float, world_y: float, map_name: str) -> Tuple[Optional[float], Optional[float]]:
    """
    Конвертирует мировые координаты в радарные с использованием официальной формулы.
    
    Args:
        world_x: X координата в мировом пространстве
        world_y: Y координата в мировом пространстве
        map_name: Название карты (например, "de_inferno")
        
    Returns:
        Tuple[Optional[float], Optional[float]]: (radar_x, radar_y) в диапазоне [0, 1]
        Возвращает (None, None) если карта не поддерживается
    """
    config = OFFICIAL_RADAR_CONFIGS.get(map_name)
    
    if not config:
        # Для неизвестных карт возвращаем None, чтобы использовать fallback
        return None, None
    
    # Официальная формула CS2
    scale = config.real_scale
    radar_x = (world_x - config.pos_x) / scale
    radar_y = (world_y - config.pos_y) / -scale  # Отрицательный знак!
    
    return radar_x, radar_y


def get_map_config(map_name: str) -> Optional[MapRadarConfig]:
    """
    Возвращает конфигурацию радара для карты.
    
    Args:
        map_name: Название карты
        
    Returns:
        MapRadarConfig или None если карта не поддерживается
    """
    return OFFICIAL_RADAR_CONFIGS.get(map_name)


def is_map_supported(map_name: str) -> bool:
    """
    Проверяет, поддерживается ли карта официальной калибровкой.
    
    Args:
        map_name: Название карты
        
    Returns:
        bool: True если карта поддерживается
    """
    return map_name in OFFICIAL_RADAR_CONFIGS


def get_supported_maps() -> list:
    """
    Возвращает список всех поддерживаемых карт.
    
    Returns:
        list: Список названий карт
    """
    return list(OFFICIAL_RADAR_CONFIGS.keys())