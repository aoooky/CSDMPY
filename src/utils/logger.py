import sys
from pathlib import Path
from loguru import logger


class Logger:
    """Централизованная система логирования"""
    
    def __init__(self, log_dir: str = "logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        self._setup_logger()
    
    def _setup_logger(self):
        """Настройка логгера с различными обработчиками"""
        # Удаляем дефолтный обработчик
        logger.remove()
        
        # Консоль - только INFO и выше, с цветами
        logger.add(
            sys.stdout,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
            level="INFO",
            colorize=True,
        )
        
        # Файл с ротацией - все логи
        logger.add(
            self.log_dir / "app_{time:YYYY-MM-DD}.log",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
            level="DEBUG",
            rotation="00:00",  # Новый файл каждый день
            retention="30 days",  # Хранить 30 дней
            compression="zip",  # Сжимать старые логи
        )
        
        # Отдельный файл для ошибок
        logger.add(
            self.log_dir / "errors_{time:YYYY-MM-DD}.log",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}\n{exception}",
            level="ERROR",
            rotation="00:00",
            retention="90 days",
            compression="zip",
        )
        
        logger.info("Logger initialized")
    
    @staticmethod
    def get_logger():
        """Получить инстанс логгера"""
        return logger


# Создаём глобальный инстанс
app_logger = Logger()
log = app_logger.get_logger()


# Декораторы для логирования
def log_execution_time(func):
    """Декоратор для логирования времени выполнения функции"""
    import functools
    import time
    
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        elapsed = time.time() - start
        log.debug(f"{func.__name__} executed in {elapsed:.4f}s")
        return result
    return wrapper


def log_async_execution_time(func):
    """Декоратор для логирования времени выполнения асинхронной функции"""
    import functools
    import time
    
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        start = time.time()
        result = await func(*args, **kwargs)
        elapsed = time.time() - start
        log.debug(f"{func.__name__} executed in {elapsed:.4f}s")
        return result
    return wrapper