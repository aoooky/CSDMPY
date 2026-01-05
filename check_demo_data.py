"""
Простая проверка данных демки через demoparser2

ФАЙЛ: check_demo_simple.py (создать в корне проекта)
ИСПОЛЬЗОВАНИЕ: python check_demo_simple.py путь/к/демке.dem
"""

import sys
from pathlib import Path

# Добавляем путь к проекту
sys.path.insert(0, str(Path(__file__).parent))

from demoparser2 import DemoParser


def analyze_demo(demo_path):
    """Анализ демки через demoparser2"""
    print("="*70)
    print(f"🔍 АНАЛИЗ ДЕМКИ: {Path(demo_path).name}")
    print("="*70)
    
    print("\n⏳ Парсинг демки через demoparser2...")
    
    try:
        parser = DemoParser(demo_path)
        
        # Парсим основные события
        df = parser.parse_event("player_death")  # Убийства
        
        print("✅ Парсинг завершён!")
        
    except Exception as e:
        print(f"❌ Ошибка парсинга: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Проверяем убийства
    print("\n" + "="*70)
    print("🔫 УБИЙСТВА")
    print("="*70)
    
    if df is None or df.empty:
        print("❌ Нет данных об убийствах")
    else:
        print(f"✅ Найдено убийств: {len(df)}")
        
        print("\nКолонки в данных убийств:")
        print(", ".join(df.columns.tolist()))
        
        # Первые 3 убийства
        print("\nПервые 3 убийства:")
        print("-"*70)
        
        for i, (idx, kill) in enumerate(df.head(3).iterrows(), 1):
            print(f"\n{i}. Убийство:")
            print(f"   Тик: {kill.get('tick', '?')}")
            print(f"   Убийца: {kill.get('attacker_name', '?')}")
            print(f"   Жертва: {kill.get('user_name', '?')}")
            print(f"   Оружие: {kill.get('weapon', '?')}")
            
            # Проверяем координаты
            x_cols = [col for col in df.columns if 'x' in col.lower() and 'user' in col.lower()]
            y_cols = [col for col in df.columns if 'y' in col.lower() and 'user' in col.lower()]
            
            if x_cols and y_cols:
                x = kill.get(x_cols[0], None)
                y = kill.get(y_cols[0], None)
                print(f"   ✅ Координаты: X={x}, Y={y}")
            else:
                print(f"   ⚠️ Координаты не найдены")
                print(f"   Доступные колонки с координатами:")
                coord_cols = [col for col in df.columns if 'x' in col.lower() or 'y' in col.lower()]
                for col in coord_cols:
                    print(f"      - {col}")
    
    # Проверяем тики игроков
    print("\n" + "="*70)
    print("👥 ПОЗИЦИИ ИГРОКОВ")
    print("="*70)
    
    try:
        # Парсим тики с позициями
        ticks_df = parser.parse_ticks(["X", "Y", "health", "team_name", "name"])
        
        if ticks_df is None or ticks_df.empty:
            print("❌ Нет данных о позициях игроков")
        else:
            print(f"✅ Найдено записей: {len(ticks_df)}")
            print(f"   Колонки: {', '.join(ticks_df.columns.tolist())}")
            
            # Проверяем бомбу
            if 'has_bomb' in ticks_df.columns:
                bomb_count = len(ticks_df[ticks_df['has_bomb'] == True])
                print(f"   ✅ Колонка 'has_bomb' найдена ({bomb_count} записей)")
            else:
                print(f"   ⚠️ Колонка 'has_bomb' НЕ найдена")
                print(f"   Доступные колонки про бомбу:")
                bomb_cols = [col for col in ticks_df.columns if 'bomb' in col.lower()]
                if bomb_cols:
                    for col in bomb_cols:
                        print(f"      - {col}")
                else:
                    print(f"      (нет)")
                    
    except Exception as e:
        print(f"⚠️ Ошибка при парсинге тиков: {e}")
    
    # Итоговый отчёт
    print("\n" + "="*70)
    print("📋 ИТОГОВЫЙ ОТЧЁТ")
    print("="*70)
    
    print("\n✅ МАРКЕРЫ УБИЙСТВ:")
    if df is not None and not df.empty:
        x_cols = [col for col in df.columns if 'x' in col.lower() and 'user' in col.lower()]
        y_cols = [col for col in df.columns if 'y' in col.lower() and 'user' in col.lower()]
        
        if x_cols and y_cols:
            print("   ✓ Данные доступны, должны работать")
            print(f"   ✓ Используйте колонки: {x_cols[0]}, {y_cols[0]}")
        else:
            print("   ⚠️ Убийства есть, но координаты нужно найти")
            print(f"   → Проверьте колонки: {', '.join(df.columns.tolist())}")
    else:
        print("   ❌ Нет данных об убийствах")
    
    print("\n💣 ИНДИКАТОР БОМБЫ:")
    print("   → Зависит от обработки в data_processor.py")
    print("   → Запустите приложение для проверки")
    
    print("\n💡 СЛЕДУЮЩИЙ ШАГ:")
    print("   Запустите приложение и проверьте визуально:")
    print("   python -m src.gui.main_window")


def main():
    if len(sys.argv) < 2:
        print("❌ Использование: python check_demo_simple.py путь/к/демке.dem")
        print("\nПример:")
        print("  python check_demo_simple.py demos\\test2.dem")
        sys.exit(1)
    
    demo_path = sys.argv[1]
    
    if not Path(demo_path).exists():
        print(f"❌ Файл не найден: {demo_path}")
        sys.exit(1)
    
    analyze_demo(demo_path)


if __name__ == "__main__":
    main()   