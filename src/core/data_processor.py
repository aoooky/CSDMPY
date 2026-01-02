
from typing import Optional
import pandas as pd
from collections import defaultdict

from .models import Match, Player, Round, Team, Kill
from ..utils.logger import log


class DataProcessor:
    """Класс для обработки и анализа данных матча"""
    
    def __init__(self, match: Match):
        self.match = match
    
    def get_player_stats(self, steam_id: str) -> Optional[dict]:
        """
        Получить статистику игрока
        
        Returns:
            Словарь со статистикой или None если игрок не найден
        """
        player = self.match.get_player(steam_id)
        if not player:
            return None
        
        # Базовая статистика
        stats = {
            "steam_id": player.steam_id,
            "name": player.name,
            "team": player.team.value,
            "kills": player.kills,
            "deaths": player.deaths,
            "assists": player.assists,
            "headshots": player.headshots,
            "damage_dealt": player.damage_dealt,
            "damage_taken": player.damage_taken,
        }
        
        # Вычисляемые метрики
        stats["kd_ratio"] = player.kills / player.deaths if player.deaths > 0 else player.kills
        stats["hs_percentage"] = (
            (player.headshots / player.kills * 100) if player.kills > 0 else 0.0
        )
        stats["adr"] = player.damage_dealt / len(self.match.rounds) if self.match.rounds else 0
        
        # Статистика по раундам
        stats["rounds_played"] = len(self.match.rounds)
        
        return stats
    
    def get_all_players_stats(self) -> list[dict]:
        """
        Получить статистику всех игроков
        
        Returns:
            Список словарей со статистикой
        """
        return [
            self.get_player_stats(steam_id)
            for steam_id in self.match.players.keys()
        ]
    
    def get_leaderboard(self, sort_by: str = "kills") -> list[dict]:
        """
        Получить таблицу лидеров
        
        Args:
            sort_by: По какому полю сортировать (kills, damage_dealt, kd_ratio, etc.)
        
        Returns:
            Отсортированный список игроков
        """
        all_stats = self.get_all_players_stats()
        
        # Вычисляем KD ratio для сортировки
        for stats in all_stats:
            if sort_by == "kd_ratio":
                stats["_sort_key"] = stats["kd_ratio"]
            else:
                stats["_sort_key"] = stats.get(sort_by, 0)
        
        # Сортируем
        sorted_stats = sorted(all_stats, key=lambda x: x["_sort_key"], reverse=True)
        
        # Удаляем временный ключ
        for stats in sorted_stats:
            stats.pop("_sort_key", None)
        
        return sorted_stats
    
    def get_round_stats(self, round_number: int) -> Optional[dict]:
        """
        Статистика по конкретному раунду
        
        Args:
            round_number: Номер раунда (1-based)
        
        Returns:
            Словарь со статистикой раунда
        """
        if round_number < 1 or round_number > len(self.match.rounds):
            return None
        
        round_obj = self.match.rounds[round_number - 1]
        
        return {
            "number": round_obj.number,
            "winner": round_obj.winner.value,
            "end_reason": round_obj.end_reason.value,
            "duration_seconds": round_obj.duration_seconds,
            "total_kills": len(round_obj.kills),
            "t_kills": round_obj.t_kills,
            "ct_kills": round_obj.ct_kills,
            "headshot_percentage": round_obj.headshot_percentage,
            "bomb_planted": round_obj.bomb_planted,
            "bomb_defused": round_obj.bomb_defused,
        }
    
    def get_all_rounds_stats(self) -> list[dict]:
        """Статистика по всем раундам"""
        return [
            self.get_round_stats(i + 1)
            for i in range(len(self.match.rounds))
        ]
    
    def get_team_comparison(self) -> dict:
        """
        Сравнение команд
        
        Returns:
            Словарь с сравнительной статистикой команд
        """
        t_stats = self.match.get_team_stats(Team.T)
        ct_stats = self.match.get_team_stats(Team.CT)
        
        return {
            "terrorists": {
                **t_stats,
                "score": self.match.t_score,
                "rounds_won": self.match.t_score,
            },
            "counter_terrorists": {
                **ct_stats,
                "score": self.match.ct_score,
                "rounds_won": self.match.ct_score,
            },
        }
    
    def get_weapon_stats(self) -> dict[str, dict]:
        """
        Статистика по оружию
        
        Returns:
            Словарь с статистикой использования оружия
        """
        weapon_stats = defaultdict(lambda: {
            "kills": 0,
            "headshots": 0,
            "users": set()
        })
        
        for round_obj in self.match.rounds:
            for kill in round_obj.kills:
                weapon = kill.weapon
                weapon_stats[weapon]["kills"] += 1
                if kill.is_headshot:
                    weapon_stats[weapon]["headshots"] += 1
                weapon_stats[weapon]["users"].add(kill.killer.steam_id)
        
        # Конвертируем set в count
        result = {}
        for weapon, stats in weapon_stats.items():
            result[weapon] = {
                "kills": stats["kills"],
                "headshots": stats["headshots"],
                "unique_users": len(stats["users"]),
                "hs_percentage": (
                    stats["headshots"] / stats["kills"] * 100 
                    if stats["kills"] > 0 else 0
                ),
            }
        
        # Сортируем по количеству убийств
        return dict(sorted(result.items(), key=lambda x: x[1]["kills"], reverse=True))
    
    def get_kill_feed(self, round_number: Optional[int] = None) -> list[dict]:
        """
        Лента убийств
        
        Args:
            round_number: Номер раунда (опционально, если None - все раунды)
        
        Returns:
            Список событий убийств
        """
        kill_feed = []
        
        rounds_to_process = (
            [self.match.rounds[round_number - 1]] 
            if round_number 
            else self.match.rounds
        )
        
        for round_obj in rounds_to_process:
            for kill in round_obj.kills:
                kill_feed.append({
                    "round": round_obj.number,
                    "tick": kill.tick,
                    "time_seconds": kill.time_seconds,
                    "killer_name": kill.killer.name,
                    "killer_team": kill.killer.team.value,
                    "victim_name": kill.victim.name,
                    "victim_team": kill.victim.team.value,
                    "weapon": kill.weapon,
                    "is_headshot": kill.is_headshot,
                    "is_wallbang": kill.is_wallbang,
                    "distance": round(kill.distance, 2),
                })
        
        return kill_feed
    
    def get_heatmap_data(self, team: Optional[Team] = None) -> list[tuple[float, float]]:
        """
        Данные для тепловой карты позиций убийств
        
        Args:
            team: Фильтр по команде (опционально)
        
        Returns:
            Список координат (x, y)
        """
        positions = []
        
        for round_obj in self.match.rounds:
            for kill in round_obj.kills:
                # Фильтр по команде
                if team and kill.killer.team != team:
                    continue
                
                if kill.killer_position:
                    positions.append(kill.killer_position.to_2d())
        
        return positions
    
    def export_to_dataframe(self) -> pd.DataFrame:
        """
        Экспорт статистики в pandas DataFrame
        
        Returns:
            DataFrame со статистикой всех игроков
        """
        stats = self.get_all_players_stats()
        return pd.DataFrame(stats)
    
    def export_kills_to_dataframe(self) -> pd.DataFrame:
        """
        Экспорт всех убийств в DataFrame
        
        Returns:
            DataFrame со всеми убийствами
        """
        kills = self.get_kill_feed()
        return pd.DataFrame(kills)
    
    def generate_summary(self) -> dict:
        """
        Генерация краткой сводки о матче
        
        Returns:
            Словарь с основной информацией
        """
        winner = self.match.winner
        top_fragger = self.match.get_top_fraggers(1)[0] if self.match.players else None
        
        summary = {
            "map": self.match.map_name,
            "demo_type": self.match.demo_type,
            "total_rounds": self.match.total_rounds,
            "score": f"{self.match.t_score}:{self.match.ct_score}",
            "winner": winner.value if winner else "Draw",
            "total_kills": self.match.total_kills,
            "players_count": len(self.match.players),
            "duration_seconds": self.match.duration_seconds,
        }
        
        if top_fragger:
            summary["top_fragger"] = {
                "name": top_fragger.name,
                "kills": top_fragger.kills,
                "deaths": top_fragger.deaths,
                "kd_ratio": round(
                    top_fragger.kills / top_fragger.deaths if top_fragger.deaths > 0 else top_fragger.kills,
                    2
                ),
            }
        
        return summary
    
    def find_clutch_situations(self) -> list[dict]:
        """
        Поиск клатч ситуаций (1vX)
        
        Returns:
            Список клатч ситуаций
        """
        clutches = []
        
        for round_obj in self.match.rounds:
            # TODO: Реализовать анализ клатч ситуаций
            # Требует информацию о живых игроках в каждый момент
            pass
        
        return clutches
    
    def get_opening_kills(self) -> list[dict]:
        """
        Первые убийства в раундах
        
        Returns:
            Список первых убийств каждого раунда
        """
        opening_kills = []
        
        for round_obj in self.match.rounds:
            if round_obj.kills:
                first_kill = round_obj.kills[0]
                opening_kills.append({
                    "round": round_obj.number,
                    "killer_name": first_kill.killer.name,
                    "killer_team": first_kill.killer.team.value,
                    "victim_name": first_kill.victim.name,
                    "victim_team": first_kill.victim.team.value,
                    "weapon": first_kill.weapon,
                    "is_headshot": first_kill.is_headshot,
                })
        
        return opening_kills