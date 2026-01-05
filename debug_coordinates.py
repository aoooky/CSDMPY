
import sys
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.core.demo_parser import DemoParserWrapper
from src.utils.logger import log


async def analyze_coordinates(demo_path: str):
    """Анализ координат из демки"""
    print("=" * 70)
    print("Map Coordinates Analyzer")
    print("=" * 70)
    print()
    
    # Парсим демку
    print(f"📁 Demo: {Path(demo_path).name}")
    print("⏳ Parsing...")
    
    parser = DemoParserWrapper(demo_path)
    result = await parser.parse()  # ← Возвращает dict!
    
    # Извлекаем данные из dict
    map_name = result.get('map_name', 'unknown')
    positions = result.get('positions')  # DataFrame
    players = result.get('players', [])
    
    print(f"✅ Map: {map_name}")
    print(f"✅ Players: {len(players)}")
    print(f"✅ Position rows: {len(positions)}")
    print()
    
    if positions is None or positions.empty:
        print("❌ No positions found!")
        return
    
    # Находим min/max координаты из DataFrame
    min_x = positions['X'].min()
    max_x = positions['X'].max()
    min_y = positions['Y'].min()
    max_y = positions['Y'].max()
    min_z = positions['Z'].min()
    max_z = positions['Z'].max()
    
    # Выводим результаты
    print("=" * 70)
    print("MAP BOUNDARIES")
    print("=" * 70)
    print()
    print(f"X axis: {min_x:.1f} to {max_x:.1f}  (width: {max_x - min_x:.1f})")
    print(f"Y axis: {min_y:.1f} to {max_y:.1f}  (height: {max_y - min_y:.1f})")
    print(f"Z axis: {min_z:.1f} to {max_z:.1f}  (vertical: {max_z - min_z:.1f})")
    print()
    
    # Рекомендуемые границы (с запасом 10%)
    margin = 0.1
    x_range = max_x - min_x
    y_range = max_y - min_y
    
    suggested_min_x = min_x - x_range * margin
    suggested_max_x = max_x + x_range * margin
    suggested_min_y = min_y - y_range * margin
    suggested_max_y = max_y + y_range * margin
    
    # Код для вставки
    print("=" * 70)
    print("SUGGESTED CODE FOR map_config.py")
    print("=" * 70)
    print()
    print(f'    "{map_name}": MapBounds(')
    print(f'        pos_x={suggested_min_x:.0f},')
    print(f'        pos_y={suggested_max_y:.0f},')
    print(f'        scale=4.9,')
    print(f'        min_x={suggested_min_x:.0f},')
    print(f'        max_x={suggested_max_x:.0f},')
    print(f'        min_y={suggested_min_y:.0f},')
    print(f'        max_y={suggested_max_y:.0f}')
    print(f'    ),')
    print()
    
    # Примеры позиций (первые 10 строк)
    print("=" * 70)
    print("SAMPLE POSITIONS (first 10 rows)")
    print("=" * 70)
    print()
    
    sample = positions.head(10)
    print(f"{'Name':<15} {'X':>10} {'Y':>10} {'Z':>10} {'Team':<15}")
    print("-" * 70)
    
    for _, row in sample.iterrows():
        name = str(row.get('name', 'Unknown'))[:14]
        x = row.get('X', 0)
        y = row.get('Y', 0)
        z = row.get('Z', 0)
        team = str(row.get('team_name', 'Unknown'))[:14]
        print(f"{name:<15} {x:>10.1f} {y:>10.1f} {z:>10.1f} {team:<15}")
    
    print()
    print("=" * 70)


def main():
    """Главная функция"""
    if len(sys.argv) < 2:
        print("Usage: python debug_coordinates.py <path_to_demo.dem>")
        print()
        print("Example:")
        print("  python debug_coordinates.py demos/test2.dem")
        sys.exit(1)
    
    demo_path = sys.argv[1]
    
    if not Path(demo_path).exists():
        print(f"❌ Error: File not found: {demo_path}")
        sys.exit(1)
    
    asyncio.run(analyze_coordinates(demo_path))


if __name__ == "__main__":
    main()
