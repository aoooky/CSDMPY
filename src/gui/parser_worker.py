
import asyncio
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QThread, QObject, pyqtSignal
from loguru import logger

from ..core.demo_parser import DemoParserWrapper
from ..core.data_processor import DataProcessor
from ..core.models import create_match_from_parse_result
from ..database.repository import MatchRepository


class ParserWorker(QThread):
    """Воркер для асинхронного парсинга демок"""
    
    # Сигналы
    progress_updated = pyqtSignal(float, str)  # progress, status
    parse_started = pyqtSignal(str)  # demo_path
    parse_completed = pyqtSignal(object)  # match object or dict
    parse_error = pyqtSignal(str)  # error message
    
    def __init__(self, demo_path: str, repository: Optional[MatchRepository] = None):
        """
        Инициализация воркера
        
        Args:
            demo_path: Путь к демо-файлу
            repository: Репозиторий для сохранения в БД
        """
        super().__init__()
        
        self.demo_path = demo_path
        self.repository = repository
        self.is_cancelled = False
        
        logger.debug(f"ParserWorker initialized for {demo_path}")
    
    def run(self):
        """Запуск парсинга (вызывается автоматически при start())"""
        try:
            logger.info(f"Starting parser for: {self.demo_path}")
            
            # Создаём новый event loop для этого потока
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                # Запускаем асинхронный парсинг
                loop.run_until_complete(self._parse_async())
            finally:
                loop.close()
                
        except Exception as e:
            error_msg = f"Failed to parse {Path(self.demo_path).name}: {e}"
            logger.error(f"Parse error: {error_msg}")
            self.parse_error.emit(error_msg)
    
    async def _parse_async(self):
        """Асинхронный парсинг"""
        try:
            demo_name = Path(self.demo_path).name
            logger.info(f"Starting async parse: {demo_name}")
            
            # Создаём парсер
            parser = DemoParserWrapper(self.demo_path)
            
            # Эмитим сигнал начала парсинга
            self.parse_started.emit(self.demo_path)
            
            # Запускаем парсинг с колбэком прогресса
            result = await parser.parse(progress_callback=self._on_progress)
            
            if result is None or self.is_cancelled:
                logger.info("Parse cancelled")
                return
            
            # Результат - это dict с данными демки
            # Логируем успех
            map_name = result.get('map_name', 'unknown')
            players_count = len(result.get('players', []))
            rounds_count = len(result.get('rounds', []))
            
            logger.info(
                f"Parse completed: {map_name}, "
                f"{players_count} players, {rounds_count} rounds"
            )
            
            # Обрабатываем данные
            try:
                processor = DataProcessor(result)  # Передаём result как match
                processed_data = processor.process()
            except Exception as e:
                logger.warning(f"DataProcessor error (non-critical): {e}")
                # Продолжаем без обработки
                processed_data = result
            
            # Создаём Match объект
            match = create_match_from_parse_result(result)
            match.file_path = self.demo_path
            match.file_name = demo_name
            
            # Сохраняем в БД если есть репозиторий
            if self.repository:
                try:
                    saved_match = self.repository.save_match(match)
                    logger.info(f"Match saved to database: ID {saved_match.id}")
                    match = saved_match
                except Exception as e:
                    logger.error(f"Failed to save match to database: {e}")
            
            # Эмитим сигнал завершения
            self.parse_completed.emit(match)
            
        except Exception as e:
            error_msg = f"Failed to parse {Path(self.demo_path).name}: {e}"
            logger.error(error_msg)
            self.parse_error.emit(error_msg)
    
    def _on_progress(self, progress: float, status: str):
        """Обработчик обновления прогресса"""
        if not self.is_cancelled:
            self.progress_updated.emit(progress, status)
            logger.debug(f"Parse progress: {progress:.1%} - {status}")
    
    def cancel(self):
        """Отмена парсинга"""
        self.is_cancelled = True
        logger.info(f"Cancelling parse: {self.demo_path}")


