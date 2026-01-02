
import sys
import asyncio
from pathlib import Path

# Добавляем путь к src
sys.path.insert(0, str(Path(__file__).parent))

from src.core.demo_parser import parse_demo
from src.core.data_processor import DataProcessor
from src.utils.logger import log


async def test_parse(demo_path: str):
    """Тест парсинга демо файла"""
    print("=" * 70)
    print("CS Demo Manager - Parser Test")
    print("=" * 70)
    print()
    
    demo_file = Path(demo_path)
    
    if not demo_file.exists():
        print(f"❌ Error: Demo file not found: {demo_path}")
        return False
    
    print(f"📁 Demo file: {demo_file.name}")
    print(f"📊 Size: {demo_file.stat().st_size / (1024*1024):.2f} MB")
    print()
    
    try:
        # Парсинг
        print("⏳ Parsing demo...")
        match = await parse_demo(demo_path)
        print("✅ Parse completed!")
        print()
        
        # Основная информация
        print("=" * 70)
        print("MATCH INFORMATION")
        print("=" * 70)
        print(f"Map:          {match.map_name}")
        print(f"Type:         {match.demo_type}")
        print(f"Server:       {match.server_name or 'N/A'}")
        print(f"Tick rate:    {match.tick_rate}")
        print(f"Total rounds: {match.total_rounds}")
        print(f"Score:        {match.t_score} : {match.ct_score}")
        print(f"Winner:       {match.winner.value if match.winner else 'Draw'}")
        print(f"Total kills:  {match.total_kills}")
        print(f"Players:      {len(match.players)}")
        print()
        
        # Статистика команд
        print("=" * 70)
        print("TEAM STATISTICS")
        print("=" * 70)
        
        processor = DataProcessor(match)
        team_comparison = processor.get_team_comparison()
        
        print("\n🔴 TERRORISTS")
        t_stats = team_comparison["terrorists"]
        print(f"   Score:        {t_stats['score']}")
        print(f"   Players:      {t_stats['players_count']}")
        print(f"   Total kills:  {t_stats['total_kills']}")
        print(f"   Total deaths: {t_stats['total_deaths']}")
        print(f"   K/D ratio:    {t_stats['kd_ratio']:.2f}")
        print(f"   Avg damage:   {t_stats['avg_damage']:.0f}")
        
        print("\n🔵 COUNTER-TERRORISTS")
        ct_stats = team_comparison["counter_terrorists"]
        print(f"   Score:        {ct_stats['score']}")
        print(f"   Players:      {ct_stats['players_count']}")
        print(f"   Total kills:  {ct_stats['total_kills']}")
        print(f"   Total deaths: {ct_stats['total_deaths']}")
        print(f"   K/D ratio:    {ct_stats['kd_ratio']:.2f}")
        print(f"   Avg damage:   {ct_stats['avg_damage']:.0f}")
        print()
        
        # Топ игроков
        print("=" * 70)
        print("TOP PLAYERS")
        print("=" * 70)
        
        leaderboard = processor.get_leaderboard("kills")[:5]
        
        print(f"\n{'#':<3} {'Name':<20} {'Team':<4} {'K':<4} {'D':<4} {'K/D':<6} {'HS%':<6}")
        print("-" * 70)
        
        for i, stats in enumerate(leaderboard, 1):
            print(
                f"{i:<3} {stats['name'][:20]:<20} {stats['team']:<4} "
                f"{stats['kills']:<4} {stats['deaths']:<4} "
                f"{stats['kd_ratio']:<6.2f} {stats['hs_percentage']:<6.1f}"
            )
        print()
        
        # Статистика по оружию
        print("=" * 70)
        print("WEAPON STATISTICS (Top 5)")
        print("=" * 70)
        
        weapon_stats = processor.get_weapon_stats()
        
        print(f"\n{'Weapon':<20} {'Kills':<8} {'HS':<8} {'HS%':<8}")
        print("-" * 70)
        
        for weapon, stats in list(weapon_stats.items())[:5]:
            print(
                f"{weapon:<20} {stats['kills']:<8} "
                f"{stats['headshots']:<8} {stats['hs_percentage']:<8.1f}"
            )
        print()
        
        # Первые убийства
        print("=" * 70)
        print("OPENING KILLS (First 5 rounds)")
        print("=" * 70)
        
        opening_kills = processor.get_opening_kills()[:5]
        
        for ok in opening_kills:
            icon = "💀" if ok["is_headshot"] else "🔫"
            print(
                f"Round {ok['round']:>2}: {icon} {ok['killer_name']:<15} "
                f"({ok['killer_team']}) -> {ok['victim_name']:<15} "
                f"[{ok['weapon']}]"
            )
        print()
        
        # Резюме
        print("=" * 70)
        print("SUMMARY")
        print("=" * 70)
        summary = processor.generate_summary()
        
        if "top_fragger" in summary:
            tf = summary["top_fragger"]
            print(f"\n🏆 Top Fragger: {tf['name']}")
            print(f"   Kills:    {tf['kills']}")
            print(f"   Deaths:   {tf['deaths']}")
            print(f"   K/D:      {tf['kd_ratio']}")
        
        print()
        print("=" * 70)
        print("✅ Test completed successfully!")
        print("=" * 70)
        
        return True
        
    except Exception as e:
        print()
        print("=" * 70)
        print("❌ TEST FAILED")
        print("=" * 70)
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Главная функция"""
    if len(sys.argv) < 2:
        print("Usage: python test_parser.py <path_to_demo.dem>")
        print()
        print("Example:")
        print("  python test_parser.py demos/my_match.dem")
        sys.exit(1)
    
    demo_path = sys.argv[1]
    
    # Запускаем асинхронный тест
    success = asyncio.run(test_parse(demo_path))
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()