"""
Виджет для 2D визуализации демо файлов
Отображает карту и позиции игроков
"""
from pathlib import Path
from typing import Optional

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel
from PyQt6.QtCore import Qt, QTimer, QRectF, QPointF, pyqtSignal
from PyQt6.QtGui import QPainter, QPixmap, QColor, QPen, QBrush, QFont

from ..core.models import Match, GameFrame, Player, Team
from ..core.map_renderer import MapRenderer
from ..utils.logger import log
from ..utils.config import config


class MapCanvas(QWidget):
    """Canvas для отрисовки карты и игроков"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(800, 600)
        
        # Данные
        self.map_image: Optional[QPixmap] = None
        self.renderer: Optional[MapRenderer] = None
        self.current_frame: Optional[GameFrame] = None
        
        # Настройки отрисовки
        self.player_size = 6  # Уменьшено с 12 до 6
        self.show_names = True
        self.show_health = True
        self.debug_mode = False  # Debug режим
        
        # Цвета команд
        self.t_color = QColor(255, 150, 0)  # Оранжевый
        self.ct_color = QColor(100, 150, 255)  # Синий
        self.dead_color = QColor(128, 128, 128)  # Серый
        
        log.debug("MapCanvas initialized")
    
    def load_map(self, map_name: str):
        """
        Загрузка изображения карты
        
        Args:
            map_name: Название карты
        """
        # Создаём рендерер
        self.renderer = MapRenderer(
            map_name,
            self.width(),
            self.height()
        )
        
        # Загружаем изображение
        map_path = self.renderer.get_map_image_path()
        
        if map_path and map_path.exists():
            self.map_image = QPixmap(str(map_path))
            log.info(f"Map image loaded: {map_name}")
        else:
            self.map_image = None
            log.warning(f"Map image not found for: {map_name}")
        
        self.update()
    
    def set_frame(self, frame: GameFrame):
        """
        Установить текущий фрейм для отрисовки
        
        Args:
            frame: GameFrame с позициями игроков
        """
        self.current_frame = frame
        self.update()
    
    def paintEvent(self, event):
        """Отрисовка canvas"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Фон
        painter.fillRect(self.rect(), QColor(40, 40, 40))
        
        # Рисуем область карты (вместо изображения)
        if self.renderer:
            map_width = self.renderer.bounds.width * self.renderer.scale
            map_height = self.renderer.bounds.height * self.renderer.scale
            
            # Рисуем фон карты
            map_rect = QRectF(
                self.renderer.offset_x,
                self.renderer.offset_y,
                map_width,
                map_height
            )
            painter.fillRect(map_rect, QColor(60, 60, 60))
            
            # Если есть изображение карты, пытаемся его нарисовать
            if self.map_image:
                self._draw_map(painter)
        
        # Debug информация
        if self.debug_mode and self.renderer:
            painter.setPen(QPen(QColor(255, 255, 0)))
            painter.setFont(QFont("Arial", 10))
            debug_text = (
                f"Canvas: {self.width()}x{self.height()} | "
                f"Bounds: ({self.renderer.bounds.min_x:.0f}, {self.renderer.bounds.min_y:.0f}) to "
                f"({self.renderer.bounds.max_x:.0f}, {self.renderer.bounds.max_y:.0f}) | "
                f"Scale: {self.renderer.scale:.3f} | "
                f"Offset: ({self.renderer.offset_x:.0f}, {self.renderer.offset_y:.0f})"
            )
            painter.drawText(10, 20, debug_text)
        
        # Игроки
        if self.current_frame and self.renderer:
            self._draw_players(painter)
        
        # Debug: рисуем границы карты
        if self.debug_mode and self.renderer:
            painter.setPen(QPen(QColor(255, 0, 0), 2))
            map_width = self.renderer.bounds.width * self.renderer.scale
            map_height = self.renderer.bounds.height * self.renderer.scale
            painter.drawRect(
                int(self.renderer.offset_x),
                int(self.renderer.offset_y),
                int(map_width),
                int(map_height)
            )
    
    def _draw_map(self, painter: QPainter):
        """Отрисовка изображения карты"""
        if not self.renderer:
            return
        
        # Вычисляем размеры области карты (в пикселях)
        map_width = self.renderer.bounds.width * self.renderer.scale
        map_height = self.renderer.bounds.height * self.renderer.scale
        
        # Используем точные смещения из renderer
        x = self.renderer.offset_x
        y = self.renderer.offset_y
        
        # Масштабируем изображение карты ТОЧНО под область координат
        # Изображение 1024x1024 растягиваем под bounds
        scaled_map = self.map_image.scaled(
            int(map_width),
            int(map_height),
            Qt.AspectRatioMode.IgnoreAspectRatio,  # Игнорируем соотношение сторон
            Qt.TransformationMode.SmoothTransformation
        )
        
        # Рисуем изображение точно в области координат
        painter.drawPixmap(int(x), int(y), scaled_map)
    
    def _draw_placeholder(self, painter: QPainter):
        """Отрисовка placeholder когда карта не загружена"""
        painter.setPen(QPen(QColor(100, 100, 100)))
        painter.setFont(QFont("Arial", 16))
        painter.drawText(
            self.rect(),
            Qt.AlignmentFlag.AlignCenter,
            "Map not loaded"
        )
    
    def _draw_players(self, painter: QPainter):
        """Отрисовка игроков"""
        for player_frame in self.current_frame.players:
            self._draw_player(painter, player_frame)
    
    def _draw_player(self, painter: QPainter, player_frame):
        """
        Отрисовка одного игрока
        
        Args:
            painter: QPainter
            player_frame: PlayerFrame с информацией об игроке
        """
        # Конвертируем координаты
        screen_x, screen_y = self.renderer.game_to_screen(player_frame.position)
        
        # Определяем цвет
        if not player_frame.is_alive:
            color = self.dead_color
        elif player_frame.player.team == Team.T:
            color = self.t_color
        elif player_frame.player.team == Team.CT:
            color = self.ct_color
        else:
            color = QColor(200, 200, 200)
        
        # Рисуем маркер игрока
        painter.setPen(QPen(color, 2))
        painter.setBrush(QBrush(color if player_frame.is_alive else Qt.BrushStyle.NoBrush))
        
        # Круг
        painter.drawEllipse(
            QPointF(screen_x, screen_y),
            self.player_size,
            self.player_size
        )
        
        # Линия направления взгляда (view angle)
        if player_frame.is_alive:
            import math
            angle_rad = math.radians(player_frame.view_angle)
            line_length = self.player_size * 2
            
            end_x = screen_x + math.cos(angle_rad) * line_length
            end_y = screen_y - math.sin(angle_rad) * line_length
            
            painter.setPen(QPen(color, 2))
            painter.drawLine(
                QPointF(screen_x, screen_y),
                QPointF(end_x, end_y)
            )
        
        # Имя игрока
        if self.show_names:
            painter.setPen(QPen(QColor(255, 255, 255)))
            painter.setFont(QFont("Arial", 8))
            
            text_rect = QRectF(
                screen_x - 50,
                screen_y - self.player_size - 15,
                100,
                15
            )
            
            painter.drawText(
                text_rect,
                Qt.AlignmentFlag.AlignCenter,
                player_frame.player.name
            )
        
        # Здоровье
        if self.show_health and player_frame.is_alive:
            painter.setPen(QPen(QColor(255, 255, 255)))
            painter.setFont(QFont("Arial", 7))
            
            health_rect = QRectF(
                screen_x - 20,
                screen_y + self.player_size + 2,
                40,
                12
            )
            
            # Цвет здоровья
            health_color = self._get_health_color(player_frame.health)
            painter.setPen(QPen(health_color))
            
            painter.drawText(
                health_rect,
                Qt.AlignmentFlag.AlignCenter,
                f"{player_frame.health}"
            )
    
    def _get_health_color(self, health: int) -> QColor:
        """Цвет в зависимости от здоровья"""
        if health > 75:
            return QColor(0, 255, 0)  # Зелёный
        elif health > 50:
            return QColor(255, 255, 0)  # Жёлтый
        elif health > 25:
            return QColor(255, 165, 0)  # Оранжевый
        else:
            return QColor(255, 0, 0)  # Красный
    
    def resizeEvent(self, event):
        """Обработка изменения размера"""
        super().resizeEvent(event)
        if self.renderer:
            self.renderer.resize_canvas(self.width(), self.height())
    
    def toggle_names(self):
        """Переключить отображение имён"""
        self.show_names = not self.show_names
        self.update()
    
    def toggle_health(self):
        """Переключить отображение здоровья"""
        self.show_health = not self.show_health
        self.update()
    
    def toggle_debug(self):
        """Переключить debug режим"""
        self.debug_mode = not self.debug_mode
        self.update()


