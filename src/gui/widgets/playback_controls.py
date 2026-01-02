
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QPushButton, QSlider, QLabel, QStyle
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QIcon


class PlaybackControls(QWidget):
    """Панель контролов для воспроизведения"""
    
    # Сигналы
    play_clicked = pyqtSignal()
    pause_clicked = pyqtSignal()
    stop_clicked = pyqtSignal()
    seek_requested = pyqtSignal(float)  # progress (0.0 - 1.0)
    speed_changed = pyqtSignal(float)  # speed multiplier
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_playing = False
        self._init_ui()
    
    def _init_ui(self):
        """Инициализация UI"""
        layout = QHBoxLayout(self)
        
        # Кнопки управления
        self.play_pause_btn = QPushButton("▶ Play")
        self.play_pause_btn.clicked.connect(self._on_play_pause_clicked)
        self.play_pause_btn.setFixedWidth(100)
        layout.addWidget(self.play_pause_btn)
        
        self.stop_btn = QPushButton("⏹ Stop")
        self.stop_btn.clicked.connect(self.stop_clicked.emit)
        self.stop_btn.setFixedWidth(80)
        layout.addWidget(self.stop_btn)
        
        # Прогресс бар (slider)
        self.progress_slider = QSlider(Qt.Orientation.Horizontal)
        self.progress_slider.setMinimum(0)
        self.progress_slider.setMaximum(1000)  # 1000 шагов для плавности
        self.progress_slider.setValue(0)
        self.progress_slider.sliderPressed.connect(self._on_slider_pressed)
        self.progress_slider.sliderReleased.connect(self._on_slider_released)
        self.progress_slider.valueChanged.connect(self._on_slider_changed)
        layout.addWidget(self.progress_slider, stretch=1)
        
        # Метка времени
        self.time_label = QLabel("00:00 / 00:00")
        self.time_label.setFixedWidth(120)
        layout.addWidget(self.time_label)
        
        # Скорость воспроизведения
        speed_label = QLabel("Speed:")
        layout.addWidget(speed_label)
        
        self.speed_0_5x_btn = QPushButton("0.5x")
        self.speed_0_5x_btn.setFixedWidth(50)
        self.speed_0_5x_btn.clicked.connect(lambda: self.speed_changed.emit(0.5))
        layout.addWidget(self.speed_0_5x_btn)
        
        self.speed_1x_btn = QPushButton("1x")
        self.speed_1x_btn.setFixedWidth(50)
        self.speed_1x_btn.clicked.connect(lambda: self.speed_changed.emit(1.0))
        self.speed_1x_btn.setStyleSheet("font-weight: bold;")
        layout.addWidget(self.speed_1x_btn)
        
        self.speed_2x_btn = QPushButton("2x")
        self.speed_2x_btn.setFixedWidth(50)
        self.speed_2x_btn.clicked.connect(lambda: self.speed_changed.emit(2.0))
        layout.addWidget(self.speed_2x_btn)
        
        # Стили
        self.setStyleSheet("""
            QPushButton {
                padding: 8px;
                background-color: #2196f3;
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #1976d2;
            }
            QPushButton:pressed {
                background-color: #0d47a1;
            }
            QSlider::groove:horizontal {
                height: 8px;
                background: #ddd;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                width: 18px;
                height: 18px;
                margin: -5px 0;
                background: #2196f3;
                border-radius: 9px;
            }
            QSlider::handle:horizontal:hover {
                background: #1976d2;
            }
            QLabel {
                color: #333;
                font-size: 12px;
            }
        """)
        
        self._slider_pressed = False
    
    def _on_play_pause_clicked(self):
        """Обработка клика на play/pause"""
        if self.is_playing:
            self.pause_clicked.emit()
        else:
            self.play_clicked.emit()
    
    def set_playing_state(self, is_playing: bool):
        """
        Установить состояние воспроизведения
        
        Args:
            is_playing: True если играет
        """
        self.is_playing = is_playing
        
        if is_playing:
            self.play_pause_btn.setText("⏸ Pause")
        else:
            self.play_pause_btn.setText("▶ Play")
    
    def set_progress(self, progress: float):
        """
        Установить прогресс
        
        Args:
            progress: Значение от 0.0 до 1.0
        """
        if not self._slider_pressed:
            value = int(progress * 1000)
            self.progress_slider.setValue(value)
    
    def set_time(self, current_seconds: float, total_seconds: float):
        """
        Установить время
        
        Args:
            current_seconds: Текущее время
            total_seconds: Общее время
        """
        current_str = self._format_time(current_seconds)
        total_str = self._format_time(total_seconds)
        self.time_label.setText(f"{current_str} / {total_str}")
    
    def _format_time(self, seconds: float) -> str:
        """
        Форматирование времени
        
        Args:
            seconds: Секунды
        
        Returns:
            Строка вида "MM:SS"
        """
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes:02d}:{secs:02d}"
    
    def _on_slider_pressed(self):
        """Обработка нажатия на slider"""
        self._slider_pressed = True
    
    def _on_slider_released(self):
        """Обработка отпускания slider"""
        self._slider_pressed = False
        # Отправляем событие seek
        progress = self.progress_slider.value() / 1000.0
        self.seek_requested.emit(progress)
    
    def _on_slider_changed(self, value: int):
        """Обработка изменения slider"""
        if self._slider_pressed:
            # Обновляем только время, не отправляем seek
            progress = value / 1000.0
            # Время будет обновлено через set_time
    
    def enable_controls(self, enabled: bool):
        """
        Включить/выключить контролы
        
        Args:
            enabled: True для включения
        """
        self.play_pause_btn.setEnabled(enabled)
        self.stop_btn.setEnabled(enabled)
        self.progress_slider.setEnabled(enabled)
        self.speed_0_5x_btn.setEnabled(enabled)
        self.speed_1x_btn.setEnabled(enabled)
        self.speed_2x_btn.setEnabled(enabled)