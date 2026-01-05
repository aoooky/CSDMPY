
import argparse
from typing import Dict, Tuple, List


# Официальные координаты радара CS2
OFFICIAL_RADAR_CONFIGS = {
    "de_inferno": {
        "pos_x": -2087,
        "pos_y": 3870,
        "scale": 4.9
    },
    "de_dust2": {
        "pos_x": -2476,
        "pos_y": 3239,
        "scale": 4.4
    },
    "de_mirage": {
        "pos_x": -3230,
        "pos_y": 1713,
        "scale": 5.0
    },
    "de_nuke": {
        "pos_x": -3453,
        "pos_y": 2887,
        "scale": 7.0
    },
}


# Тестовые координаты известных позиций на картах
# Формат: {map_name: {position_name: {"world": (x, y), "expected_radar": (x, y)}}}
TEST_POSITIONS = {
    "de_inferno": {
        "CT_spawn": {
            "world": (2353, 1977),
            "expected_radar": (0.88, 0.38)
        },
        "T_spawn": {
            "world": (-1650, 718),
            "expected_radar": (0.09, 0.64)
        },
        "bombsite_A": {
            "world": (1800, 2600),
            "expected_radar": (0.77, 0.25)
        },
        "bombsite_B": {
            "world": (200, 200),
            "expected_radar": (0.46, 0.73)
        },
    },
    "de_dust2": {
        "CT_spawn": {
            "world": (1000, 2400),
            "expected_radar": (0.77, 0.19)
        },
        "T_spawn": {
            "world": (-1300, 250),
            "expected_radar": (0.26, 0.66)
        },
    },
    "de_mirage": {
        "CT_spawn": {
            "world": (-1500, 300),
            "expected_radar": (0.34, 0.28)
        },
        "T_spawn": {
            "world": (-2300, -500),
            "expected_radar": (0.18, 0.43)
        },
    },
}


def world_to_radar_official(world_x: float, world_y: float, config: Dict) -> Tuple[float, float]:
    """Конвертирует мировые координаты в радарные с использованием официальной формулы."""
    scale = config["scale"] * 1024
    radar_x = (world_x - config["pos_x"]) / scale
    radar_y = (world_y - config["pos_y"]) / -scale  # Отрицательный знак!
    return radar_x, radar_y


