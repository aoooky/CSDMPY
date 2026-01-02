"""
Рендерер карт CS:GO/CS2
Конвертация игровых координат в координаты экрана
"""
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .models import Position
from ..utils.logger import log
from ..utils.config import config


@dataclass
class MapBounds:
    """Границы карты в игровых координатах"""
    min_x: float
    max_x: float
    min_y: float
    max_y: float
    
    @property
    def width(self) -> float:
        return self.max_x - self.min_x
    
    @property
    def height(self) -> float:
        return self.max_y - self.min_y


class MapRenderer:
    """
    Конвертер координат для отображения карты
    Преобразует игровые координаты в пиксельные
    """
    
    # Границы карт в игровых единицах (Source Engine units)
    # С добавленным margin 5% для игроков на краях
    MAP_BOUNDS = {
        "de_dust2": MapBounds(-2476, 3239, -2286, 2995),
        "de_mirage": MapBounds(-3230, 1713, -3401, 1828),
        "de_train": MapBounds(-2477, 2954, -2425, 2447),
        "de_ancient": MapBounds(-2953, 2700, -3016, 1577),
        "de_nuke": MapBounds(-3453, 2278, -2887, 3870),
        "de_overpass": MapBounds(-4831, 1781, -3401, 3225),
        "de_inferno": MapBounds(-1915, 2878, -971, 3728),  # +5% margin от (-1697, 2660, -758, 3514)
    }
    
    def __init__(self, map_name: str, canvas_width: int, canvas_height: int):
        """
        Args:
            map_name: Название карты (например, "de_dust2")
            canvas_width: Ширина холста в пикселях
            canvas_height: Высота холста в пикселях
        """
        self.map_name = map_name.lower()
        self.canvas_width = canvas_width
        self.canvas_height = canvas_height
        
        # Получаем границы карты (без padding)
        self.bounds = self.MAP_BOUNDS.get(
            self.map_name,
            MapBounds(-2500, 2500, -2500, 2500)  # Дефолтные значения
        )
        
        # Сохраняем оригинальные границы
        self.original_bounds = self.bounds
        
        # Вычисляем масштаб
        self._calculate_scale()
        
        log.debug(
            f"Map renderer initialized: {map_name}, "
            f"canvas: {canvas_width}x{canvas_height}, "
            f"scale: {self.scale:.3f}"
        )
    
    def _calculate_scale(self):
        """Вычисление масштаба для отображения"""
        # Соотношение сторон карты
        map_ratio = self.bounds.width / self.bounds.height
        canvas_ratio = self.canvas_width / self.canvas_height
        
        # Выбираем масштаб по меньшей стороне
        if map_ratio > canvas_ratio:
            # Карта шире чем canvas - масштабируем по ширине
            self.scale = self.canvas_width / self.bounds.width
        else:
            # Карта выше чем canvas - масштабируем по высоте
            self.scale = self.canvas_height / self.bounds.height
        
        # Уменьшаем масштаб на 10% чтобы был отступ
        self.scale *= 0.9
        
        # Применяем дефолтный масштаб из конфига
        self.scale *= config.default_map_scale
        
        # Вычисляем смещения для центрирования
        self.offset_x = (self.canvas_width - self.bounds.width * self.scale) / 2
        self.offset_y = (self.canvas_height - self.bounds.height * self.scale) / 2
    
    def game_to_screen(self, position: Position) -> tuple[float, float]:
        """
        Конвертация игровых координат в экранные
        
        Args:
            position: Позиция в игровых координатах
        
        Returns:
            (x, y) координаты на экране
        """
        # Нормализуем координаты относительно минимума
        x = position.x - self.bounds.min_x
        y = position.y - self.bounds.min_y
        
        # Масштабируем
        screen_x = x * self.scale + self.offset_x
        # В Source Engine Y направлена вверх, на экране - вниз
        screen_y = self.canvas_height - (y * self.scale + self.offset_y)
        
        return (screen_x, screen_y)
    
    def screen_to_game(self, screen_x: float, screen_y: float) -> Position:
        """
        Конвертация экранных координат в игровые
        
        Args:
            screen_x: X координата на экране
            screen_y: Y координата на экране
        
        Returns:
            Position в игровых координатах
        """
        # Обратное преобразование
        x = (screen_x - self.offset_x) / self.scale + self.bounds.min_x
        y = (self.canvas_height - screen_y - self.offset_y) / self.scale + self.bounds.min_y
        
        return Position(x=x, y=y, z=0)
    
    def set_zoom(self, zoom: float):
        """
        Установить масштаб
        
        Args:
            zoom: Множитель масштаба (1.0 = 100%, 2.0 = 200%, и т.д.)
        """
        self.scale = (self.canvas_width / self.bounds.width) * zoom
        self._calculate_scale()
        log.debug(f"Zoom set to {zoom:.2f}x")
    
    def resize_canvas(self, width: int, height: int):
        """
        Изменить размер холста
        
        Args:
            width: Новая ширина
            height: Новая высота
        """
        self.canvas_width = width
        self.canvas_height = height
        self._calculate_scale()
        log.debug(f"Canvas resized to {width}x{height}")
    
    def get_map_image_path(self) -> Optional[Path]:
        """
        Получить путь к изображению карты
        
        Returns:
            Path к PNG файлу карты или None если не найдено
        """
        map_path = config.maps_dir / f"{self.map_name}.png"
        
        if map_path.exists():
            return map_path
        
        log.warning(f"Map image not found: {map_path}")
        return None
    
    @staticmethod
    def is_map_supported(map_name: str) -> bool:
        """Проверка поддерживается ли карта"""
        return map_name.lower() in MapRenderer.MAP_BOUNDS
    
    @staticmethod
    def get_supported_maps() -> list[str]:
        """Получить список поддерживаемых карт"""
        return list(MapRenderer.MAP_BOUNDS.keys())