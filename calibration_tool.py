"""
Инструмент для калибровки карт

Этот скрипт поможет проверить, правильно ли отображаются игроки на картах.
Если нет - поможет откалибровать координаты.

Использование:
    python calibration_tool.py --demo path/to/demo.dem --map de_dust2

Или просто:
    python calibration_tool.py --test
"""

import sys
import argparse
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, 
    QHBoxLayout, QPushButton, QLabel, QSpinBox, QDoubleSpinBox,
    QGraphicsView, QGraphicsScene, QGraphicsPixmapItem
)
from PyQt6.QtCore import Qt, QPointF
from PyQt6.QtGui import QPixmap, QPainter, QColor, QPen

from src.utils.map_config import MAP_CONFIGS, get_map_config, world_to_radar
from src.core.map_renderer import MapRenderer


class CalibrationWindow(QMainWindow):
    """Окно для калибровки карт"""
    
    def __init__(self, map_name: str = "de_dust2", demo_path: str = None):
        super().__init__()
        
        self.map_name = map_name
        self.demo_path = demo_path
        self.renderer = None
        self.test_points = []
        
        self.init_ui()
        self.load_map()
        
    def init_ui(self):
        """Инициализация UI"""
        self.setWindowTitle(f"Map Calibration Tool - {self.map_name}")
        self.setGeometry(100, 100, 1400, 900)
        
        # Центральный виджет
        central = QWidget()
        self.setCentralWidget(central)
        
        # Основной layout
        main_layout = QHBoxLayout(central)
        
        # Левая панель - карта
        left_panel = self._create_map_view()
        main_layout.addWidget(left_panel, 3)
        
        # Правая панель - контролы
        right_panel = self._create_controls()
        main_layout.addWidget(right_panel, 1)
        
    def _create_map_view(self) -> QGraphicsView:
        """Создание view для карты"""
        self.scene = QGraphicsScene()
        self.view = QGraphicsView(self.scene)
        self.view.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        return self.view
    
    def _create_controls(self) -> QWidget:
        """Создание панели контролов"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Заголовок
        layout.addWidget(QLabel(f"<h2>Calibration: {self.map_name}</h2>"))
        
        # Текущие параметры
        layout.addWidget(QLabel("<h3>Current Config:</h3>"))
        
        config = get_map_config(self.map_name)
        
        # Min X
        layout.addWidget(QLabel("Min X:"))
        self.min_x_spin = QDoubleSpinBox()
        self.min_x_spin.setRange(-10000, 10000)
        self.min_x_spin.setValue(config.min_x)
        self.min_x_spin.valueChanged.connect(self.on_config_changed)
        layout.addWidget(self.min_x_spin)
        
        # Max X
        layout.addWidget(QLabel("Max X:"))
        self.max_x_spin = QDoubleSpinBox()
        self.max_x_spin.setRange(-10000, 10000)
        self.max_x_spin.setValue(config.max_x)
        self.max_x_spin.valueChanged.connect(self.on_config_changed)
        layout.addWidget(self.max_x_spin)
        
        # Min Y
        layout.addWidget(QLabel("Min Y:"))
        self.min_y_spin = QDoubleSpinBox()
        self.min_y_spin.setRange(-10000, 10000)
        self.min_y_spin.setValue(config.min_y)
        self.min_y_spin.valueChanged.connect(self.on_config_changed)
        layout.addWidget(self.min_y_spin)
        
        # Max Y
        layout.addWidget(QLabel("Max Y:"))
        self.max_y_spin = QDoubleSpinBox()
        self.max_y_spin.setRange(-10000, 10000)
        self.max_y_spin.setValue(config.max_y)
        self.max_y_spin.valueChanged.connect(self.on_config_changed)
        layout.addWidget(self.max_y_spin)
        
        # Scale
        layout.addWidget(QLabel("Scale:"))
        self.scale_spin = QDoubleSpinBox()
        self.scale_spin.setRange(0.1, 20.0)
        self.scale_spin.setSingleStep(0.1)
        self.scale_spin.setValue(config.scale)
        self.scale_spin.valueChanged.connect(self.on_config_changed)
        layout.addWidget(self.scale_spin)
        
        layout.addSpacing(20)
        
        # Кнопки
        add_test_btn = QPushButton("Add Test Points")
        add_test_btn.clicked.connect(self.add_test_points)
        layout.addWidget(add_test_btn)
        
        clear_btn = QPushButton("Clear Points")
        clear_btn.clicked.connect(self.clear_points)
        layout.addWidget(clear_btn)
        
        export_btn = QPushButton("Export Config")
        export_btn.clicked.connect(self.export_config)
        layout.addWidget(export_btn)
        
        # Инструкция
        layout.addSpacing(20)
        layout.addWidget(QLabel("<h3>Instructions:</h3>"))
        instructions = QLabel(
            "1. Adjust parameters until test points align with map\n"
            "2. Test points represent game coordinates\n"
            "3. Red = Top-Left corner\n"
            "4. Blue = Bottom-Right corner\n"
            "5. Green = Center\n"
            "6. Export config when done"
        )
        instructions.setWordWrap(True)
        layout.addWidget(instructions)
        
        layout.addStretch()
        
        return widget
    
    def load_map(self):
        """Загрузка карты"""
        self.renderer = MapRenderer(self.map_name)
        
        # Отображаем карту
        pixmap = self.renderer.get_map_image()
        self.scene.clear()
        self.scene.addPixmap(pixmap)
        
        # Добавляем тестовые точки
        self.add_test_points()
        
    def add_test_points(self):
        """Добавление тестовых точек"""
        self.clear_points()
        
        config = get_map_config(self.map_name)
        
        # Определяем тестовые точки в игровых координатах
        test_coords = [
            # (x, y, цвет, метка)
            (config.min_x, config.max_y, QColor(255, 0, 0), "Top-Left"),
            (config.max_x, config.min_y, QColor(0, 0, 255), "Bottom-Right"),
            ((config.min_x + config.max_x) / 2, 
             (config.min_y + config.max_y) / 2, 
             QColor(0, 255, 0), "Center"),
            (config.min_x, config.min_y, QColor(255, 255, 0), "Bottom-Left"),
            (config.max_x, config.max_y, QColor(255, 0, 255), "Top-Right"),
        ]
        
        # Рисуем точки
        for x, y, color, label in test_coords:
            self.draw_test_point(x, y, color, label)
    
    def draw_test_point(self, x: float, y: float, color: QColor, label: str):
        """Отрисовка тестовой точки"""
        pos = self.renderer.world_to_screen(x, y)
        
        # Рисуем круг
        from PyQt6.QtWidgets import QGraphicsEllipseItem, QGraphicsTextItem
        
        size = 10
        circle = QGraphicsEllipseItem(
            pos.x() - size/2, 
            pos.y() - size/2, 
            size, size
        )
        circle.setBrush(color)
        circle.setPen(QPen(Qt.GlobalColor.black, 2))
        self.scene.addItem(circle)
        
        # Рисуем метку
        text = QGraphicsTextItem(f"{label}\n({x:.0f}, {y:.0f})")
        text.setPos(pos.x() + 15, pos.y() - 10)
        text.setDefaultTextColor(color)
        self.scene.addItem(text)
        
        self.test_points.append((circle, text))
    
    def clear_points(self):
        """Очистка тестовых точек"""
        for circle, text in self.test_points:
            self.scene.removeItem(circle)
            self.scene.removeItem(text)
        self.test_points.clear()
    
    def on_config_changed(self):
        """Обработчик изменения конфигурации"""
        # Обновляем конфигурацию
        config = get_map_config(self.map_name)
        config.min_x = self.min_x_spin.value()
        config.max_x = self.max_x_spin.value()
        config.min_y = self.min_y_spin.value()
        config.max_y = self.max_y_spin.value()
        config.scale = self.scale_spin.value()
        
        # Перерисовываем точки
        self.add_test_points()
    
    def export_config(self):
        """Экспорт конфигурации"""
        config = get_map_config(self.map_name)
        
        output = f"""
