"""
Обновлённый Demo Viewer с правильной калибровкой координат
"""

from typing import Optional, Dict, List
from datetime import datetime

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGraphicsView, 
    QGraphicsScene, QGraphicsPixmapItem, QPushButton,
    QSlider, QLabel, QSpinBox
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QPointF
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QPixmap
from loguru import logger

from src.core.map_renderer import MapRenderer


class DemoViewer(QWidget):
    """Виджет для просмотра демки в 2D"""
    
    # Сигналы
    playback_started = pyqtSignal()
    playback_paused = pyqtSignal()
    playback_stopped = pyqtSignal()
    playback_state_changed = pyqtSignal(str)  # "playing", "paused", "stopped"
    tick_changed = pyqtSignal(int)
    
    def __init__(self):
        super().__init__()
        
        # Данные демки
        self.positions_data = None
        self.rounds_data = None
        self.kills_data = None
        self.map_name = None
        
        # Совместимость со старым кодом
        self.frames = []  # Для совместимости с main_window
        
        # Рендерер карты
        self.map_renderer: Optional[MapRenderer] = None
        
        # Воспроизведение
        self.current_tick = 0
        self.max_tick = 0
        self.is_playing = False
        self.playback_speed = 1.0  # 1.0 = реальное время
        
        # Таймер для анимации (60 FPS)
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.fps = 60
        self.tick_rate = 64  # CS tick rate
        
        # Кэш для оптимизации
        self._player_cache = {}
        self._kill_cache = {}
        
        self.init_ui()
        
        logger.info("DemoViewer initialized")
    
    def init_ui(self):
        """Инициализация UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Сцена и view для карты
        self.scene = QGraphicsScene()
        self.view = QGraphicsView(self.scene)
        self.view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        layout.addWidget(self.view, 1)
        
        # Панель управления
        controls = self._create_controls()
        layout.addWidget(controls)
    
    def _create_controls(self) -> QWidget:
        """Создание панели управления"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        
        # Кнопки воспроизведения
        self.play_btn = QPushButton("▶ Play")
        self.play_btn.clicked.connect(self.toggle_playback)
        layout.addWidget(self.play_btn)
        
        self.stop_btn = QPushButton("⏹ Stop")
        self.stop_btn.clicked.connect(self.stop_playback)
        layout.addWidget(self.stop_btn)
        
        # Слайдер времени
        layout.addWidget(QLabel("Timeline:"))
        self.time_slider = QSlider(Qt.Orientation.Horizontal)
        self.time_slider.setMinimum(0)
        self.time_slider.setMaximum(100)
        self.time_slider.valueChanged.connect(self.on_slider_changed)
        layout.addWidget(self.time_slider, 1)
        
        # Метка времени
        self.time_label = QLabel("00:00 / 00:00")
        layout.addWidget(self.time_label)
        
        # Скорость воспроизведения
        layout.addWidget(QLabel("Speed:"))
        
        speed_05x = QPushButton("0.5x")
        speed_05x.clicked.connect(lambda: self.set_speed(0.5))
        layout.addWidget(speed_05x)
        
        speed_1x = QPushButton("1x")
        speed_1x.clicked.connect(lambda: self.set_speed(1.0))
        layout.addWidget(speed_1x)
        
        speed_2x = QPushButton("2x")
        speed_2x.clicked.connect(lambda: self.set_speed(2.0))
        layout.addWidget(speed_2x)
        
        speed_4x = QPushButton("4x")
        speed_4x.clicked.connect(lambda: self.set_speed(4.0))
        layout.addWidget(speed_4x)
        
        # Информация
        self.info_label = QLabel("No demo loaded")
        layout.addWidget(self.info_label)
        
        return widget
    
    def load_demo(self, demo_data: dict):
        """
        Загрузка данных демки
        
        Args:
            demo_data: Словарь с данными из парсера
        """
        logger.info(f"Loading demo data: {demo_data.get('map_name', 'Unknown')}")
        
        # Сохраняем данные
        self.positions_data = demo_data.get("positions")
        self.rounds_data = demo_data.get("rounds", [])
        self.kills_data = demo_data.get("kills", [])
        self.map_name = demo_data.get("map_name", "de_dust2")
        
        # Определяем диапазон тиков
        if self.positions_data is not None and not self.positions_data.empty:
            self.max_tick = int(self.positions_data['tick'].max())
            self.current_tick = int(self.positions_data['tick'].min())
        else:
            self.max_tick = 0
            self.current_tick = 0
        
        # Загружаем карту
        self.load_map(self.map_name)
        
        # Обновляем UI
        self.time_slider.setMaximum(self.max_tick)
        self.time_slider.setValue(self.current_tick)
        self.update_info()
        
        # Рендерим первый кадр
        self.render_frame()
        
        logger.info(f"Demo loaded: {self.max_tick} ticks")
    
    def load_map(self, map_name: str):
        """Загрузка карты"""
        logger.info(f"Loading map: {map_name}")
        
        # Создаём рендерер
        self.map_renderer = MapRenderer(map_name, assets_dir="assets/maps")
        
        # Отображаем карту
        self.scene.clear()
        map_pixmap = self.map_renderer.get_map_image()
        self.scene.addPixmap(map_pixmap)
        
        # Подгоняем view под размер карты
        self.view.fitInView(self.scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
        
        logger.info(f"Map loaded: {map_name}")
    
    def toggle_playback(self):
        """Переключение воспроизведения"""
        if self.is_playing:
            self.pause_playback()
        else:
            self.start_playback()
    
    def start_playback(self):
        """Начало воспроизведения"""
        if self.positions_data is None:
            return
        
        self.is_playing = True
        self.play_btn.setText("⏸ Pause")
        
        # Запускаем таймер
        interval = int(1000 / self.fps)  # миллисекунды
        self.timer.start(interval)
        
        self.playback_started.emit()
        self.playback_state_changed.emit("playing")
        logger.debug("Playback started")
    
    def pause_playback(self):
        """Пауза воспроизведения"""
        self.is_playing = False
        self.play_btn.setText("▶ Play")
        self.timer.stop()
        
        self.playback_paused.emit()
        self.playback_state_changed.emit("paused")
        logger.debug("Playback paused")
    
    def stop_playback(self):
        """Остановка воспроизведения"""
        self.is_playing = False
        self.play_btn.setText("▶ Play")
        self.timer.stop()
        
        # Возврат к началу
        self.current_tick = int(self.positions_data['tick'].min()) if self.positions_data is not None else 0
        self.time_slider.setValue(self.current_tick)
        self.render_frame()
        
        self.playback_stopped.emit()
        self.playback_state_changed.emit("stopped")
        logger.debug("Playback stopped")
    
    def update_frame(self):
        """Обновление кадра (вызывается таймером)"""
        if not self.is_playing or self.positions_data is None:
            return
        
        # Вычисляем следующий тик
        ticks_per_frame = (self.tick_rate / self.fps) * self.playback_speed
        self.current_tick += int(ticks_per_frame)
        
        # Проверяем границы
        if self.current_tick >= self.max_tick:
            self.current_tick = self.max_tick
            self.pause_playback()
        
        # Обновляем UI
        self.time_slider.blockSignals(True)
        self.time_slider.setValue(self.current_tick)
        self.time_slider.blockSignals(False)
        
        self.render_frame()
        self.tick_changed.emit(self.current_tick)
    
    def render_frame(self):
        """Отрисовка текущего кадра"""
        if self.positions_data is None or self.map_renderer is None:
            return
        
        # Очищаем предыдущий кадр (кроме фона карты)
        for item in self.scene.items():
            if not isinstance(item, QGraphicsPixmapItem):
                self.scene.removeItem(item)
        
        # Получаем позиции игроков на текущем тике
        current_data = self.positions_data[
            self.positions_data['tick'] == self.current_tick
        ]
        
        if current_data.empty:
            # Интерполяция между тиками
            current_data = self._interpolate_positions(self.current_tick)
        
        # Создаём overlay для рисования
        overlay = QPixmap(self.map_renderer.get_map_image().size())
        overlay.fill(Qt.GlobalColor.transparent)
        painter = QPainter(overlay)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Рисуем убийства (если есть)
        self._draw_kills(painter)
        
        # Рисуем бомбу (если есть)
        self._draw_bomb(painter)
        
        # Рисуем игроков
        for _, player in current_data.iterrows():
            x = player.get('X', 0)
            y = player.get('Y', 0)
            yaw = player.get('yaw', 0)
            health = player.get('health', 100)
            team = player.get('team_name', 'Unknown')
            name = player.get('name', '')
            
            # Цвет команды
            if 'CT' in team or 'Counter' in team:
                color = QColor(100, 150, 255)  # Синий
            elif 'T' in team or 'Terrorist' in team:
                color = QColor(255, 200, 100)  # Жёлтый/оранжевый
            else:
                color = QColor(150, 150, 150)  # Серый
            
            # Рисуем игрока
            self.map_renderer.draw_player(
                painter, x, y, yaw, color, 
                health=int(health),
                name=name,
                size=14,
                show_name=True,
                show_health=False
            )
        
        # Рисуем легенду
        self._draw_legend(painter, current_data)
        
        painter.end()
        
        # Добавляем overlay на сцену
        self.scene.addPixmap(overlay)
        
        # Обновляем информацию
        self.update_info()
    
    def _interpolate_positions(self, target_tick: int):
        """
        Интерполяция позиций между тиками
        
        Args:
            target_tick: Целевой тик
            
        Returns:
            DataFrame с интерполированными позициями
        """
        # Находим ближайшие тики
        before = self.positions_data[self.positions_data['tick'] <= target_tick]
        after = self.positions_data[self.positions_data['tick'] > target_tick]
        
        if before.empty:
            return after.head(1)
        if after.empty:
            return before.tail(1)
        
        tick_before = before['tick'].max()
        tick_after = after['tick'].min()
        
        # Линейная интерполяция
        alpha = (target_tick - tick_before) / (tick_after - tick_before)
        
        data_before = before[before['tick'] == tick_before]
        data_after = after[after['tick'] == tick_after]
        
        # Простая интерполяция (можно улучшить)
        result = data_before.copy()
        
        for col in ['X', 'Y', 'Z', 'yaw']:
            if col in data_before.columns and col in data_after.columns:
                result[col] = data_before[col] * (1 - alpha) + data_after[col] * alpha
        
        return result
    
    def _draw_kills(self, painter: QPainter):
        """Отрисовка убийств на текущем тике"""
        if self.kills_data is None:
            return
        
        # Показываем убийства из последних 5 секунд
        tick_window = self.tick_rate * 5
        
        recent_kills = [
            k for k in self.kills_data
            if self.current_tick - tick_window <= k.get('tick', 0) <= self.current_tick
        ]
        
        for kill in recent_kills:
            x = kill.get('victim_X', 0)
            y = kill.get('victim_Y', 0)
            weapon = kill.get('weapon', '')
            headshot = kill.get('headshot', False)
            
            self.map_renderer.draw_kill(
                painter, x, y, weapon, headshot, 
                show_weapon_icon=True
            )
    
    def _draw_bomb(self, painter: QPainter):
        """Отрисовка бомбы"""
        if self.positions_data is None:
            return
        
        # Ищем игрока с бомбой
        current_data = self.positions_data[
            self.positions_data['tick'] == self.current_tick
        ]
        
        for _, player in current_data.iterrows():
            # Проверяем, есть ли у игрока бомба
            has_bomb = player.get('has_bomb', False)
            if has_bomb:
                x = player.get('X', 0)
                y = player.get('Y', 0)
                
                # Пульсация для посаженной бомбы
                import math
                pulse = int(127 + 128 * math.sin(self.current_tick / 10))
                
                self.map_renderer.draw_bomb(
                    painter, x, y, 
                    planted=False,
                    pulse_alpha=pulse
                )
                break
    
    def _draw_legend(self, painter: QPainter, current_data):
        """Отрисовка легенды с информацией"""
        if current_data.empty:
            return
        
        # Подсчитываем живых игроков
        ct_alive = len(current_data[
            (current_data['team_name'].str.contains('CT', case=False)) & 
            (current_data['health'] > 0)
        ])
        
        t_alive = len(current_data[
            (current_data['team_name'].str.contains('T', case=False)) & 
            (current_data['health'] > 0)
        ])
        
        # Получаем текущий раунд
        current_round = self._get_current_round()
        round_num = current_round.get('round_num', 0) if current_round else 0
        max_rounds = len(self.rounds_data) if self.rounds_data else 0
        
        # Рисуем легенду в верхнем левом углу
        self.map_renderer.draw_legend(
            painter, 10, 10,
            ct_alive, t_alive,
            round_num, max_rounds
        )
    
    def on_slider_changed(self, value: int):
        """Обработчик изменения слайдера"""
        self.current_tick = value
        self.render_frame()
    
    def set_speed(self, speed: float):
        """Установка скорости воспроизведения"""
        self.playback_speed = speed
        logger.debug(f"Playback speed set to {speed}x")
    
    def update_info(self):
        """Обновление информационных меток"""
        # Время
        current_time = self.current_tick / self.tick_rate
        max_time = self.max_tick / self.tick_rate
        
        current_str = f"{int(current_time // 60):02d}:{int(current_time % 60):02d}"
        max_str = f"{int(max_time // 60):02d}:{int(max_time % 60):02d}"
        
        self.time_label.setText(f"{current_str} / {max_str}")
        
        # Информация о раунде
        current_round = self._get_current_round()
        if current_round:
            round_num = current_round.get('round_num', 0)
            self.info_label.setText(
                f"Round {round_num} | "
                f"Tick {self.current_tick} / {self.max_tick} | "
                f"Speed {self.playback_speed}x"
            )
        else:
            self.info_label.setText(
                f"Tick {self.current_tick} / {self.max_tick} | "
                f"Speed {self.playback_speed}x"
            )
    
    def _get_current_round(self) -> Optional[dict]:
        """Получить текущий раунд"""
        for round_data in self.rounds_data:
            start = round_data.get('start_tick', 0)
            end = round_data.get('end_tick', 0)
            if start <= self.current_tick <= end:
                return round_data
        return None
    
    def resizeEvent(self, event):
        """Обработка изменения размера"""
        super().resizeEvent(event)
        if self.scene:
            self.view.fitInView(
                self.scene.sceneRect(), 
                Qt.AspectRatioMode.KeepAspectRatio
            )