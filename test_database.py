
import sys
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.database.database import db
from src.utils.config import config
from src.utils.logger import log


async def test_database():
    """Тест подключения и работы с БД"""
    print("=" * 60)
    print("Database Test")
    print("=" * 60)
    print()
    
    # Информация о конфигурации
    print("Configuration:")
    print(f"  Type: {config.database.type}")
    print(f"  Path: {config.database.path}")
    print(f"  URL:  {config.database.url}")
    print()
    
    try:
        # Инициализация
        print("⏳ Initializing database...")
        await db.initialize()
        print("✅ Database initialized")
        print()
        
        # Проверка файла БД (для SQLite)
        if config.database.type == "sqlite":
            if config.database.path.exists():
                size = config.database.path.stat().st_size
                print(f"📁 Database file: {config.database.path}")
                print(f"📊 Size: {size} bytes")
            else:
                print("❌ Database file not found!")
        print()
        
        # Проверка таблиц
        print("⏳ Checking tables...")
        async with db.session() as session:
            from sqlalchemy import text
            result = await session.execute(text("SELECT name FROM sqlite_master WHERE type='table';"))
            tables = [row[0] for row in result]
            
            print(f"✅ Found {len(tables)} tables:")
            for table in tables:
                print(f"   - {table}")
        print()
        
        # Проверка количества записей
        print("⏳ Checking record counts...")
        from src.database.repository import MatchRepository
        
        match_count = await MatchRepository.count()
        print(f"📊 Matches in database: {match_count}")
        print()
        
        # Статистика
        from src.database.repository import StatsRepository
        stats = await StatsRepository.get_total_stats()
        
        if stats:
            print("📈 Total statistics:")
            print(f"   Total matches: {stats.get('total_matches', 0)}")
            print(f"   Total kills:   {stats.get('total_kills', 0)}")
            print(f"   Total rounds:  {stats.get('total_rounds', 0)}")
        print()
        
        # Закрытие
        await db.close()
        print("✅ Database connection closed")
        print()
        
        print("=" * 60)
        print("✅ All tests passed!")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print()
        print("=" * 60)
        print("❌ Test failed!")
        print("=" * 60)
        print(f"Error: {e}")
        print()
        
        import traceback
        traceback.print_exc()
        
        return False


def main():
    """Главная функция"""
    success = asyncio.run(test_database())
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()