# Config for {self.map_name}
"{self.map_name}": MapBounds(
    pos_x={config.pos_x},
    pos_y={config.pos_y},
    scale={self.scale_spin.value()},
    min_x={self.min_x_spin.value()},
    max_x={self.max_x_spin.value()},
    min_y={self.min_y_spin.value()},
    max_y={self.max_y_spin.value()}
),
"""
        
        print(output)
        
        # Сохраняем в файл
        output_file = Path("calibration_output.txt")
        with open(output_file, "w") as f:
            f.write(output)
        
        print(f"Config saved to {output_file}")


def test_all_maps():
    """Тестирование всех карт"""
    print("\n=== Map Configuration Test ===\n")
    
    for map_name in MAP_CONFIGS.keys():
        print(f"\nTesting {map_name}...")
        renderer = MapRenderer(map_name)
        
        config = get_map_config(map_name)
        
        # Тестовые точки
        test_points = [
            ("Top-Left", config.min_x, config.max_y),
            ("Top-Right", config.max_x, config.max_y),
            ("Bottom-Left", config.min_x, config.min_y),
            ("Bottom-Right", config.max_x, config.min_y),
            ("Center", (config.min_x + config.max_x) / 2, 
                      (config.min_y + config.max_y) / 2),
        ]
        
        print(f"  Image size: {renderer.get_map_size()}")
        print(f"  Game bounds: X[{config.min_x:.0f}, {config.max_x:.0f}], "
              f"Y[{config.min_y:.0f}, {config.max_y:.0f}]")
        
        print("  Test points:")
        for label, x, y in test_points:
            screen_pos = renderer.world_to_screen(x, y)
            valid = renderer.is_position_valid(x, y)
            print(f"    {label}: ({x:.0f}, {y:.0f}) -> "
                  f"Screen({screen_pos.x():.0f}, {screen_pos.y():.0f}) "
                  f"[{'✓' if valid else '✗'}]")


def main():
    """Главная функция"""
    parser = argparse.ArgumentParser(description="Map Calibration Tool")
    parser.add_argument("--map", default="de_dust2", help="Map name")
    parser.add_argument("--demo", help="Demo file path (optional)")
    parser.add_argument("--test", action="store_true", 
                       help="Run tests for all maps")
    
    args = parser.parse_args()
    
    if args.test:
        test_all_maps()
        return
    
    app = QApplication(sys.argv)
    window = CalibrationWindow(args.map, args.demo)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()