def test_map_calibration(map_name: str) -> Dict:
    """
    Тестирует калибровку конкретной карты.
    
    Returns:
        Dict с результатами тестирования
    """
    print(f"\n{'='*70}")
    print(f"ТЕСТИРОВАНИЕ: {map_name.upper()}")
    print(f"{'='*70}")
    
    # Проверяем наличие конфигурации
    if map_name not in OFFICIAL_RADAR_CONFIGS:
        print(f"⚠️ Нет официальной конфигурации для {map_name}")
        return {"map": map_name, "status": "no_config"}
    
    config = OFFICIAL_RADAR_CONFIGS[map_name]
    
    # Показываем параметры радара
    print(f"\nПараметры радара:")
    print(f"  pos_x: {config['pos_x']}")
    print(f"  pos_y: {config['pos_y']}")
    print(f"  scale: {config['scale']} (реальный: {config['scale'] * 1024})")
    
    # Проверяем наличие тестовых позиций
    if map_name not in TEST_POSITIONS:
        print(f"\n⚠️ Нет тестовых позиций для {map_name}")
        return {"map": map_name, "status": "no_test_positions", "config": config}
    
    positions = TEST_POSITIONS[map_name]
    
    print(f"\n{'Позиция':<15} {'World X':>10} {'World Y':>10} {'Calc X':>10} {'Calc Y':>10} {'Expect X':>10} {'Expect Y':>10} {'Error':>8} {'Status':>6}")
    print("-" * 95)
    
    results = []
    total_error = 0
    
    for pos_name, data in positions.items():
        world_x, world_y = data["world"]
        expected_x, expected_y = data["expected_radar"]
        
        # Вычисляем координаты
        calc_x, calc_y = world_to_radar_official(world_x, world_y, config)
        
        # Вычисляем погрешность
        error_x = abs(calc_x - expected_x)
        error_y = abs(calc_y - expected_y)
        error = (error_x + error_y) / 2
        
        total_error += error
        
        # Статус
        if error < 0.03:
            status = "✓✓"
        elif error < 0.05:
            status = "✓"
        elif error < 0.10:
            status = "~"
        else:
            status = "✗"
        
        print(f"{pos_name:<15} {world_x:>10.0f} {world_y:>10.0f} "
              f"{calc_x:>10.3f} {calc_y:>10.3f} "
              f"{expected_x:>10.3f} {expected_y:>10.3f} "
              f"{error*100:>7.2f}% {status:>6}")
        
        results.append({
            "position": pos_name,
            "error": error,
            "status": status
        })
    
    # Средняя погрешность
    avg_error = (total_error / len(positions)) * 100
    
    print("-" * 95)
    print(f"\nСредняя погрешность: {avg_error:.2f}%")
    
    # Общая оценка
    if avg_error < 3:
        grade = "ОТЛИЧНО"
        emoji = "✅"
    elif avg_error < 5:
        grade = "ХОРОШО"
        emoji = "✓"
    elif avg_error < 10:
        grade = "ПРИЕМЛЕМО"
        emoji = "~"
    else:
        grade = "ТРЕБУЕТСЯ НАСТРОЙКА"
        emoji = "⚠️"
    
    print(f"{emoji} {grade}: Калибровка работает с точностью {100-avg_error:.1f}%")
    
    return {
        "map": map_name,
        "status": "tested",
        "avg_error": avg_error,
        "grade": grade,
        "results": results
    }


def test_all_maps():
    """Тестирует калибровку всех доступных карт."""
    print("\n" + "="*70)
    print("ТЕСТИРОВАНИЕ ВСЕХ КАРТ")
    print("="*70)
    
    summary = []
    
    for map_name in OFFICIAL_RADAR_CONFIGS.keys():
        result = test_map_calibration(map_name)
        if result["status"] == "tested":
            summary.append(result)
    
    # Общая сводка
    print(f"\n{'='*70}")
    print("СВОДКА РЕЗУЛЬТАТОВ")
    print(f"{'='*70}\n")
    
    print(f"{'Карта':<15} {'Точность':>12} {'Погрешность':>15} {'Оценка':<20}")
    print("-" * 70)
    
    for result in summary:
        accuracy = 100 - result["avg_error"]
        emoji_map = {
            "ОТЛИЧНО": "✅",
            "ХОРОШО": "✓",
            "ПРИЕМЛЕМО": "~",
            "ТРЕБУЕТСЯ НАСТРОЙКА": "⚠️"
        }
        emoji = emoji_map.get(result["grade"], "")
        
        print(f"{result['map']:<15} {accuracy:>11.1f}% {result['avg_error']:>14.2f}% {emoji} {result['grade']:<20}")
    
    print("-" * 70)
    
    # Средняя точность по всем картам
    if summary:
        avg_accuracy = sum(100 - r["avg_error"] for r in summary) / len(summary)
        print(f"\nСредняя точность по всем картам: {avg_accuracy:.1f}%")


def main():
    parser = argparse.ArgumentParser(description="Тест калибровки карт CS2")
    parser.add_argument("--map", type=str, help="Название карты (например, de_inferno)")
    parser.add_argument("--all", action="store_true", help="Тестировать все карты")
    
    args = parser.parse_args()
    
    if args.all:
        test_all_maps()
    elif args.map:
        test_map_calibration(args.map)
    else:
        # По умолчанию тестируем de_inferno
        test_map_calibration("de_inferno")
        
        print("\n" + "="*70)
        print("Используйте опции:")
        print("  --map de_dust2  - тестировать конкретную карту")
        print("  --all           - тестировать все карты")
        print("="*70)


if __name__ == "__main__":
    main()
