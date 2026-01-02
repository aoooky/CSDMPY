"""
Модели данных для CS Demo Manager
ФИНАЛЬНАЯ версия - содержит ВСЕ необходимые классы
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict
from datetime import datetime


@dataclass
class Player:
    """Информация об игроке"""
    steamid: str
    name: str
    team: str
    kills: int = 0
    deaths: int = 0
    assists: int = 0
    damage: int = 0
    headshots: int = 0
    mvps: int = 0
    score: int = 0
    
    # Дополнительная статистика
    clutches_won: int = 0
    clutches_lost: int = 0
    first_kills: int = 0
    first_deaths: int = 0
    
    @property
    def kd_ratio(self) -> float:
        """K/D соотношение"""
        return self.kills / max(self.deaths, 1)
    
    @property
    def hs_percentage(self) -> float:
        """Процент хедшотов"""
        return (self.headshots / max(self.kills, 1)) * 100
    
    @property
    def adr(self) -> float:
        """Average Damage per Round (будет вычислено позже)"""
        return 0.0
    
    def to_dict(self) -> Dict:
        """Конвертация в словарь"""
        return {
            'steamid': self.steamid,
            'name': self.name,
            'team': self.team,
            'kills': self.kills,
            'deaths': self.deaths,
            'assists': self.assists,
            'damage': self.damage,
            'headshots': self.headshots,
            'kd_ratio': self.kd_ratio,
            'hs_percentage': self.hs_percentage
        }


@dataclass
class Team:
    """Информация о команде"""
    name: str = "Unknown"
    side: str = "Unknown"  # CT или T
    score: int = 0
    players: List[Player] = field(default_factory=list)
    
    # Статистика команды
    total_kills: int = 0
    total_deaths: int = 0
    total_damage: int = 0
    rounds_won: int = 0
    rounds_lost: int = 0
    
    # Экономика
    total_money_spent: int = 0
    eco_rounds: int = 0
    force_rounds: int = 0
    full_buy_rounds: int = 0
    
    @property
    def player_count(self) -> int:
        """Количество игроков в команде"""
        return len(self.players)
    
    @property
    def total_kd(self) -> float:
        """K/D соотношение команды"""
        return self.total_kills / max(self.total_deaths, 1)
    
    @property
    def average_kd(self) -> float:
        """Средний K/D на игрока"""
        if not self.players:
            return 0.0
        return sum(p.kd_ratio for p in self.players) / len(self.players)
    
    @property
    def win_rate(self) -> float:
        """Процент побед в раундах"""
        total = self.rounds_won + self.rounds_lost
        if total == 0:
            return 0.0
        return (self.rounds_won / total) * 100
    
    def to_dict(self) -> Dict:
        """Конвертация в словарь"""
        return {
            'name': self.name,
            'side': self.side,
            'score': self.score,
            'total_kills': self.total_kills,
            'total_deaths': self.total_deaths,
            'total_kd': self.total_kd,
            'rounds_won': self.rounds_won,
            'win_rate': self.win_rate,
            'players': [p.to_dict() for p in self.players]
        }


@dataclass
class Round:
    """Информация о раунде"""
    round_num: int
    winner: str
    reason: str
    duration: float
    start_tick: int
    end_tick: int
    
    # Дополнительная информация
    winner_side: str = ""  # CT или T
    ct_score: int = 0
    t_score: int = 0
    
    # Экономика
    ct_money: int = 0
    t_money: int = 0
    ct_equipment_value: int = 0
    t_equipment_value: int = 0
    
    # События
    kills: List['Kill'] = field(default_factory=list)
    bomb_planted: bool = False
    bomb_defused: bool = False
    bomb_exploded: bool = False
    
    # Время
    plant_tick: int = 0
    defuse_tick: int = 0
    
    @property
    def kill_count(self) -> int:
        """Количество убийств в раунде"""
        return len(self.kills)
    
    def to_dict(self) -> Dict:
        """Конвертация в словарь"""
        return {
            'round_num': self.round_num,
            'winner': self.winner,
            'winner_side': self.winner_side,
            'reason': self.reason,
            'duration': self.duration,
            'ct_score': self.ct_score,
            't_score': self.t_score,
            'kills': self.kill_count,
            'bomb_planted': self.bomb_planted
        }


@dataclass
class Kill:
    """Информация об убийстве"""
    tick: int
    attacker_steamid: str
    attacker_name: str
    victim_steamid: str
    victim_name: str
    weapon: str
    headshot: bool
    
    # Позиция жертвы
    victim_X: float = 0.0
    victim_Y: float = 0.0
    victim_Z: float = 0.0
    
    # Позиция убийцы
    attacker_X: float = 0.0
    attacker_Y: float = 0.0
    attacker_Z: float = 0.0
    
    # Дополнительно
    penetrated: bool = False
    through_smoke: bool = False
    attacker_blind: bool = False
    distance: float = 0.0
    round_num: int = 0
    
    # Команды
    attacker_team: str = ""
    victim_team: str = ""
    
    @property
    def is_teamkill(self) -> bool:
        """Является ли тимкиллом"""
        return self.attacker_team == self.victim_team and self.attacker_steamid != self.victim_steamid
    
    def to_dict(self) -> Dict:
        """Конвертация в словарь"""
        return {
            'tick': self.tick,
            'attacker_name': self.attacker_name,
            'victim_name': self.victim_name,
            'weapon': self.weapon,
            'headshot': self.headshot,
            'distance': self.distance,
            'penetrated': self.penetrated
        }


@dataclass
class MatchInfo:
    """Общая информация о матче"""
    map_name: str
    duration: float
    date: str
    server_name: str
    tick_rate: int
    
    # Команды
    team1_name: str = "Team 1"
    team2_name: str = "Team 2"
    
    # Счёт
    team1_score: int = 0
    team2_score: int = 0
    
    # Тип матча
    game_mode: str = "competitive"  # competitive, casual, wingman
    demo_source: str = "valve"  # valve, faceit, esea, etc
    
    def to_dict(self) -> Dict:
        """Конвертация в словарь"""
        return {
            'map_name': self.map_name,
            'duration': self.duration,
            'date': self.date,
            'server_name': self.server_name,
            'tick_rate': self.tick_rate,
            'game_mode': self.game_mode
        }


@dataclass
class Damage:
    """Информация об уроне"""
    tick: int
    attacker_steamid: str
    attacker_name: str
    victim_steamid: str
    victim_name: str
    damage: int
    damage_armor: int
    health: int
    armor: int
    weapon: str
    hitgroup: str
    round_num: int = 0


@dataclass
class Match:
    """Полная информация о матче (для БД и GUI)"""
    # Идентификатор
    id: Optional[int] = None
    
    # Файл
    file_path: str = ""
    file_name: str = ""
    file_size: int = 0
    
    # Карта
    map_name: str = ""
    
    # Время
    date: str = ""
    duration: float = 0.0
    parsed_at: Optional[str] = None
    
    # Сервер
    tick_rate: int = 64
    server_name: str = ""
    
    # Тип демо
    demo_type: str = "matchmaking"  # matchmaking, faceit, tournament, etc
    game_mode: str = "competitive"
    
    # Счёт
    score_team1: int = 0
    score_team2: int = 0
    score_ct: int = 0
    score_t: int = 0
    winner: str = ""
    
    # Статистика
    total_rounds: int = 0
    total_kills: int = 0
    total_players: int = 0
    
    # Метаданные
    parser_version: str = "1.0"
    checksum: str = ""
    
    # Связанные данные (не для БД)
    players: List[Player] = field(default_factory=list)
    rounds: List[Round] = field(default_factory=list)
    kills: List[Kill] = field(default_factory=list)
    teams: List[Team] = field(default_factory=list)
    
    @property
    def winner_team(self) -> str:
        """Определение команды-победителя"""
        if self.score_ct > self.score_t:
            return "CT"
        elif self.score_t > self.score_ct:
            return "T"
        else:
            return "Draw"
    
    @property
    def match_score(self) -> str:
        """Счёт в формате строки"""
        return f"{self.score_ct}:{self.score_t}"
    
    @property
    def average_round_duration(self) -> float:
        """Средняя длительность раунда"""
        if not self.rounds:
            return 0.0
        return sum(r.duration for r in self.rounds) / len(self.rounds)
    
    def to_dict(self) -> Dict:
        """Конвертация в словарь"""
        return {
            'id': self.id,
            'file_name': self.file_name,
            'map_name': self.map_name,
            'date': self.date,
            'duration': self.duration,
            'score_ct': self.score_ct,
            'score_t': self.score_t,
            'total_rounds': self.total_rounds,
            'total_kills': self.total_kills,
            'winner_team': self.winner_team
        }


@dataclass
class WeaponStats:
    """Статистика по оружию"""
    weapon_name: str
    kills: int = 0
    headshots: int = 0
    damage: int = 0
    shots_fired: int = 0
    shots_hit: int = 0
    
    @property
    def hs_percentage(self) -> float:
        """Процент хедшотов"""
        return (self.headshots / max(self.kills, 1)) * 100
    
    @property
    def accuracy(self) -> float:
        """Точность"""
        return (self.shots_hit / max(self.shots_fired, 1)) * 100
    
    def to_dict(self) -> Dict:
        """Конвертация в словарь"""
        return {
            'weapon_name': self.weapon_name,
            'kills': self.kills,
            'headshots': self.headshots,
            'hs_percentage': self.hs_percentage,
            'accuracy': self.accuracy
        }


@dataclass
class PlayerRoundStats:
    """Статистика игрока в конкретном раунде"""
    steamid: str
    round_num: int
    kills: int = 0
    deaths: int = 0
    assists: int = 0
    damage: int = 0
    survived: bool = False
    mvp: bool = False


# Вспомогательные функции для создания объектов

def create_match_from_parse_result(parse_result: dict) -> Match:
    """
    Создание объекта Match из результата парсинга
    
    Args:
        parse_result: Результат parse_demo()
        
    Returns:
        Match объект
    """
    info = parse_result.get("info")
    players = parse_result.get("players", [])
    rounds = parse_result.get("rounds", [])
    kills = parse_result.get("kills", [])
    
    # Подсчитываем счёт
    ct_score = sum(1 for r in rounds if "CT" in r.winner)
    t_score = sum(1 for r in rounds if "T" in r.winner or "Terrorist" in r.winner)
    
    return Match(
        map_name=parse_result.get("map_name", info.map_name if info else "unknown"),
        date=info.date if info else "",
        duration=info.duration if info else 0.0,
        tick_rate=info.tick_rate if info else 64,
        server_name=info.server_name if info else "",
        score_ct=ct_score,
        score_t=t_score,
        total_rounds=len(rounds),
        total_kills=len(kills),
        total_players=len(players),
        players=players,
        rounds=rounds,
        kills=kills,
        parsed_at=datetime.now().isoformat()
    )


def create_teams_from_players(players: List[Player]) -> List[Team]:
    """
    Создание команд из списка игроков
    
    Args:
        players: Список игроков
        
    Returns:
        Список команд (обычно 2: CT и T)
    """
    teams_dict = {}
    
    for player in players:
        team_name = player.team
        if team_name not in teams_dict:
            # Определяем сторону
            if "CT" in team_name or "Counter" in team_name:
                side = "CT"
            elif "T" in team_name or "Terrorist" in team_name:
                side = "T"
            else:
                side = "Unknown"
            
            teams_dict[team_name] = Team(
                name=team_name,
                side=side
            )
        
        teams_dict[team_name].players.append(player)
        teams_dict[team_name].total_kills += player.kills
        teams_dict[team_name].total_deaths += player.deaths
        teams_dict[team_name].total_damage += player.damage
    
    return list(teams_dict.values())