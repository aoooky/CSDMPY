
import sys
from pathlib import Path

from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap, QPainter, QColor, QPen, QBrush

from src.core.map_renderer import MapRenderer
from src.utils.map_config import MAP_CONFIGS


class MapTestWindow(QMainWindow):
    """Окно для тестирования карт"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Map Calibration Test")
        self.setGeometry(100, 100, 1600, 900)
        
        self.current_index = 0
        self.maps = list(MAP_CONFIGS.keys())
        self.renderers = {}
        
        self.init_ui()
        self.load_current_map()
    
    def init_ui(self):
        """Инициализация UI"""
        central = QWidget()
        self.setCentralWidget(central)
        
        layout = QVBoxLayout(central)
        
        # Заголовок
        self.title_label = QLabel()
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setStyleSheet("font-size: 20px; font-weight: bold;")
        layout.addWidget(self.title_label)
        
        # Изображение
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setStyleSheet("border: 2px solid #333;")
        layout.addWidget(self.image_label, 1)
        
        # Инструкции
        instructions = QLabel(
            "RED = Top-Left corner | BLUE = Bottom-Right | GREEN = Center\n"
            "YELLOW = Bottom-Left | MAGENTA = Top-Right\n\n"
            "Press SPACE for next map | Press Q to quit\n"
            "If points are OUTSIDE the map -> Need calibration!"
        )
        instructions.setAlignment(Qt.AlignmentFlag.AlignCenter)
        instructions.setStyleSheet("font-size: 14px; padding: 10px;")
        layout.addWidget(instructions)
    
    def load_current_map(self):
        """Загрузка текущей карты"""
        map_name = self.maps[self.current_index]
        
        # Создаём рендерер
        if map_name not in self.renderers:
            self.renderers[map_name] = MapRenderer(map_name, assets_dir="assets/maps")
        
        renderer = self.renderers[map_name]
        
        # Получаем изображение карты
        base_pixmap = renderer.get_map_image()
        
        # Создаём копию для рисования
        result_pixmap = QPixmap(base_pixmap.size())
        result_pixmap.fill(Qt.GlobalColor.white)
        
        painter = QPainter(result_pixmap)
        
        # Рисуем карту
        painter.drawPixmap(0, 0, base_pixmap)
        
        # Рисуем тестовые точки
        self.draw_test_points(painter, renderer)
        
        painter.end()
        
        # Масштабируем под окно
        scaled = result_pixmap.scaled(
            1400, 700,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        
        self.image_label.setPixmap(scaled)
        
        # Обновляем заголовок
        self.title_label.setText(
            f"Map {self.current_index + 1}/{len(self.maps)}: {map_name}"
        )
        
        # Выводим информацию в консоль
        self.print_debug_info(renderer)
    
    def draw_test_points(self, painter: QPainter, renderer: MapRenderer):
        """Отрисовка тестовых точек"""
        config = renderer.map_bounds
        
        # Определяем тестовые точки
        test_points = [
            # (x, y, цвет, размер, метка)
            (config.min_x, config.max_y, QColor(255, 0, 0), 15, "TL"),
            (config.max_x, config.min_y, QColor(0, 0, 255), 15, "BR"),
            ((config.min_x + config.max_x) / 2, 
             (config.min_y + config.max_y) / 2, 
             QColor(0, 255, 0), 20, "C"),
            (config.min_x, config.min_y, QColor(255, 255, 0), 15, "BL"),
            (config.max_x, config.max_y, QColor(255, 0, 255), 15, "TR"),
        ]
        
        for x, y, color, size, label in test_points:
            pos = renderer.world_to_screen(x, y)
            
            # Рисуем круг
            painter.setPen(QPen(Qt.GlobalColor.black, 3))
            painter.setBrush(QBrush(color))
            painter.drawEllipse(pos, size, size)
            
            # Рисуем крестик
            painter.setPen(QPen(Qt.GlobalColor.white, 2))
            painter.drawLine(
                int(pos.x() - size), int(pos.y()),
                int(pos.x() + size), int(pos.y())
            )
            painter.drawLine(
                int(pos.x()), int(pos.y() - size),
                int(pos.x()), int(pos.y() + size)
            )
            
            # Рисуем метку
            painter.setPen(Qt.GlobalColor.white)
            from PyQt6.QtGui import QFont
            painter.setFont(QFont("Arial", 12, QFont.Weight.Bold))
            painter.drawText(
                int(pos.x() + size + 5),
                int(pos.y() + 5),
                f"{label} ({x:.0f}, {y:.0f})"
            )
    
    def print_debug_info(self, renderer: MapRenderer):
        """Вывод отладочной информации"""
        print(f"\n{'='*60}")
        print(f"Map: {renderer.map_name}")
        print(f"{'='*60}")
        
        info = renderer.get_debug_info()
        print(f"Image loaded: {info['image_loaded']}")
        print(f"Image size: {info['image_size']}")
        print(f"Game bounds:")
        print(f"  X: [{info['bounds']['min_x']:.0f}, {info['bounds']['max_x']:.0f}]")
        print(f"  Y: [{info['bounds']['min_y']:.0f}, {info['bounds']['max_y']:.0f}]")
        
        # Проверяем тестовые точки
        config = renderer.map_bounds
        test_coords = [
            (config.min_x, config.max_y, "Top-Left"),
            (config.max_x, config.min_y, "Bottom-Right"),
            ((config.min_x + config.max_x) / 2, 
             (config.min_y + config.max_y) / 2, "Center"),
        ]
        
        print(f"\nTest points:")
        for x, y, label in test_coords:
            screen_pos = renderer.world_to_screen(x, y)
            width, height = renderer.get_map_size()
            
            # Проверяем, внутри ли изображения
            inside = (0 <= screen_pos.x() <= width and 
                     0 <= screen_pos.y() <= height)
            
            status = "✓ OK" if inside else "✗ OUTSIDE IMAGE!"
            
            print(f"  {label}: ({x:.0f}, {y:.0f}) -> "
                  f"Screen({screen_pos.x():.0f}, {screen_pos.y():.0f}) "
                  f"[{status}]")
        
        print(f"{'='*60}\n")
    
    def keyPressEvent(self, event):
        """Обработка нажатий клавиш"""
        if event.key() == Qt.Key.Key_Space:
            # Следующая карта
            self.current_index = (self.current_index + 1) % len(self.maps)
            self.load_current_map()
        elif event.key() == Qt.Key.Key_Q:
            # Выход
            self.close()
        elif event.key() == Qt.Key.Key_Left:
            # Предыдущая карта
            self.current_index = (self.current_index - 1) % len(self.maps)
            self.load_current_map()
        elif event.key() == Qt.Key.Key_Right:
            # Следующая карта
            self.current_index = (self.current_index + 1) % len(self.maps)
            self.load_current_map()


def main():
    """Главная функция"""
    print("\n" + "="*60)
    print("MAP CALIBRATION TEST")
    print("="*60)
    print("\nChecking all maps...")
    print("\nControls:")
    print("  SPACE / RIGHT ARROW = Next map")
    print("  LEFT ARROW = Previous map")
    print("  Q = Quit")
    print("\n" + "="*60 + "\n")
    
    app = QApplication(sys.argv)
    window = MapTestWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