class DemoViewer(QWidget):
    """
    Главный виджет для просмотра демо
    Включает canvas и информационную панель
    """
    
    # Сигналы
    playback_state_changed = pyqtSignal(bool)  # playing: bool
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.match: Optional[Match] = None
        self.frames: list[GameFrame] = []
        self.current_frame_index = 0
        self.is_playing = False
        self.playback_speed = 1.0  # Множитель скорости
        
        # Интерполяция для плавной анимации
        self.interpolation_progress = 0.0  # 0.0 - 1.0 между frames
        self.interpolated_frame: Optional[GameFrame] = None
        
        # Таймер для воспроизведения
        self.playback_timer = QTimer()
        self.playback_timer.timeout.connect(self._advance_frame)
        # Используем 60 FPS для плавной анимации
        self.render_fps = 60  # FPS отрисовки
        
        # Скорость переключения frames (4 FPS = реальное время)
        self.game_fps = 4  # Скорость переключения game frames
        
        # Таймер для обновления UI
        self.ui_update_timer = QTimer()
        self.ui_update_timer.timeout.connect(self._update_ui)
        self.ui_update_timer.start(100)  # Обновляем UI каждые 100мс
        
        self._init_ui()
        
        log.debug("DemoViewer initialized")
    
    def _init_ui(self):
        """Инициализация UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Canvas для карты
        self.canvas = MapCanvas()
        layout.addWidget(self.canvas)
        
        # Информационная панель
        info_layout = QHBoxLayout()
        
        self.round_label = QLabel("Round: -")
        self.tick_label = QLabel("Tick: -")
        self.time_label = QLabel("Time: -")
        
        info_layout.addWidget(self.round_label)
        info_layout.addWidget(self.tick_label)
        info_layout.addWidget(self.time_label)
        info_layout.addStretch()
        
        layout.addLayout(info_layout)
    
    def load_match(self, match: Match, frames: list[GameFrame]):
        """
        Загрузить матч для просмотра
        
        Args:
            match: Match объект
            frames: Список GameFrame для воспроизведения
        """
        self.match = match
        self.frames = frames
        self.current_frame_index = 0
        
        # Загружаем карту
        self.canvas.load_map(match.map_name)
        
        # Показываем первый фрейм
        if self.frames:
            self._show_frame(0)
        
        log.info(
            f"Match loaded: {match.map_name}, "
            f"{len(frames)} frames, "
            f"{len(match.players)} players"
        )
    
    def _show_frame(self, index: int):
        """Показать фрейм по индексу"""
        if 0 <= index < len(self.frames):
            frame = self.frames[index]
            self.current_frame_index = index
            
            # Обновляем canvas
            self.canvas.set_frame(frame)
            
            # Обновляем информацию
            self.round_label.setText(f"Round: {frame.round_number}")
            self.tick_label.setText(f"Tick: {frame.tick}")
            self.time_label.setText(f"Time: {frame.time_seconds:.1f}s")
    
    def play(self):
        """Начать воспроизведение"""
        if not self.frames:
            return
        
        self.is_playing = True
        # 60 FPS для плавной отрисовки
        interval = int(1000 / self.render_fps)  # ~16.6 мс
        self.playback_timer.start(interval)
        self.playback_state_changed.emit(True)
        log.debug(f"Playback started (speed: {self.playback_speed}x, {self.render_fps} FPS)")
    
    def set_speed(self, speed: float):
        """
        Установить скорость воспроизведения
        
        Args:
            speed: Множитель (0.5 = половина скорости, 2.0 = двойная)
        """
        self.playback_speed = speed
        log.debug(f"Playback speed set to {speed}x")
    
    def pause(self):
        """Пауза"""
        self.is_playing = False
        self.playback_timer.stop()
        self.playback_state_changed.emit(False)
        log.debug("Playback paused")
    
    def stop(self):
        """Остановить и вернуться к началу"""
        self.pause()
        self.seek(0)
        log.debug("Playback stopped")
    
    def seek(self, frame_index: int):
        """
        Перейти к фрейму
        
        Args:
            frame_index: Индекс фрейма
        """
        if 0 <= frame_index < len(self.frames):
            self.current_frame_index = frame_index
            self.interpolation_progress = 0.0  # Сбрасываем интерполяцию
            self._show_frame(frame_index)
    
    def _advance_frame(self):
        """Переход к следующему фрейму (60 FPS с интерполяцией)"""
        if not self.frames or self.current_frame_index >= len(self.frames) - 1:
            self.pause()
            return
        
        # Вычисляем шаг интерполяции
        # При game_fps=4 и render_fps=60: нужно 60/4 = 15 шагов между frames
        steps_per_frame = self.render_fps / self.game_fps
        step_size = 1.0 / steps_per_frame
        
        # Увеличиваем прогресс с учётом скорости
        self.interpolation_progress += step_size * self.playback_speed
        
        # Если прошли весь frame, переходим к следующему
        if self.interpolation_progress >= 1.0:
            self.current_frame_index += 1
            self.interpolation_progress = 0.0
            
            if self.current_frame_index >= len(self.frames) - 1:
                self.pause()
                return
        
        # Создаём интерполированный frame
        self._create_interpolated_frame()
        
        # Обновляем отрисовку
        self.canvas.update()
    
    def _create_interpolated_frame(self):
        """Создание интерполированного frame между двумя game frames"""
        if self.current_frame_index >= len(self.frames) - 1:
            self.interpolated_frame = self.frames[self.current_frame_index]
            self.canvas.set_frame(self.interpolated_frame)
            return
        
        current = self.frames[self.current_frame_index]
        next_frame = self.frames[self.current_frame_index + 1]
        
        # Создаём новый frame
        from ..core.models import GameFrame, PlayerFrame, Position
        
        interpolated = GameFrame(
            tick=current.tick,
            time_seconds=current.time_seconds,
            round_number=current.round_number,
        )
        
        # Интерполируем позиции каждого игрока
        for current_pf in current.players:
            # Находим того же игрока в следующем frame
            next_pf = None
            for npf in next_frame.players:
                if npf.player.steam_id == current_pf.player.steam_id:
                    next_pf = npf
                    break
            
            if next_pf is None:
                # Игрок не найден в следующем frame, используем текущую позицию
                interpolated.players.append(current_pf)
                continue
            
            # Линейная интерполяция позиции
            t = self.interpolation_progress
            x = current_pf.position.x + (next_pf.position.x - current_pf.position.x) * t
            y = current_pf.position.y + (next_pf.position.y - current_pf.position.y) * t
            z = current_pf.position.z + (next_pf.position.z - current_pf.position.z) * t
            
            # Интерполяция угла (с учётом кругового характера)
            angle_diff = next_pf.view_angle - current_pf.view_angle
            # Нормализуем разницу углов (-180 до 180)
            while angle_diff > 180:
                angle_diff -= 360
            while angle_diff < -180:
                angle_diff += 360
            view_angle = current_pf.view_angle + angle_diff * t
            
            # Создаём интерполированный PlayerFrame
            interpolated_pf = PlayerFrame(
                tick=current.tick,
                time_seconds=current.time_seconds,
                player=current_pf.player,
                position=Position(x, y, z),
                view_angle=view_angle,
                health=current_pf.health,  # Здоровье не интерполируем
                armor=current_pf.armor,
                is_alive=current_pf.is_alive,
                active_weapon=current_pf.active_weapon,
            )
            
            interpolated.players.append(interpolated_pf)
        
        self.interpolated_frame = interpolated
        self.canvas.set_frame(self.interpolated_frame)
    
    def get_progress(self) -> float:
        """
        Получить прогресс воспроизведения
        
        Returns:
            Прогресс от 0.0 до 1.0
        """
        if not self.frames:
            return 0.0
        return self.current_frame_index / (len(self.frames) - 1)
    
    def set_progress(self, progress: float):
        """
        Установить прогресс воспроизведения
        
        Args:
            progress: Значение от 0.0 до 1.0
        """
        if not self.frames:
            return
        
        frame_index = int(progress * (len(self.frames) - 1))
        self.seek(frame_index)
    
    def _update_ui(self):
        """Периодическое обновление UI"""
        if self.is_playing and self.frames:
            # Можно добавить дополнительные обновления здесь
            pass