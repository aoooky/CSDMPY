"""
Воркер для асинхронного парсинга демок в фоновом режиме
Не блокирует UI
"""
import asyncio
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QObject, pyqtSignal, QThread

from ..core.demo_parser import parse_demo
from ..core.models import Match
from ..core.data_processor import DataProcessor
from ..utils.logger import log


class ParserWorker(QObject):
    """
    Воркер для парсинга в отдельном потоке
    Использует сигналы для коммуникации с главным потоком
    """
    
    # Сигналы
    started = pyqtSignal(str)  # demo_path
    progress = pyqtSignal(str, int)  # message, percentage
    finished = pyqtSignal(object, object)  # Match object, frames list
    error = pyqtSignal(str, str)  # error_message, demo_path
    
    def __init__(self):
        super().__init__()
        self.demo_path: Optional[str] = None
        self.should_stop = False
        self.parse_positions_flag = True  # Флаг парсинга позиций
    
    def set_demo_path(self, demo_path: str):
        """Установить путь к демо файлу"""
        self.demo_path = demo_path
        self.should_stop = False
    
    def stop(self):
        """Остановить парсинг"""
        self.should_stop = True
        log.info("Parser worker stop requested")
    
    async def _parse_async(self):
        """Асинхронный парсинг"""
        if not self.demo_path:
            raise ValueError("Demo path not set")
        
        demo_name = Path(self.demo_path).name
        
        try:
            # Начинаем парсинг
            self.started.emit(self.demo_path)
            self.progress.emit(f"Parsing {demo_name}...", 10)
            
            log.info(f"Starting async parse: {demo_name}")
            
            # Создаём парсер
            from ..core.demo_parser import DemoParserWrapper
            parser = DemoParserWrapper(self.demo_path)
            
            # Парсим демо (основные данные)
            match = await parser.parse()
            
            if self.should_stop:
                log.info("Parsing cancelled by user")
                return
            
            self.progress.emit("Parsing positions...", 60)
            
            # Парсим позиции для визуализации
            frames = []
            if self.parse_positions_flag:
                try:
                    # Уменьшенный интервал для точности 1:1 с реальным временем
                    # При 64 tick: tick_interval=16 = ~4 frames/sec
                    # При воспроизведении 15 FPS получим примерно реальное время
                    frames = await parser.parse_positions(tick_interval=16)
                    log.info(f"Parsed {len(frames)} position frames")
                except Exception as e:
                    log.error(f"Failed to parse positions: {e}")
                    # Продолжаем даже если позиции не распарсились
            
            if self.should_stop:
                log.info("Parsing cancelled by user")
                return
            
            self.progress.emit("Processing data...", 90)
            
            # Создаём процессор для дополнительного анализа
            from ..core.data_processor import DataProcessor
            processor = DataProcessor(match)
            
            self.progress.emit("Completed!", 100)
            
            log.info(
                f"Parse completed: {match.map_name}, "
                f"{match.total_rounds} rounds, {len(match.players)} players, "
                f"{len(frames)} frames"
            )
            
            # Отправляем результат
            self.finished.emit(match, frames)
            
        except FileNotFoundError as e:
            error_msg = f"Demo file not found: {demo_name}"
            log.error(error_msg)
            self.error.emit(error_msg, self.demo_path)
            
        except Exception as e:
            error_msg = f"Failed to parse {demo_name}: {str(e)}"
            log.exception(error_msg)
            self.error.emit(error_msg, self.demo_path)
    
    def run(self):
        """
        Запуск парсинга
        Эта функция вызывается в отдельном потоке
        """
        try:
            # Создаём новый event loop для этого потока
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Запускаем асинхронный парсинг
            loop.run_until_complete(self._parse_async())
            
            loop.close()
            
        except Exception as e:
            log.exception(f"Worker thread error: {e}")
            self.error.emit(str(e), self.demo_path or "unknown")


class ParserManager(QObject):
    """
    Менеджер для управления парсингом демок
    Упрощённый интерфейс для GUI
    """
    
    # Сигналы
    parse_started = pyqtSignal(str)
    parse_progress = pyqtSignal(str, int)
    parse_finished = pyqtSignal(object, object)  # Match, frames
    parse_error = pyqtSignal(str, str)  # error, demo_path
    
    def __init__(self):
        super().__init__()
        self.worker: Optional[ParserWorker] = None
        self.thread: Optional[QThread] = None
        self.current_match: Optional[Match] = None
        self.current_frames: list = []
        self.current_processor: Optional[DataProcessor] = None
    
    def parse_demo(self, demo_path: str):
        """
        Начать парсинг демо файла
        
        Args:
            demo_path: Путь к .dem файлу
        """
        if self.is_parsing():
            log.warning("Parser is already running")
            return
        
        log.info(f"Starting parser for: {demo_path}")
        
        # Создаём воркер и поток
        self.worker = ParserWorker()
        self.thread = QThread()
        
        # Перемещаем воркер в поток
        self.worker.moveToThread(self.thread)
        
        # Подключаем сигналы
        self.worker.started.connect(self._on_started)
        self.worker.progress.connect(self._on_progress)
        self.worker.finished.connect(self._on_finished)
        self.worker.error.connect(self._on_error)
        
        # Подключаем запуск
        self.thread.started.connect(self.worker.run)
        
        # Настраиваем воркер
        self.worker.set_demo_path(demo_path)
        
        # Запускаем поток
        self.thread.start()
    
    def stop_parsing(self):
        """Остановить парсинг"""
        if self.worker:
            self.worker.stop()
        
        if self.thread and self.thread.isRunning():
            self.thread.quit()
            self.thread.wait()
        
        log.info("Parser stopped")
    
    def is_parsing(self) -> bool:
        """Проверка идёт ли парсинг"""
        return self.thread is not None and self.thread.isRunning()
    
    def get_current_match(self) -> Optional[Match]:
        """Получить текущий распарсенный матч"""
        return self.current_match
    
    def get_current_frames(self) -> list:
        """Получить текущие фреймы позиций"""
        return self.current_frames
    
    def get_processor(self) -> Optional[DataProcessor]:
        """Получить процессор данных для текущего матча"""
        return self.current_processor
    
    def _on_started(self, demo_path: str):
        """Обработка начала парсинга"""
        log.debug(f"Parse started: {demo_path}")
        self.parse_started.emit(demo_path)
    
    def _on_progress(self, message: str, percentage: int):
        """Обработка прогресса"""
        log.debug(f"Parse progress: {message} ({percentage}%)")
        self.parse_progress.emit(message, percentage)
    
    def _on_finished(self, match: Match, frames: list):
        """Обработка завершения парсинга"""
        self.current_match = match
        self.current_frames = frames
        self.current_processor = DataProcessor(match)
        
        log.info(f"Parse finished: {match.map_name}, {len(frames)} frames")
        self.parse_finished.emit(match, frames)
        
        # Очистка
        self._cleanup()
    
    def _on_error(self, error: str, demo_path: str):
        """Обработка ошибки"""
        log.error(f"Parse error: {error}")
        self.parse_error.emit(error, demo_path)
        
        # Очистка
        self._cleanup()
    
    def _cleanup(self):
        """Очистка ресурсов"""
        if self.thread:
            self.thread.quit()
            self.thread.wait()
            self.thread = None
        
        self.worker = None