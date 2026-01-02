
from typing import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
    AsyncSession,
    AsyncEngine
)
from sqlalchemy.pool import NullPool

from .models import Base
from ..utils.config import config
from ..utils.logger import log


class Database:
    """Класс для управления подключением к базе данных"""
    
    def __init__(self):
        self.engine: AsyncEngine | None = None
        self.session_factory: async_sessionmaker[AsyncSession] | None = None
        self._initialized = False
    
    async def initialize(self):
        """Инициализация подключения к БД"""
        if self._initialized:
            log.warning("Database already initialized")
            return
        
        log.info(f"Initializing database: {config.database.type}")
        
        try:
            # Создаём движок
            if config.database.type == "sqlite":
                # SQLite специфичные параметры
                db_url = config.database.url
                log.debug(f"Database URL: {db_url}")
                
                self.engine = create_async_engine(
                    db_url,
                    echo=config.debug,
                    poolclass=NullPool,  # SQLite не поддерживает pool
                    connect_args={"check_same_thread": False}
                )
            else:
                # PostgreSQL
                self.engine = create_async_engine(
                    config.database.url,
                    echo=config.debug,
                    pool_pre_ping=True,
                    pool_size=5,
                    max_overflow=10
                )
            
            # Создаём фабрику сессий
            self.session_factory = async_sessionmaker(
                self.engine,
                class_=AsyncSession,
                expire_on_commit=False
            )
            
            # Создаём таблицы
            await self.create_tables()
            
            self._initialized = True
            log.info("Database initialized successfully")
            
        except Exception as e:
            log.exception(f"Failed to initialize database: {e}")
            raise
    
    async def create_tables(self):
        """Создание всех таблиц"""
        if not self.engine:
            raise RuntimeError("Database engine not initialized")
        
        log.info("Creating database tables...")
        
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        log.info("Database tables created")
    
    async def drop_tables(self):
        """Удаление всех таблиц (осторожно!)"""
        if not self.engine:
            raise RuntimeError("Database engine not initialized")
        
        log.warning("Dropping all database tables...")
        
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        
        log.warning("All database tables dropped")
    
    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Контекстный менеджер для получения сессии
        
        Usage:
            async with db.session() as session:
                result = await session.execute(select(MatchModel))
        """
        if not self.session_factory:
            raise RuntimeError("Database not initialized")
        
        session = self.session_factory()
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            log.error(f"Database session error: {e}")
            raise
        finally:
            await session.close()
    
    async def close(self):
        """Закрытие подключения к БД"""
        if self.engine:
            await self.engine.dispose()
            log.info("Database connection closed")
            self._initialized = False
    
    def is_initialized(self) -> bool:
        """Проверка инициализации"""
        return self._initialized


# Глобальный инстанс базы данных
db = Database()