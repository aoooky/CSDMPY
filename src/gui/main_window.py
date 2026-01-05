
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFileDialog, QSplitter,
    QListWidget, QListWidgetItem, QMessageBox, QStatusBar,
    QMenuBar, QMenu, QToolBar
)
from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtGui import QAction, QIcon
from pathlib import Path
from loguru import logger
import asyncio

from ..utils.config import config
from ..utils.logger import log
from ..core.models import Match
from .parser_worker import ParserManager
from .demo_viewer import DemoViewer
from .stats_panel import StatsPanel
from .widgets.playback_controls import PlaybackControls
from .matches_browser import MatchesBrowser


class MainWindow(QMainWindow):
    """Главное окно приложения"""
    
    # Сигналы
    demo_selected = pyqtSignal(str)  # Путь к выбранной демке
    demo_parse_requested = pyqtSignal(str)  # Запрос на парсинг демки
    
    def __init__(self):
        super().__init__()
        self.current_demo_path: str | None = None
        self.demo_paths: list[str] = []
        self.current_match: Match | None = None
        
        # Создаём менеджер парсера
        self.parser_manager = ParserManager()
        self._connect_parser_signals()
        
        self._init_ui()
        self._create_menu_bar()
        self._create_toolbar()
        self._create_status_bar()
        
        log.info("Main window initialized")
    
    def _connect_parser_signals(self):
        """Подключение сигналов парсера"""
        self.parser_manager.parse_started.connect(self._on_parse_started)
        self.parser_manager.parse_progress.connect(self._on_parse_progress)
        self.parser_manager.parse_finished.connect(self._on_parse_finished)
        self.parser_manager.parse_error.connect(self._on_parse_error)
    
    def _init_ui(self):
        """Инициализация UI"""
        self.setWindowTitle(config.window_title)
        self.setGeometry(100, 100, config.window_width, config.window_height)
        
        # Центральный виджет
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Главный layout
        main_layout = QHBoxLayout(central_widget)
        
        # Создаём сплиттер для разделения панелей
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Левая панель - список демок
        self.demo_list_widget = self._create_demo_list_panel()
        splitter.addWidget(self.demo_list_widget)
        
        # Правая панель - просмотр и статистика
        right_panel = self._create_right_panel()
        splitter.addWidget(right_panel)
        
        # Устанавливаем пропорции сплиттера (1:3)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)
        
        main_layout.addWidget(splitter)
    
    def _create_demo_list_panel(self) -> QWidget:
        """Создание панели со списком демок"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # Заголовок
        title = QLabel("📁 Demo Files")
        title.setStyleSheet("font-size: 14px; font-weight: bold; padding: 5px;")
        layout.addWidget(title)
        
        # Кнопки управления
        buttons_layout = QHBoxLayout()
        
        add_btn = QPushButton("➕ Add Demo")
        add_btn.clicked.connect(self.add_demo_file)
        add_btn.setToolTip("Add .dem file")
        buttons_layout.addWidget(add_btn)
        
        add_folder_btn = QPushButton("📂 Add Folder")
        add_folder_btn.clicked.connect(self.add_demo_folder)
        add_folder_btn.setToolTip("Add all .dem files from folder")
        buttons_layout.addWidget(add_folder_btn)
        
        layout.addLayout(buttons_layout)
        
        # Список демок
        self.demo_list = QListWidget()
        self.demo_list.itemClicked.connect(self._on_demo_selected)
        self.demo_list.setStyleSheet("""
            QListWidget {
                border: 1px solid #ccc;
                border-radius: 4px;
                padding: 5px;
                background-color: #f9f9f9;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #eee;
            }
            QListWidget::item:hover {
                background-color: #e3f2fd;
            }
            QListWidget::item:selected {
                background-color: #2196f3;
                color: white;
            }
        """)
        layout.addWidget(self.demo_list)
        
        # Кнопка парсинга
        self.parse_btn = QPushButton("🔍 Parse Selected Demo")
        self.parse_btn.clicked.connect(self._on_parse_clicked)
        self.parse_btn.setEnabled(False)
        self.parse_btn.setStyleSheet("""
            QPushButton {
                padding: 10px;
                font-size: 13px;
                font-weight: bold;
                background-color: #4caf50;
                color: white;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        layout.addWidget(self.parse_btn)
        
        return panel
    
    def _create_right_panel(self) -> QWidget:
        """Создание правой панели (просмотр и статистика)"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Создаём табы для переключения между просмотром и статистикой
        from PyQt6.QtWidgets import QTabWidget
        tabs = QTabWidget()
        
        # Таб 1: Визуализация
        self.demo_viewer = DemoViewer()
        tabs.addTab(self.demo_viewer, "🎬 Viewer")
        
        # Таб 2: Статистика
        self.stats_panel = StatsPanel()
        tabs.addTab(self.stats_panel, "📊 Statistics")
        
        # Таб 3: База данных (История)
        self.matches_browser = MatchesBrowser()
        self.matches_browser.match_selected.connect(self._on_match_from_db_selected)
        self.matches_browser.match_deleted.connect(self._on_match_deleted)
        tabs.addTab(self.matches_browser, "💾 Database")
        
        # Обновляем браузер при переключении на таб
        tabs.currentChanged.connect(self._on_tab_changed)
        
        layout.addWidget(tabs)
        
        # Контролы воспроизведения
        self.playback_controls = PlaybackControls()
        self.playback_controls.play_clicked.connect(self._on_play_clicked)
        self.playback_controls.pause_clicked.connect(self._on_pause_clicked)
        self.playback_controls.stop_clicked.connect(self._on_stop_clicked)
        self.playback_controls.seek_requested.connect(self._on_seek_requested)
        self.playback_controls.speed_changed.connect(self._on_speed_changed)
        self.playback_controls.enable_controls(False)  # Изначально отключены
        layout.addWidget(self.playback_controls)
        
        # Подключаем сигнал изменения состояния воспроизведения
        self.demo_viewer.playback_state_changed.connect(
            self.playback_controls.set_playing_state
        )
        
        # Таймер для обновления прогресса
        from PyQt6.QtCore import QTimer
        self.progress_timer = QTimer()
        self.progress_timer.timeout.connect(self._update_playback_progress)
        self.progress_timer.start(100)  # Обновляем каждые 100мс
        
        return panel
    
    def _create_menu_bar(self):
        """Создание меню"""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("&File")
        
        add_demo_action = QAction("&Add Demo", self)
        add_demo_action.setShortcut("Ctrl+O")
        add_demo_action.triggered.connect(self.add_demo_file)
        file_menu.addAction(add_demo_action)
        
        add_folder_action = QAction("Add &Folder", self)
        add_folder_action.setShortcut("Ctrl+Shift+O")
        add_folder_action.triggered.connect(self.add_demo_folder)
        file_menu.addAction(add_folder_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("E&xit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # View menu
        view_menu = menubar.addMenu("&View")
        
        refresh_action = QAction("&Refresh", self)
        refresh_action.setShortcut("F5")
        refresh_action.triggered.connect(self.refresh_demo_list)
        view_menu.addAction(refresh_action)
        
        view_menu.addSeparator()
        
        debug_action = QAction("&Debug Mode", self)
        debug_action.setShortcut("F12")
        debug_action.setCheckable(True)
        debug_action.triggered.connect(self._toggle_debug_mode)
        view_menu.addAction(debug_action)
        
        # Help menu
        help_menu = menubar.addMenu("&Help")
        
        about_action = QAction("&About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
    def _create_toolbar(self):
        """Создание тулбара"""
        toolbar = QToolBar("Main Toolbar")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)
        
        # Кнопки тулбара
        add_action = QAction("➕ Add Demo", self)
        add_action.triggered.connect(self.add_demo_file)
        toolbar.addAction(add_action)
        
        toolbar.addSeparator()
        
        parse_action = QAction("🔍 Parse", self)
        parse_action.triggered.connect(self._on_parse_clicked)
        toolbar.addAction(parse_action)
    
    def _create_status_bar(self):
        """Создание статус бара"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")
    
    def add_demo_file(self):
        """Добавление одного .dem файла"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Demo File",
            str(config.demos_dir),
            "Demo Files (*.dem);;All Files (*)"
        )
        
        if file_path:
            self._add_demo_to_list(file_path)
            log.info(f"Added demo: {file_path}")
            self.status_bar.showMessage(f"Added: {Path(file_path).name}", 3000)
    
    def add_demo_folder(self):
        """Добавление всех .dem файлов из папки"""
        folder_path = QFileDialog.getExistingDirectory(
            self,
            "Select Folder with Demos",
            str(config.demos_dir)
        )
        
        if folder_path:
            demo_files = list(Path(folder_path).glob("*.dem"))
            
            if not demo_files:
                QMessageBox.warning(
                    self,
                    "No Demos Found",
                    f"No .dem files found in {folder_path}"
                )
                return
            
            for demo_file in demo_files:
                self._add_demo_to_list(str(demo_file))
            
            log.info(f"Added {len(demo_files)} demos from {folder_path}")
            self.status_bar.showMessage(f"Added {len(demo_files)} demo files", 3000)
    
    def _add_demo_to_list(self, file_path: str):
        """Добавление демки в список"""
        if file_path not in self.demo_paths:
            self.demo_paths.append(file_path)
            
            item = QListWidgetItem(Path(file_path).name)
            item.setData(Qt.ItemDataRole.UserRole, file_path)
            item.setToolTip(file_path)
            self.demo_list.addItem(item)
    
    def _on_demo_selected(self, item: QListWidgetItem):
        """Обработка выбора демки"""
        demo_path = item.data(Qt.ItemDataRole.UserRole)
        self.current_demo_path = demo_path
        self.parse_btn.setEnabled(True)
        
        log.debug(f"Demo selected: {demo_path}")
        self.status_bar.showMessage(f"Selected: {Path(demo_path).name}")
        
        self.demo_selected.emit(demo_path)
    
    def _on_parse_clicked(self):
        """Обработка клика на кнопку парсинга"""
        if not self.current_demo_path:
            QMessageBox.warning(self, "No Demo Selected", "Please select a demo file first")
            return
        
        # Проверяем что парсинг не запущен
        if self.parser_manager.is_parsing():
            QMessageBox.warning(self, "Parser Busy", "Parsing is already in progress")
            return
        
        self.status_bar.showMessage(f"Starting parse: {Path(self.current_demo_path).name}...")
        log.info(f"Starting parse: {self.current_demo_path}")
        
        # Отключаем кнопку во время парсинга
        self.parse_btn.setEnabled(False)
        self.parse_btn.setText("⏳ Parsing...")
        
        # Запускаем парсинг
        self.parser_manager.parse_demo(self.current_demo_path)
    
    def _on_parse_started(self, demo_path: str):
        """Обработка начала парсинга"""
        self.status_bar.showMessage(f"Parsing: {Path(demo_path).name}...")
        log.info(f"Parse started: {demo_path}")
    
    def _on_parse_progress(self, message: str, percentage: int):
        """Обработка прогресса парсинга"""
        self.status_bar.showMessage(f"{message} ({percentage}%)")
    
    def _on_parse_finished(self, demo_path, frames=None):
        """Обработчик завершения парсинга"""
        from pathlib import Path
        logger.info(f"Parse finished: {demo_path}")
        
        # Показываем уведомление
        demo_name = Path(demo_path).name
        logger.info(f"✅ Successfully parsed: {demo_name}")
        
    
    def _on_parse_error(self, error: str, demo_path: str):
        """Обработка ошибки парсинга"""
        QMessageBox.critical(
            self,
            "Parse Error",
            f"Failed to parse demo:\n\n{error}"
        )
        
        self.status_bar.showMessage("Parse failed", 3000)
        
        # Включаем кнопку обратно
        self.parse_btn.setEnabled(True)
        self.parse_btn.setText("🔍 Parse Selected Demo")
        
        log.error(f"Parse error: {error}")
    
    def refresh_demo_list(self):
        """Обновление списка демок"""
        self.demo_list.clear()
        self.demo_paths.clear()
        self.current_demo_path = None
        self.parse_btn.setEnabled(False)
        
        log.info("Demo list refreshed")
        self.status_bar.showMessage("List refreshed", 2000)
    
    def show_about(self):
        """Показать информацию о программе"""
        QMessageBox.about(
            self,
            "About CS Demo Manager",
            f"""
            <h2>CS Demo Manager</h2>
            <p>Version: {config.version}</p>
            <p>Python-based CS:GO/CS2 demo analyzer</p>
            <br>
            <p>Features:</p>
            <ul>
                <li>Demo parsing</li>
                <li>2D visualization</li>
                <li>Statistics</li>
            </ul>
            """
        )
    
    def update_status(self, message: str, timeout: int = 0):
        """Обновление статус бара"""
        self.status_bar.showMessage(message, timeout)
    
    def _on_play_clicked(self):
        """Обработка клика Play"""
        self.demo_viewer.play()
        log.debug("Play clicked")
    
    def _on_pause_clicked(self):
        """Обработка клика Pause"""
        self.demo_viewer.pause()
        log.debug("Pause clicked")
    
    def _on_stop_clicked(self):
        """Обработка клика Stop"""
        self.demo_viewer.stop()
        log.debug("Stop clicked")
    
    def _on_seek_requested(self, progress: float):
        """Обработка seek (перемотки)"""
        self.demo_viewer.set_progress(progress)
        log.debug(f"Seek to {progress*100:.1f}%")
    
    def _on_speed_changed(self, speed: float):
        """Обработка изменения скорости"""
        self.demo_viewer.set_speed(speed)
        log.debug(f"Speed changed to {speed}x")
    
    def _on_tab_changed(self, index: int):
        """Обработка переключения таба"""
        # Если переключились на Database таб, обновляем список
        if index == 2:  # Database таб
            self.matches_browser.refresh()
    
    def _on_match_from_db_selected(self, match_id: int):
        """Обработка выбора матча из БД"""
        log.info(f"Loading match from database: {match_id}")
        
        import asyncio
        from ..database.repository import MatchRepository
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            match_model = loop.run_until_complete(MatchRepository.get_by_id(match_id))
            
            if not match_model:
                QMessageBox.warning(self, "Error", f"Match #{match_id} not found")
                return
            
            # TODO: Конвертировать MatchModel обратно в Match объект
            # И загрузить в stats_panel и demo_viewer
            
            info = (
                f"Match #{match_id}\n\n"
                f"Map: {match_model.map_name}\n"
                f"Score: {match_model.t_score}:{match_model.ct_score}\n"
                f"Rounds: {match_model.total_rounds}\n"
                f"Players: {match_model.total_players}\n\n"
                f"Note: Full match loading from DB not yet implemented."
            )
            
            QMessageBox.information(self, "Match Info", info)
            
        except Exception as e:
            log.error(f"Failed to load match: {e}")
            QMessageBox.critical(self, "Error", f"Failed to load match:\n{e}")
    
    def _on_match_deleted(self, match_id: int):
        """Обработка удаления матча"""
        log.info(f"Match {match_id} was deleted")
    
    def _update_playback_progress(self):
        """Обновление прогресса воспроизведения"""
        if self.demo_viewer.is_playing or self.demo_viewer.frames:
            progress = self.demo_viewer.get_progress()
            self.playback_controls.set_progress(progress)
            
            # Обновляем время
            if self.demo_viewer.frames and self.demo_viewer.current_frame_index < len(self.demo_viewer.frames):
                current_frame = self.demo_viewer.frames[self.demo_viewer.current_frame_index]
                total_time = self.demo_viewer.frames[-1].time_seconds if self.demo_viewer.frames else 0
                self.playback_controls.set_time(current_frame.time_seconds, total_time)
    
    def _toggle_debug_mode(self, checked: bool):
        """Переключить debug режим"""
        self.demo_viewer.canvas.toggle_debug()

        log.debug(f"Debug mode: {checked}")
