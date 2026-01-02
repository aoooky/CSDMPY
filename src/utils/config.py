
from pathlib import Path
from typing import Literal
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseConfig(BaseSettings):
    """Настройки базы данных"""
    model_config = SettingsConfigDict(
        env_prefix="CSDM_DATABASE_",
    )
    
    type: Literal["sqlite", "postgresql"] = "sqlite"
    path: Path = Field(default=Path("data/cs_demos.db"))
    
    # Для PostgreSQL (опционально)
    host: str | None = None
    port: int = 5432
    username: str | None = None
    password: str | None = None
    database: str | None = None
    
    @property
    def url(self) -> str:
        """Генерация URL для подключения к БД"""
        if self.type == "sqlite":
            # Создаём директорию если не существует
            db_path = Path(self.path)
            db_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Конвертируем путь в абсолютный и используем forward slashes
            abs_path = db_path.resolve()
            # Для Windows используем формат с тройным слешем и forward slashes
            path_str = str(abs_path).replace("\\", "/")
            return f"sqlite+aiosqlite:///{path_str}"
        else:
            return f"postgresql+asyncpg://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"


class AppConfig(BaseSettings):
    """Основная конфигурация приложения"""
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="CSDM_",
        case_sensitive=False,
    )
    
    # Основные настройки
    app_name: str = "CS Demo Manager"
    version: str = "0.1.0"
    debug: bool = False
    
    # Пути
    demos_dir: Path = Field(default=Path("demos"))
    assets_dir: Path = Field(default=Path("assets"))
    maps_dir: Path = Field(default=Path("assets/maps"))
    
    # База данных
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    
    # Парсинг
    max_concurrent_parsing: int = 4
    parse_timeout: int = 300  # 5 минут
    
    # Визуализация
    default_map_scale: float = 1.0
    render_fps: int = 60
    player_marker_size: int = 10
    
    # Окно приложения
    window_width: int = 1400
    window_height: int = 900
    window_title: str = "CS Demo Manager - Python"
    
    # Поддерживаемые карты
    supported_maps: list[str] = Field(
        default=[
            "de_dust2",
            "de_mirage", 
            "de_train",
            "de_ancient",
            "de_nuke",
            "de_overpass",
            "de_inferno"
        ]
    )
    
    def __init__(self, **data):
        super().__init__(**data)
        # Создаём необходимые директории
        self.demos_dir.mkdir(parents=True, exist_ok=True)
        self.assets_dir.mkdir(parents=True, exist_ok=True)
        self.maps_dir.mkdir(parents=True, exist_ok=True)
    
    @property
    def map_image_path(self) -> dict[str, Path]:
        """Словарь путей к изображениям карт"""
        return {
            map_name: self.maps_dir / f"{map_name}.png"
            for map_name in self.supported_maps
        }


# Глобальная конфигурация
config = AppConfig()


# Пример .env файла:
"""
# .env
CSDM_DEBUG=true
CSDM_DEMOS_DIR=./my_demos
CSDM_DATABASE__TYPE=sqlite
CSDM_DATABASE__PATH=./data/my_database.db
CSDM_MAX_CONCURRENT_PARSING=8
"""