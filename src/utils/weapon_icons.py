"""
Система иконок оружия для CS Demo Manager
Создаёт векторные иконки оружия если изображения не найдены
"""

from pathlib import Path
from typing import Dict, Optional

from PyQt6.QtGui import QPixmap, QPainter, QColor, QPen, QBrush, QFont
from PyQt6.QtCore import Qt, QRectF
from loguru import logger


class WeaponIconManager:
    """Менеджер иконок оружия"""
    
    # Категории оружия
    RIFLES = ["ak47", "m4a1", "m4a1_silencer", "aug", "sg556", "famas", "galil"]
    SNIPERS = ["awp", "ssg08", "scar20", "g3sg1"]
    SMGS = ["mp9", "mac10", "mp7", "ump45", "p90", "bizon"]
    HEAVY = ["nova", "xm1014", "mag7", "sawedoff", "m249", "negev"]
    PISTOLS = ["glock", "usp_silencer", "hkp2000", "p250", "fiveseven", 
               "tec9", "cz75a", "deagle", "revolver", "elite"]
    EQUIPMENT = ["knife", "hegrenade", "flashbang", "smokegrenade", 
                 "molotov", "incgrenade", "decoy", "c4", "taser"]
    
    # Цвета для категорий
    CATEGORY_COLORS = {
        "rifle": QColor(255, 150, 50),      # Оранжевый
        "sniper": QColor(200, 50, 50),      # Красный
        "smg": QColor(100, 200, 255),       # Голубой
        "heavy": QColor(150, 150, 150),     # Серый
        "pistol": QColor(255, 255, 100),    # Жёлтый
        "equipment": QColor(100, 255, 100), # Зелёный
        "knife": QColor(200, 200, 200),     # Светло-серый
    }
    
    def __init__(self, icons_dir: str = "assets/weapons"):
        """
        Инициализация менеджера
        
        Args:
            icons_dir: Директория с иконками оружия
        """
        self.icons_dir = Path(icons_dir)
        self.icons_dir.mkdir(parents=True, exist_ok=True)
        
        # Кэш загруженных иконок
        self._cache: Dict[str, QPixmap] = {}
        
        # Размер иконок по умолчанию
        self.default_size = 32
        
        logger.info(f"WeaponIconManager initialized: {self.icons_dir}")
    
    def get_icon(self, weapon_name: str, size: int = None) -> QPixmap:
        """
        Получить иконку оружия
        
        Args:
            weapon_name: Название оружия (например "ak47", "weapon_ak47")
            size: Размер иконки (по умолчанию 32)
            
        Returns:
            QPixmap с иконкой
        """
        if size is None:
            size = self.default_size
        
        # Нормализуем название
        clean_name = self._normalize_weapon_name(weapon_name)
        
        # Проверяем кэш
        cache_key = f"{clean_name}_{size}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        # Пробуем загрузить из файла
        icon = self._load_from_file(clean_name, size)
        
        # Если не нашли - создаём векторную иконку
        if icon is None or icon.isNull():
            icon = self._create_vector_icon(clean_name, size)
        
        # Кэшируем
        self._cache[cache_key] = icon
        
        return icon
    
    def _normalize_weapon_name(self, name: str) -> str:
        """Нормализация названия оружия"""
        clean = name.lower().strip()
        
        # Убираем префикс "weapon_"
        if clean.startswith("weapon_"):
            clean = clean[7:]
        
        # Алиасы
        aliases = {
            "m4a1_s": "m4a1_silencer",
            "usp_s": "usp_silencer",
            "m4a4": "m4a1",
            "he": "hegrenade",
            "flash": "flashbang",
            "smoke": "smokegrenade",
        }
        
        if clean in aliases:
            clean = aliases[clean]
        
        return clean
    
    def _load_from_file(self, weapon_name: str, size: int) -> Optional[QPixmap]:
        """Загрузка иконки из файла"""
        # Пробуем разные расширения
        for ext in [".png", ".svg", ".jpg"]:
            path = self.icons_dir / f"{weapon_name}{ext}"
            if path.exists():
                pixmap = QPixmap(str(path))
                if not pixmap.isNull():
                    # Масштабируем до нужного размера
                    return pixmap.scaled(
                        size, size,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation
                    )
        
        return None
    
    def _create_vector_icon(self, weapon_name: str, size: int) -> QPixmap:
        """Создание векторной иконки (fallback)"""
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Определяем категорию и цвет
        category = self._get_weapon_category(weapon_name)
        color = self.CATEGORY_COLORS.get(category, QColor(150, 150, 150))
        
        # Рисуем иконку в зависимости от типа
        if weapon_name == "knife":
            self._draw_knife(painter, size, color)
        elif category == "rifle":
            self._draw_rifle(painter, size, color)
        elif category == "sniper":
            self._draw_sniper(painter, size, color)
        elif category == "pistol":
            self._draw_pistol(painter, size, color)
        elif weapon_name in ["hegrenade", "flashbang", "smokegrenade", "molotov", "incgrenade"]:
            self._draw_grenade(painter, size, color)
        elif weapon_name == "c4":
            self._draw_c4(painter, size, color)
        else:
            # Дефолтная иконка (прямоугольник)
            self._draw_default(painter, size, color, weapon_name)
        
        painter.end()
        
        return pixmap
    
    def _get_weapon_category(self, weapon_name: str) -> str:
        """Определение категории оружия"""
        if weapon_name in self.RIFLES:
            return "rifle"
        elif weapon_name in self.SNIPERS:
            return "sniper"
        elif weapon_name in self.SMGS:
            return "smg"
        elif weapon_name in self.HEAVY:
            return "heavy"
        elif weapon_name in self.PISTOLS:
            return "pistol"
        elif weapon_name == "knife":
            return "knife"
        else:
            return "equipment"
    
    def _draw_knife(self, painter: QPainter, size: int, color: QColor):
        """Рисование ножа (треугольник)"""
        painter.setPen(QPen(Qt.GlobalColor.black, 2))
        painter.setBrush(QBrush(color))
        
        from PyQt6.QtGui import QPolygonF
        from PyQt6.QtCore import QPointF
        
        knife = QPolygonF([
            QPointF(size * 0.3, size * 0.7),
            QPointF(size * 0.7, size * 0.3),
            QPointF(size * 0.5, size * 0.2),
        ])
        painter.drawPolygon(knife)
    
    def _draw_rifle(self, painter: QPainter, size: int, color: QColor):
        """Рисование винтовки (прямоугольник + ствол)"""
        painter.setPen(QPen(Qt.GlobalColor.black, 2))
        painter.setBrush(QBrush(color))
        
        # Приклад
        painter.drawRect(int(size * 0.1), int(size * 0.4), 
                        int(size * 0.3), int(size * 0.2))
        
        # Ствол
        painter.drawRect(int(size * 0.4), int(size * 0.45), 
                        int(size * 0.5), int(size * 0.1))
    
    def _draw_sniper(self, painter: QPainter, size: int, color: QColor):
        """Рисование снайперки (длинный ствол + прицел)"""
        painter.setPen(QPen(Qt.GlobalColor.black, 2))
        painter.setBrush(QBrush(color))
        
        # Ствол
        painter.drawRect(int(size * 0.3), int(size * 0.45), 
                        int(size * 0.6), int(size * 0.1))
        
        # Прицел
        painter.drawEllipse(int(size * 0.4), int(size * 0.3), 
                           int(size * 0.15), int(size * 0.15))
    
    def _draw_pistol(self, painter: QPainter, size: int, color: QColor):
        """Рисование пистолета (маленький прямоугольник)"""
        painter.setPen(QPen(Qt.GlobalColor.black, 2))
        painter.setBrush(QBrush(color))
        
        painter.drawRect(int(size * 0.3), int(size * 0.4), 
                        int(size * 0.4), int(size * 0.2))
    
    def _draw_grenade(self, painter: QPainter, size: int, color: QColor):
        """Рисование гранаты (круг)"""
        painter.setPen(QPen(Qt.GlobalColor.black, 2))
        painter.setBrush(QBrush(color))
        
        painter.drawEllipse(int(size * 0.25), int(size * 0.25), 
                           int(size * 0.5), int(size * 0.5))
    
    def _draw_c4(self, painter: QPainter, size: int, color: QColor):
        """Рисование C4 (прямоугольник с полосками)"""
        painter.setPen(QPen(Qt.GlobalColor.black, 2))
        painter.setBrush(QBrush(color))
        
        # Основной прямоугольник
        painter.drawRect(int(size * 0.2), int(size * 0.3), 
                        int(size * 0.6), int(size * 0.4))
        
        # Полоски
        painter.drawLine(int(size * 0.3), int(size * 0.35),
                        int(size * 0.3), int(size * 0.65))
        painter.drawLine(int(size * 0.5), int(size * 0.35),
                        int(size * 0.5), int(size * 0.65))
        painter.drawLine(int(size * 0.7), int(size * 0.35),
                        int(size * 0.7), int(size * 0.65))
    
    def _draw_default(self, painter: QPainter, size: int, color: QColor, name: str):
        """Дефолтная иконка с текстом"""
        painter.setPen(QPen(Qt.GlobalColor.black, 2))
        painter.setBrush(QBrush(color))
        
        # Круг
        painter.drawEllipse(int(size * 0.1), int(size * 0.1), 
                           int(size * 0.8), int(size * 0.8))
        
        # Текст (первые 2 буквы)
        painter.setPen(Qt.GlobalColor.black)
        painter.setFont(QFont("Arial", int(size * 0.3), QFont.Weight.Bold))
        text = name[:2].upper()
        painter.drawText(QRectF(0, 0, size, size), 
                        Qt.AlignmentFlag.AlignCenter, text)
    
    def preload_common_weapons(self):
        """Предзагрузка популярных оружий"""
        common = [
            "ak47", "m4a1", "awp", "deagle", "glock", 
            "usp_silencer", "knife", "hegrenade", "flashbang"
        ]
        
        for weapon in common:
            self.get_icon(weapon)
        
        logger.info(f"Preloaded {len(common)} common weapons")
    
    def get_weapon_color(self, weapon_name: str) -> QColor:
        """Получить цвет оружия по категории"""
        clean_name = self._normalize_weapon_name(weapon_name)
        category = self._get_weapon_category(clean_name)
        return self.CATEGORY_COLORS.get(category, QColor(150, 150, 150))


# Глобальный экземпляр менеджера
_icon_manager: Optional[WeaponIconManager] = None


def get_weapon_icon_manager() -> WeaponIconManager:
    """Получить глобальный экземпляр менеджера иконок"""
    global _icon_manager
    if _icon_manager is None:
        _icon_manager = WeaponIconManager()
        _icon_manager.preload_common_weapons()
    return _icon_manager


def get_weapon_icon(weapon_name: str, size: int = 32) -> QPixmap:
    """Быстрый доступ к иконке оружия"""
    return get_weapon_icon_manager().get_icon(weapon_name, size)