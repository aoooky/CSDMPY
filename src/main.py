
import sys
import asyncio
from pathlib import Path

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

# Добавляем путь к src в PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.gui.main_window import MainWindow
from src.utils.logger import log
from src.utils.config import config
from src.database.database import db


class Application:
    """Главный класс приложения"""
    
    def __init__(self):
        """Инициализация приложения"""
        self.app = None
        self.main_window = None
        
    async def setup_async(self):
        """Асинхронная настройка (БД и т.д.)"""
        log.info("Setting up async components...")
        
        # Инициализация базы данных
        try:
            await db.initialize()
            log.info("Database initialized successfully")
        except Exception as e:
            log.error(f"Failed to initialize database: {e}")
            log.warning("Application will continue without database support")
            # Продолжаем работу даже если БД не инициализирована
        
    def setup(self):
        """Настройка приложения"""
        log.info(f"Starting {config.app_name} v{config.version}")
        log.info(f"Debug mode: {config.debug}")
        
        # Создание QApplication
        self.app = QApplication(sys.argv)
        self.app.setApplicationName(config.app_name)
        self.app.setApplicationVersion(config.version)
        
        # Настройка стиля
        self._setup_style()
        
        # Инициализация БД в event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self.setup_async())
        
        # Создание главного окна
        self.main_window = MainWindow()
        
        log.info("Application setup completed")
    
    def _setup_style(self):
        """Настройка глобального стиля приложения"""
        style = """
        QMainWindow {
            background-color: #ffffff;
        }
        
        QMenuBar {
            background-color: #f0f0f0;
            padding: 4px;
        }
        
        QMenuBar::item {
            padding: 4px 12px;
            background-color: transparent;
        }
        
        QMenuBar::item:selected {
            background-color: #e0e0e0;
        }
        
        QToolBar {
            background-color: #f5f5f5;
            border-bottom: 1px solid #ddd;
            spacing: 8px;
            padding: 4px;
        }
        
        QStatusBar {
            background-color: #f5f5f5;
            border-top: 1px solid #ddd;
        }
        
        QPushButton {
            padding: 6px 12px;
            background-color: #2196f3;
            color: white;
            border: none;
            border-radius: 4px;
        }
        
        QPushButton:hover {
            background-color: #1976d2;
        }
        
        QPushButton:pressed {
            background-color: #0d47a1;
        }
        """
        self.app.setStyleSheet(style)
    
    def run(self):
        """Запуск приложения"""
        if not self.main_window:
            raise RuntimeError("Application not setup. Call setup() first.")
        
        self.main_window.show()
        log.info("Application started")
        
        exit_code = self.app.exec()
        
        # Очистка при выходе
        self.cleanup()
        
        return exit_code
    
    def cleanup(self):
        """Очистка ресурсов при выходе"""
        log.info("Cleaning up...")
        
        # Закрываем БД
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(db.close())
        
        log.info("Cleanup completed")


def main():
    """Главная функция"""
    try:
        app = Application()
        app.setup()
        sys.exit(app.run())
    except Exception as e:
        log.exception(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()