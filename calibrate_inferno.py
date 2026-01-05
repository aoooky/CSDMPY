
import sys
import pandas as pd
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider, QPushButton
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPainter, QPixmap, QColor, QPen, QBrush
from loguru import logger

# Путь к демке и изображению карты
DEMO_PATH = "demos/vitality-vs-faze-m3-inferno.dem"
MAP_IMAGE = "assets/maps/de_inferno.png"

# Начальные границы (которые мы будем подбирать)
current_bounds = {
    'min_x': -2087,
    'max_x': 2048,
    'min_y': -770,
    'max_y': 3870
}


class CalibrationWindow(QMainWindow):
    def __init__(self, positions_df):
        super().__init__()
        self.positions_df = positions_df
        self.current_tick = int(positions_df['tick'].min())
        
        self.setWindowTitle("Калибровка карты de_inferno")
        self.setGeometry(100, 100, 1400, 900)
        
        self.init_ui()
    
    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        
        # Левая панель - карта
        self.map_label = QLabel()
        layout.addWidget(self.map_label, 3)
        
        # Правая панель - контролы
        controls = QWidget()
        controls_layout = QVBoxLayout(controls)
        
        # Слайдеры для границ
        self.create_slider(controls_layout, "Min X", -5000, 0, current_bounds['min_x'], 'min_x')
        self.create_slider(controls_layout, "Max X", 0, 5000, current_bounds['max_x'], 'max_x')
        self.create_slider(controls_layout, "Min Y", -5000, 0, current_bounds['min_y'], 'min_y')
        self.create_slider(controls_layout, "Max Y", 0, 5000, current_bounds['max_y'], 'max_y')
        
        # Кнопка для вывода результата
        print_btn = QPushButton("📋 Вывести границы")
        print_btn.clicked.connect(self.print_bounds)
        controls_layout.addWidget(print_btn)
        
        # Информация
        self.info_label = QLabel()
        controls_layout.addWidget(self.info_label)
        
        controls_layout.addStretch()
        layout.addWidget(controls, 1)
        
        # Загружаем карту
        self.map_pixmap = QPixmap(MAP_IMAGE)
        
        self.update_map()
    
    def create_slider(self, layout, name, min_val, max_val, current, key):
        label = QLabel(f"{name}: {current}")
        layout.addWidget(label)
        
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setMinimum(min_val)
        slider.setMaximum(max_val)
        slider.setValue(current)
        slider.valueChanged.connect(lambda v: self.on_slider_changed(key, v, label, name))
        layout.addWidget(slider)
    
    def on_slider_changed(self, key, value, label, name):
        current_bounds[key] = value
        label.setText(f"{name}: {value}")
        self.update_map()
    
    def world_to_screen(self, x, y):
        """Конвертация игровых координат в экранные"""
        width = current_bounds['max_x'] - current_bounds['min_x']
        height = current_bounds['max_y'] - current_bounds['min_y']
        
        if width <= 0:
            width = 1
        if height <= 0:
            height = 1
        
        norm_x = (x - current_bounds['min_x']) / width
        norm_y = (y - current_bounds['min_y']) / height
        norm_y = 1.0 - norm_y
        
        screen_x = norm_x * self.map_pixmap.width()
        screen_y = norm_y * self.map_pixmap.height()
        
        return screen_x, screen_y
    
    def update_map(self):
        """Обновление карты с игроками"""
        # Создаём копию карты
        result = self.map_pixmap.copy()
        painter = QPainter(result)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Получаем данные текущего тика
        current_data = self.positions_df[self.positions_df['tick'] == self.current_tick]
        
        if current_data.empty:
            current_data = self.positions_df.iloc[:10]  # Первые 10 игроков
        
        # Счётчики
        on_map = 0
        off_map = 0
        
        # Рисуем игроков
        for _, player in current_data.iterrows():
            x = player.get('X', 0)
            y = player.get('Y', 0)
            name = player.get('name', '')
            team = player.get('team_name', '')
            
            # Конвертируем координаты
            screen_x, screen_y = self.world_to_screen(x, y)
            
            # Проверяем, попадает ли на карту
            if 0 <= screen_x <= self.map_pixmap.width() and 0 <= screen_y <= self.map_pixmap.height():
                color = QColor(100, 150, 255) if 'CT' in team else QColor(255, 200, 100)
                on_map += 1
            else:
                color = QColor(255, 0, 0)  # Красный - вне карты
                off_map += 1
            
            # Рисуем игрока
            painter.setPen(QPen(Qt.GlobalColor.black, 2))
            painter.setBrush(QBrush(color))
            painter.drawEllipse(int(screen_x - 8), int(screen_y - 8), 16, 16)
            
            # Имя
            painter.setPen(Qt.GlobalColor.white)
            painter.drawText(int(screen_x - 30), int(screen_y - 12), name[:8])
            
            # Координаты
            coords_text = f"({int(x)}, {int(y)})"
            painter.drawText(int(screen_x - 40), int(screen_y + 25), coords_text)
        
        painter.end()
        
        # Обновляем изображение
        self.map_label.setPixmap(result.scaled(1000, 1000, Qt.AspectRatioMode.KeepAspectRatio))
        
        # Обновляем информацию
        self.info_label.setText(
            f"✅ На карте: {on_map}\n"
            f"❌ Вне карты: {off_map}\n\n"
            f"Всего: {len(current_data)}"
        )
    
    def print_bounds(self):
        """Вывести текущие границы"""
        print("\n" + "="*50)
        print("📋 ТЕКУЩИЕ ГРАНИЦЫ ДЛЯ de_inferno:")
        print("="*50)
        print(f'"de_inferno": MapBounds(')
        print(f'    pos_x={current_bounds["min_x"]},')
        print(f'    pos_y={current_bounds["max_y"]},')
        print(f'    scale=4.9,')
        print(f'    min_x={current_bounds["min_x"]},')
        print(f'    max_x={current_bounds["max_x"]},')
        print(f'    min_y={current_bounds["min_y"]},')
        print(f'    max_y={current_bounds["max_y"]}')
        print(f'),')
        print("="*50 + "\n")


def main():
    # Парсим демку
    logger.info("Парсинг демки...")
    from demoparser2 import DemoParser
    
    parser = DemoParser(DEMO_PATH)
    positions = parser.parse_ticks(['X', 'Y', 'name', 'team_name', 'health'])
    
    logger.info(f"Загружено {len(positions)} позиций")
    
    # Запускаем GUI
    app = QApplication(sys.argv)
    window = CalibrationWindow(positions)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
