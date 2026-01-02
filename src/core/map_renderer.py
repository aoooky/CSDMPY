"""
Обновлённый MapRenderer с иконками оружия и событиями
"""

import os
from pathlib import Path
from typing import Optional, Tuple

from PyQt6.QtCore import QPointF, Qt
from PyQt6.QtGui import QPixmap, QPainter, QColor, QPen, QBrush, QFont
from loguru import logger

from src.utils.map_config import (
    get_map_config, 
    world_to_radar, 
    normalize_map_name,
    MapBounds
)
from src.utils.weapon_icons import get_weapon_icon_manager


class MapRenderer:
    """Рендерер карт с иконками оружия и событиями"""
    
    def __init__(self, map_name: str, assets_dir: str = "assets/maps"):
        """
        Инициализация рендерера
        
        Args:
            map_name: Название карты (например "de_dust2")
            assets_dir: Директория с изображениями карт
        """
        self.map_name = normalize_map_name(map_name)
        self.assets_dir = Path(assets_dir)
        
        # Загружаем конфигурацию карты
        self.map_bounds = get_map_config(self.map_name)
        
        # Загружаем изображение карты
        self.map_image: Optional[QPixmap] = None
        self.load_map_image()
        
        # Менеджер иконок оружия
        self.weapon_icons = get_weapon_icon_manager()
        
        # Кэш для оптимизации
        self._cache = {}
        
        logger.info(f"MapRenderer initialized for {self.map_name}")
        logger.debug(f"Map bounds: {self.map_bounds}")
    
    def load_map_image(self) -> bool:
        """
        Загрузка изображения карты
        
        Returns:
            True если изображение загружено успешно
        """
        # Пробуем найти файл карты
        possible_paths = [
            self.assets_dir / f"{self.map_name}.png",
            self.assets_dir / f"{self.map_name.replace('de_', '')}.png",
            self.assets_dir / f"{self.map_name}_radar.png",
        ]
        
        for path in possible_paths:
            if path.exists():
                self.map_image = QPixmap(str(path))
                if not self.map_image.isNull():
                    logger.info(f"Loaded map image: {path}")
                    logger.debug(f"Image size: {self.map_image.width()}x{self.map_image.height()}")
                    return True
        
        # Если не нашли - создаём заглушку
        logger.warning(f"Map image not found for {self.map_name}, using placeholder")
        self.map_image = self._create_placeholder()
        return False
    
    def _create_placeholder(self) -> QPixmap:
        """Создание изображения-заглушки"""
        pixmap = QPixmap(1024, 1024)
        pixmap.fill(QColor(40, 40, 40))
        
        painter = QPainter(pixmap)
        painter.setPen(QColor(100, 100, 100))
        painter.setFont(QFont("Arial", 24))
        painter.drawText(
            pixmap.rect(),
            Qt.AlignmentFlag.AlignCenter,
            f"{self.map_name}\n(Image not found)"
        )
        painter.end()
        
        return pixmap
    
    def world_to_screen(self, x: float, y: float) -> QPointF:
        """
        Конвертация игровых координат в экранные
        
        Args:
            x: Игровая X координата
            y: Игровая Y координата
            
        Returns:
            QPointF с экранными координатами
        """
        if not self.map_image:
            return QPointF(0, 0)
        
        # Используем нашу систему координат
        screen_x, screen_y = world_to_radar(
            x, y,
            self.map_bounds,
            self.map_image.width(),
            self.map_image.height()
        )
        
        return QPointF(screen_x, screen_y)
    
    def is_position_valid(self, x: float, y: float) -> bool:
        """
        Проверка, находится ли позиция в пределах карты
        
        Args:
            x: Игровая X координата
            y: Игровая Y координата
            
        Returns:
            True если позиция валидна
        """
        return (
            self.map_bounds.min_x <= x <= self.map_bounds.max_x and
            self.map_bounds.min_y <= y <= self.map_bounds.max_y
        )
    
    def get_map_image(self) -> QPixmap:
        """Получить изображение карты"""
        return self.map_image
    
    def get_map_size(self) -> Tuple[int, int]:
        """Получить размер карты в пикселях"""
        if self.map_image:
            return self.map_image.width(), self.map_image.height()
        return 1024, 1024
    
    def draw_player(
        self,
        painter: QPainter,
        x: float,
        y: float,
        yaw: float,
        color: QColor,
        health: int = 100,
        name: str = "",
        size: int = 12,
        show_name: bool = True,
        show_health: bool = False
    ):
        """
        Отрисовка игрока на карте
        
        Args:
            painter: QPainter для рисования
            x, y: Игровые координаты
            yaw: Угол взгляда (градусы)
            color: Цвет игрока (команда)
            health: Здоровье игрока (0-100)
            name: Имя игрока
            size: Размер маркера
            show_name: Показывать ли имя
            show_health: Показывать ли здоровье
        """
        # Проверяем валидность позиции
        if not self.is_position_valid(x, y):
            return
        
        # Конвертируем в экранные координаты
        pos = self.world_to_screen(x, y)
        
        # Сохраняем состояние painter
        painter.save()
        
        # Рисуем направление взгляда (треугольник)
        painter.translate(pos)
        painter.rotate(-yaw)  # Инвертируем угол для правильной ориентации
        
        # Цвет зависит от здоровья
        if health <= 0:
            color = QColor(100, 100, 100)  # Мёртвый - серый
        elif health < 25:
            color = color.lighter(120)  # Мало HP - светлее
        
        # Контур
        painter.setPen(QPen(Qt.GlobalColor.black, 2))
        painter.setBrush(QBrush(color))
        
        # Треугольник (указывает направление)
        from PyQt6.QtGui import QPolygonF
        triangle = QPolygonF([
            QPointF(0, -size),           # Вершина (вперёд)
            QPointF(-size/2, size/2),    # Левый угол
            QPointF(size/2, size/2)      # Правый угол
        ])
        painter.drawPolygon(triangle)
        
        # Восстанавливаем состояние
        painter.restore()
        
        # Рисуем имя игрока
        if show_name and name:
            painter.setPen(Qt.GlobalColor.white)
            painter.setFont(QFont("Arial", 8, QFont.Weight.Bold))
            text_rect = painter.fontMetrics().boundingRect(name)
            
            # Фон для текста
            bg_rect = text_rect.adjusted(-2, -1, 2, 1)
            bg_rect.moveCenter(QPointF(pos.x(), pos.y() - size - 10).toPoint())
            painter.fillRect(bg_rect, QColor(0, 0, 0, 180))
            
            # Текст
            painter.drawText(
                int(pos.x() - text_rect.width() / 2),
                int(pos.y() - size - 5),
                name
            )
        
        # Рисуем здоровье
        if show_health and health > 0:
            hp_text = f"{health}"
            painter.setPen(Qt.GlobalColor.white)
            painter.setFont(QFont("Arial", 7))
            painter.drawText(
                int(pos.x() - 10),
                int(pos.y() + size + 12),
                hp_text
            )
    
    def draw_kill(
        self,
        painter: QPainter,
        x: float,
        y: float,
        weapon: str = "",
        headshot: bool = False,
        show_weapon_icon: bool = True
    ):
        """
        Отрисовка маркера убийства с иконкой оружия
        
        Args:
            painter: QPainter для рисования
            x, y: Игровые координаты
            weapon: Название оружия
            headshot: Был ли хедшот
            show_weapon_icon: Показывать ли иконку оружия
        """
        if not self.is_position_valid(x, y):
            return
        
        pos = self.world_to_screen(x, y)
        
        painter.save()
        
        # Рисуем иконку оружия
        if show_weapon_icon and weapon:
            icon = self.weapon_icons.get_icon(weapon, size=24)
            icon_rect = icon.rect()
            icon_rect.moveCenter(pos.toPoint())
            painter.drawPixmap(icon_rect, icon)
        
        # Рисуем крестик убийства
        if headshot:
            painter.setPen(QPen(QColor(255, 0, 0), 3))  # Красный для хедшота
        else:
            painter.setPen(QPen(QColor(200, 200, 200), 2))  # Серый
        
        size = 6
        painter.drawLine(
            int(pos.x() - size), int(pos.y()),
            int(pos.x() + size), int(pos.y())
        )
        painter.drawLine(
            int(pos.x()), int(pos.y() - size),
            int(pos.x()), int(pos.y() + size)
        )
        
        # Индикатор хедшота (красный круг)
        if headshot:
            painter.setPen(QPen(QColor(255, 0, 0), 2))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(pos, 15, 15)
        
        painter.restore()
    
    def draw_bomb(
        self,
        painter: QPainter,
        x: float,
        y: float,
        planted: bool = False,
        pulse_alpha: int = 255
    ):
        """
        Отрисовка бомбы
        
        Args:
            painter: QPainter для рисования
            x, y: Игровые координаты
            planted: Посажена ли бомба
            pulse_alpha: Прозрачность для пульсации (0-255)
        """
        if not self.is_position_valid(x, y):
            return
        
        pos = self.world_to_screen(x, y)
        
        painter.save()
        
        if planted:
            # Пульсирующий красный круг для посаженной бомбы
            color = QColor(255, 0, 0, pulse_alpha)
            painter.setPen(QPen(Qt.GlobalColor.black, 3))
            painter.setBrush(QBrush(color))
            painter.drawEllipse(pos, 12, 12)
            
            # Внешнее кольцо
            painter.setPen(QPen(QColor(255, 0, 0, pulse_alpha // 2), 2))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(pos, 18, 18)
        else:
            # Жёлтый круг для переносимой бомбы
            color = QColor(255, 255, 0, 220)
            painter.setPen(QPen(Qt.GlobalColor.black, 2))
            painter.setBrush(QBrush(color))
            painter.drawEllipse(pos, 10, 10)
        
        # Иконка C4
        painter.setPen(Qt.GlobalColor.black)
        painter.setFont(QFont("Arial", 8, QFont.Weight.Bold))
        painter.drawText(
            int(pos.x() - 6),
            int(pos.y() + 4),
            "C4"
        )
        
        painter.restore()
    
    def draw_grenade_trajectory(
        self,
        painter: QPainter,
        positions: list[Tuple[float, float]],
        grenade_type: str = "hegrenade",
        show_explosion: bool = True
    ):
        """
        Отрисовка траектории гранаты
        
        Args:
            painter: QPainter для рисования
            positions: Список (x, y) координат
            grenade_type: Тип гранаты
            show_explosion: Показывать ли взрыв в конце
        """
        if len(positions) < 2:
            return
        
        # Цвет в зависимости от типа
        colors = {
            "hegrenade": QColor(255, 100, 100, 150),    # Красный
            "flashbang": QColor(255, 255, 100, 150),    # Жёлтый
            "smokegrenade": QColor(150, 150, 150, 150), # Серый
            "molotov": QColor(255, 150, 0, 150),        # Оранжевый
            "incgrenade": QColor(255, 150, 0, 150),     # Оранжевый
        }
        
        color = colors.get(grenade_type, QColor(100, 200, 100, 150))
        
        painter.save()
        painter.setPen(QPen(color, 2, Qt.PenStyle.DashLine))
        
        # Рисуем линию через все точки
        from PyQt6.QtGui import QPainterPath
        path = QPainterPath()
        
        first_pos = self.world_to_screen(*positions[0])
        path.moveTo(first_pos)
        
        for x, y in positions[1:]:
            if self.is_position_valid(x, y):
                pos = self.world_to_screen(x, y)
                path.lineTo(pos)
        
        painter.drawPath(path)
        
        # Рисуем взрыв в конце
        if show_explosion and positions:
            last_x, last_y = positions[-1]
            if self.is_position_valid(last_x, last_y):
                last_pos = self.world_to_screen(last_x, last_y)
                
                painter.setPen(QPen(color.darker(), 2))
                painter.setBrush(QBrush(color))
                painter.drawEllipse(last_pos, 15, 15)
                
                # Иконка гранаты
                icon = self.weapon_icons.get_icon(grenade_type, size=20)
                icon_rect = icon.rect()
                icon_rect.moveCenter(last_pos.toPoint())
                painter.drawPixmap(icon_rect, icon)
        
        painter.restore()
    
    def draw_legend(
        self,
        painter: QPainter,
        x: int,
        y: int,
        ct_alive: int,
        t_alive: int,
        round_num: int = 0,
        max_rounds: int = 0
    ):
        """
        Отрисовка легенды (счёт, живые игроки)
        
        Args:
            painter: QPainter для рисования
            x, y: Позиция легенды
            ct_alive: Живых CT
            t_alive: Живых T
            round_num: Номер раунда
            max_rounds: Всего раундов
        """
        painter.save()
        
        # Фон
        bg_rect = QRectF(x, y, 200, 80)
        painter.fillRect(bg_rect, QColor(0, 0, 0, 200))
        painter.setPen(QPen(QColor(100, 100, 100), 2))
        painter.drawRect(bg_rect)
        
        # CT команда
        painter.setPen(Qt.GlobalColor.white)
        painter.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        
        ct_color = QColor(100, 150, 255)
        painter.fillRect(int(x + 10), int(y + 10), 15, 15, ct_color)
        painter.drawText(int(x + 30), int(y + 22), f"CT: {ct_alive}")
        
        # T команда
        t_color = QColor(255, 200, 100)
        painter.fillRect(int(x + 10), int(y + 35), 15, 15, t_color)
        painter.drawText(int(x + 30), int(y + 47), f"T: {t_alive}")
        
        # Раунд
        if round_num > 0:
            painter.drawText(int(x + 10), int(y + 70), 
                           f"Round {round_num}/{max_rounds}")
        
        painter.restore()
    
    def get_debug_info(self) -> dict:
        """Получить отладочную информацию"""
        return {
            "map_name": self.map_name,
            "image_loaded": self.map_image is not None,
            "image_size": self.get_map_size() if self.map_image else None,
            "bounds": {
                "min_x": self.map_bounds.min_x,
                "max_x": self.map_bounds.max_x,
                "min_y": self.map_bounds.min_y,
                "max_y": self.map_bounds.max_y,
            }
        }