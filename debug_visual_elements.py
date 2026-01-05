
import sys
from pathlib import Path

# Добавляем путь к проекту
sys.path.insert(0, str(Path(__file__).parent))

# Пробуем разные варианты импорта
try:
    from src.core.demo_parser import DemoParser
except ImportError:
    try:
        from src.core.demo_parser import CSGODemoParser as DemoParser
    except ImportError:
        # Если ничего не работает - импортируем модуль целиком
        import src.core.demo_parser as demo_parser_module
        # Находим класс парсера
        for name in dir(demo_parser_module):
            obj = getattr(demo_parser_module, name)
            if isinstance(obj, type) and 'parser' in name.lower():
                DemoParser = obj
                break

try:
    from src.core.data_processor import DataProcessor
except ImportError:
    try:
        from src.core.data_processor import MatchDataProcessor as DataProcessor
    except ImportError:
        import src.core.data_processor as processor_module
        for name in dir(processor_module):
            obj = getattr(processor_module, name)
            if isinstance(obj, type) and 'processor' in name.lower():
                DataProcessor = obj
                break


def check_kills(demo_data):
    """Проверка данных об убийствах"""
    print("\n" + "="*60)
    print("🔫 ПРОВЕРКА ДАННЫХ ОБ УБИЙСТВАХ")
    print("="*60)
    
    kills = demo_data.get('kills', [])
    
    if not kills:
        print("❌ Нет данных об убийствах!")
        return False
    
    print(f"✅ Найдено убийств: {len(kills)}")
    print("\nПервые 5 убийств:")
    print("-" * 60)
    
    for i, kill in enumerate(kills[:5], 1):
        print(f"\n{i}. Убийство на тике {kill.tick}:")
        print(f"   Убийца: {getattr(kill, 'killer_name', 'Unknown')}")
        print(f"   Жертва: {getattr(kill, 'victim_name', 'Unknown')}")
        print(f"   Оружие: {getattr(kill, 'weapon', 'Unknown')}")
        
        # Проверяем координаты жертвы
        victim_x = getattr(kill, 'victim_X', None)
        victim_y = getattr(kill, 'victim_Y', None)
        
        if victim_x is not None and victim_y is not None:
            print(f"   Позиция жертвы: X={victim_x:.2f}, Y={victim_y:.2f}")
        else:
            print(f"   ⚠️ Нет координат жертвы!")
            # Пробуем альтернативные имена атрибутов
            for attr in dir(kill):
                if 'victim' in attr.lower() and ('x' in attr.lower() or 'y' in attr.lower()):
                    print(f"      Найден атрибут: {attr} = {getattr(kill, attr)}")
    
    return True


def check_bomb(demo_data):
    """Проверка данных о бомбе"""
    print("\n" + "="*60)
    print("💣 ПРОВЕРКА ДАННЫХ О БОМБЕ")
    print("="*60)
    
    positions = demo_data.get('positions')
    
    if positions is None or positions.empty:
        print("❌ Нет данных о позициях!")
        return False
    
    # Проверяем наличие колонки has_bomb
    if 'has_bomb' in positions.columns:
        bomb_carriers = positions[positions['has_bomb'] == True]
        print(f"✅ Колонка 'has_bomb' найдена")
        print(f"   Записей с бомбой: {len(bomb_carriers)}")
        
        if not bomb_carriers.empty:
            print("\nПримеры игроков с бомбой:")
            print("-" * 60)
            for i, (idx, player) in enumerate(bomb_carriers.head(3).iterrows(), 1):
                print(f"\n{i}. Тик {player['tick']}:")
                print(f"   Игрок: {player.get('name', 'Unknown')}")
                print(f"   Команда: {player.get('team_name', 'Unknown')}")
                print(f"   Позиция: X={player.get('X', 0):.2f}, Y={player.get('Y', 0):.2f}")
    else:
        print("⚠️ Колонка 'has_bomb' НЕ найдена!")
        print("\nДоступные колонки:")
        print(", ".join(positions.columns.tolist()))
    
    # Проверяем события установки бомбы
    print("\n" + "-"*60)
    print("Проверка событий установки бомбы:")
    
    # Ищем в разных возможных местах
    bomb_plants = None
    
    if hasattr(demo_data, 'bomb_plants'):
        bomb_plants = demo_data['bomb_plants']
    elif 'bomb_plants' in demo_data:
        bomb_plants = demo_data['bomb_plants']
    
    if bomb_plants:
        print(f"✅ Найдено установок бомбы: {len(bomb_plants)}")
        
        if bomb_plants:
            print("\nПримеры установок:")
            print("-" * 60)
            for i, plant in enumerate(bomb_plants[:3], 1):
                print(f"\n{i}. Установка на тике {getattr(plant, 'tick', '?')}:")
                plant_x = getattr(plant, 'x', None)
                plant_y = getattr(plant, 'y', None)
                if plant_x and plant_y:
                    print(f"   Позиция: X={plant_x:.2f}, Y={plant_y:.2f}")
                else:
                    print(f"   ⚠️ Нет координат установки")
    else:
        print("⚠️ События установки бомбы НЕ найдены!")
    
    return True