class ParserManager(QObject):
    """Менеджер для управления воркерами парсинга"""
    
    # Сигналы для совместимости с MainWindow
    parse_started = pyqtSignal(str)  # demo_path
    parse_completed = pyqtSignal(object)  # match
    parse_finished = pyqtSignal(str)  # demo_path (алиас для completed)
    parse_error = pyqtSignal(str)  # error_msg
    parse_progress = pyqtSignal(float, str)  # progress, status (алиас)
    progress_updated = pyqtSignal(float, str)  # progress, status
    
    def __init__(self, repository: Optional[MatchRepository] = None):
        """
        Инициализация менеджера
        
        Args:
            repository: Репозиторий для сохранения в БД
        """
        super().__init__()
        
        self.repository = repository
        self.workers = {}  # demo_path -> worker
        
        logger.debug("ParserManager initialized")
    
    def parse_demo(
        self,
        demo_path: str,
        on_progress=None,
        on_started=None,
        on_completed=None,
        on_error=None
    ) -> ParserWorker:
        """
        Запуск парсинга демо-файла
        
        Args:
            demo_path: Путь к демо-файлу
            on_progress: Колбэк для обновления прогресса (progress, status)
            on_started: Колбэк при старте парсинга (demo_path)
            on_completed: Колбэк при завершении парсинга (match)
            on_error: Колбэк при ошибке (error_msg)
            
        Returns:
            ParserWorker объект
        """
        # Проверяем, не парсится ли уже эта демка
        if demo_path in self.workers:
            logger.warning(f"Demo already being parsed: {demo_path}")
            return self.workers[demo_path]
        
        # Создаём воркер
        worker = ParserWorker(demo_path, self.repository)
        
        # Подключаем колбэки
        if on_progress:
            worker.progress_updated.connect(on_progress)
        if on_started:
            worker.parse_started.connect(on_started)
        if on_completed:
            worker.parse_completed.connect(on_completed)
            worker.parse_completed.connect(lambda: self._on_worker_finished(demo_path))
        if on_error:
            worker.parse_error.connect(on_error)
            worker.parse_error.connect(lambda: self._on_worker_finished(demo_path))
        
        # Подключаем к собственным сигналам менеджера (для main_window)
        worker.parse_started.connect(self.parse_started.emit)
        worker.parse_completed.connect(self.parse_completed.emit)
        # parse_finished эмитит demo_path вместо match
        worker.parse_completed.connect(lambda match: self.parse_finished.emit(demo_path))
        worker.parse_error.connect(self.parse_error.emit)
        worker.parse_error.connect(lambda error: self.parse_finished.emit(demo_path))
        worker.progress_updated.connect(self.progress_updated.emit)
        worker.progress_updated.connect(self.parse_progress.emit)  # Алиас
        
        # Сохраняем воркер
        self.workers[demo_path] = worker
        
        # Запускаем парсинг
        worker.start()
        
        logger.info(f"Started parsing: {demo_path}")
        
        return worker
    
    def cancel_demo(self, demo_path: str):
        """Отмена парсинга демо-файла"""
        if demo_path in self.workers:
            worker = self.workers[demo_path]
            worker.cancel()
            logger.info(f"Cancelled parsing: {demo_path}")
    
    def cancel_all(self):
        """Отмена всех активных парсингов"""
        for demo_path in list(self.workers.keys()):
            self.cancel_demo(demo_path)
        logger.info("Cancelled all parsing")
    
    def _on_worker_finished(self, demo_path: str):
        """Обработчик завершения воркера"""
        if demo_path in self.workers:
            del self.workers[demo_path]
            logger.debug(f"Worker removed: {demo_path}")
    
    def get_active_count(self) -> int:
        """Получить количество активных воркеров"""
        return len(self.workers)
    
    def is_parsing(self, demo_path: str = None) -> bool:
        """
        Проверить, парсится ли демка
        
        Args:
            demo_path: Путь к демке (опционально). Если None - проверяет любую активную
        
        Returns:
            True если парсинг активен
        """
        if demo_path is None:
            # Проверяем, есть ли хоть один активный воркер
            return len(self.workers) > 0
        

        return demo_path in self.workers
