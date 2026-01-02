#!/usr/bin/env python
"""
Скрипт для определения правильных границ карты
Запуск: python debug_coordinates.py demos/your_demo.dem
"""
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
    match = await parser.parse()
    
    print(f"✅ Map: {match.map_name}")
    print(f"✅ Players: {len(match.players)}")
    print()
    
    # Парсим позиции
    print("⏳ Parsing positions...")
    frames = await parser.parse_positions(tick_interval=128)
    print(f"✅ Frames: {len(frames)}")
    print()
    
    if not frames:
        print("❌ No frames found!")
        return
    
    # Находим min/max координаты
    min_x = float('inf')
    max_x = float('-inf')
    min_y = float('inf')
    max_y = float('-inf')
    min_z = float('inf')
    max_z = float('-inf')
    
    for frame in frames:
        for player_frame in frame.players:
            pos = player_frame.position
            min_x = min(min_x, pos.x)
            max_x = max(max_x, pos.x)
            min_y = min(min_y, pos.y)
            max_y = max(max_y, pos.y)
            min_z = min(min_z, pos.z)
            max_z = max(max_z, pos.z)
    
    # Выводим результаты
    print("=" * 70)
    print("MAP BOUNDARIES")
    print("=" * 70)
    print()
    print(f"X axis: {min_x:.1f} to {max_x:.1f}  (width: {max_x - min_x:.1f})")
    print(f"Y axis: {min_y:.1f} to {max_y:.1f}  (height: {max_y - min_y:.1f})")
    print(f"Z axis: {min_z:.1f} to {max_z:.1f}  (vertical: {max_z - min_z:.1f})")
    print()
    
    # Код для вставки
    print("=" * 70)
    print("CODE TO USE IN map_renderer.py")
    print("=" * 70)
    print()
    print(f'"{match.map_name}": MapBounds({min_x:.0f}, {max_x:.0f}, {min_y:.0f}, {max_y:.0f}),')
    print()
    
    # Примеры позиций
    print("=" * 70)
    print("SAMPLE POSITIONS (first 10 players from first frame)")
    print("=" * 70)
    print()
    
    if frames and frames[0].players:
        print(f"{'Player':<20} {'X':>10} {'Y':>10} {'Z':>10}")
        print("-" * 70)
        for pf in frames[0].players[:10]:
            print(f"{pf.player.name:<20} {pf.position.x:>10.1f} {pf.position.y:>10.1f} {pf.position.z:>10.1f}")
    
    print()
    print("=" * 70)


def main():
    """Главная функция"""
    if len(sys.argv) < 2:
        print("Usage: python debug_coordinates.py <path_to_demo.dem>")
        print()
        print("Example:")
        print("  python debug_coordinates.py demos/match.dem")
        sys.exit(1)
    
    demo_path = sys.argv[1]
    
    if not Path(demo_path).exists():
        print(f"❌ Error: File not found: {demo_path}")
        sys.exit(1)
    
    asyncio.run(analyze_coordinates(demo_path))


if __name__ == "__main__":
    main()