def check_data_structure(demo_data):
    """Общая проверка структуры данных"""
    print("\n" + "="*60)
    print("📊 СТРУКТУРА ДАННЫХ ДЕМКИ")
    print("="*60)
    
    print("\nОсновные ключи в demo_data:")
    for key in demo_data.keys():
        value = demo_data[key]
        if hasattr(value, '__len__'):
            print(f"  - {key}: {type(value).__name__} (размер: {len(value)})")
        else:
            print(f"  - {key}: {type(value).__name__}")
    
    # Проверяем колонки DataFrame позиций
    positions = demo_data.get('positions')
    if positions is not None and not positions.empty:
        print(f"\nКолонки в positions DataFrame ({len(positions.columns)}):")
        for col in sorted(positions.columns):
            print(f"  - {col}")


def main():
    if len(sys.argv) < 2:
        print("❌ Использование: python debug_visual_elements.py путь/к/демке.dem")
        print("\nПример:")
        print("  python debug_visual_elements.py demos/match.dem")
        sys.exit(1)
    
    demo_path = Path(sys.argv[1])
    
    if not demo_path.exists():
        print(f"❌ Файл не найден: {demo_path}")
        sys.exit(1)
    
    print(f"🔍 Анализ демки: {demo_path.name}")
    print(f"   Путь: {demo_path}")
    
    # Парсим демку
    print("\n⏳ Парсинг демки...")
    parser = DemoParser()
    demo_data = parser.parse_demo(str(demo_path))
    
    if not demo_data:
        print("❌ Ошибка парсинга демки!")
        sys.exit(1)
    
    print("✅ Демка успешно распарсена")
    
    # Обрабатываем данные
    print("\n⏳ Обработка данных...")
    processor = DataProcessor()
    processed_data = processor.process(demo_data)
    
    # Проверяем структуру
    check_data_structure(processed_data)
    
    # Проверяем убийства
    kills_ok = check_kills(processed_data)
    
    # Проверяем бомбу
    bomb_ok = check_bomb(processed_data)
    
    # Итоговый отчёт
    print("\n" + "="*60)
    print("📋 ИТОГОВЫЙ ОТЧЁТ")
    print("="*60)
    
    if kills_ok:
        print("✅ Маркеры убийств: данные доступны, должны работать")
    else:
        print("❌ Маркеры убийств: требуется доработка")
    
    if bomb_ok:
        print("✅ Индикатор бомбы: данные частично доступны")
    else:
        print("❌ Индикатор бомбы: требуется доработка")
    
    print("\n💡 Рекомендации:")
    print("1. Если маркеры убийств не работают - проверьте атрибуты в _draw_kills()")
    print("2. Если бомба не отображается - проверьте колонку 'has_bomb'")
    print("3. Запустите приложение и проверьте визуально")


if __name__ == "__main__":
    main()
