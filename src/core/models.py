"""
Модели данных для CS Demo Manager
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional


class Team(str, Enum):
    """Команды"""
    T = "T"
    CT = "CT"
    SPEC = "SPEC"


class WeaponType(str, Enum):
    """Типы оружия"""
    PISTOL = "pistol"
    SMG = "smg"
    RIFLE = "rifle"
    SNIPER = "sniper"
    SHOTGUN = "shotgun"
    HEAVY = "heavy"
    GRENADE = "grenade"
    KNIFE = "knife"
    OTHER = "other"


class GrenadeType(str, Enum):
    """Типы гранат"""
    SMOKE = "smoke"
    FLASHBANG = "flashbang"
    HE = "hegrenade"
    MOLOTOV = "molotov"
    INCENDIARY = "incendiary"
    DECOY = "decoy"


@dataclass
class Position:
    """Позиция на карте"""
    x: float
    y: float
    z: float
    tick: int
    
    def __post_init__(self):
        self.x = float(self.x)
        self.y = float(self.y)
        self.z = float(self.z)


@dataclass
class Grenade:
    """Граната"""
    type: GrenadeType
    thrower_id: int
    thrower_name: str
    team: Team
    tick: int
    
    # Позиции
    throw_position: Position
    detonate_position: Optional[Position] = None
    
    # Траектория (для анимации)
    trajectory: List[Position] = field(default_factory=list)
    
    # Время события
    throw_time: float = 0.0
    detonate_time: Optional[float] = None
    
    # Эффект
    duration: float = 0.0  # Длительность эффекта (smoke=18s, molotov=7s)
    

@dataclass
class Player:
    """Игрок"""
    steam_id: int
    name: str
    team: Team
    
    # Статистика
    kills: int = 0
    deaths: int = 0
    assists: int = 0
    damage_dealt: int = 0
    damage_taken: int = 0
    mvps: int = 0
    score: int = 0
    headshot_kills: int = 0
    
    # Текущее состояние
    health: int = 100
    armor: int = 0
    helmet: bool = False
    money: int = 800
    
    # Оружие
    current_weapon: Optional[str] = None
    
    # Позиции по тикам (для воспроизведения)
    positions: List[Position] = field(default_factory=list)
    
    def add_position(self, x: float, y: float, z: float, tick: int):
        """Добавить позицию"""
        self.positions.append(Position(x, y, z, tick))
    
    @property
    def kd_ratio(self) -> float:
        """K/D соотношение"""
        return self.kills / self.deaths if self.deaths > 0 else float(self.kills)
    
    @property
    def adr(self) -> float:
        """Average Damage per Round"""
        return 0.0  # Будет вычисляться в процессоре
    
    @property
    def hs_percentage(self) -> float:
        """Процент хэдшотов"""
        return (self.headshot_kills / self.kills * 100) if self.kills > 0 else 0.0


@dataclass
class Kill:
    """Убийство"""
    tick: int
    time: float
    killer_id: int
    killer_name: str
    killer_team: Team
    victim_id: int
    victim_name: str
    victim_team: Team
    weapon: str
    is_headshot: bool
    is_wallbang: bool
    is_teamkill: bool
    
    # Позиции
    killer_position: Optional[Position] = None
    victim_position: Optional[Position] = None
    
    # Дистанция убийства
    distance: float = 0.0


@dataclass
class Round:
    """Раунд"""
    number: int
    winner: Team
    reason: str
    duration: float
    
    # Тики раунда
    start_tick: int
    end_tick: int
    freeze_time_end_tick: int
    
    # События
    kills: List[Kill] = field(default_factory=list)
    grenades: List[Grenade] = field(default_factory=list)
    
    # Экономика
    t_money: int = 0
    ct_money: int = 0
    
    # Бомба
    bomb_planted: bool = False
    bomb_defused: bool = False
    bomb_exploded: bool = False
    plant_tick: Optional[int] = None
    defuse_tick: Optional[int] = None
    
    def add_kill(self, kill: Kill):
        """Добавить убийство"""
        self.kills.append(kill)
    
    def add_grenade(self, grenade: Grenade):
        """Добавить гранату"""
        self.grenades.append(grenade)


@dataclass
class Match:
    """Матч"""
    demo_path: str
    map_name: str
    game_type: str  # "csgo" или "cs2"
    server_name: str
    tick_rate: int
    
    # Команды
    t_score: int = 0
    ct_score: int = 0
    winner: Optional[Team] = None
    
    # Дата
    date: datetime = field(default_factory=datetime.now)
    duration: float = 0.0
    
    # Игроки и раунды
    players: Dict[int, Player] = field(default_factory=dict)
    rounds: List[Round] = field(default_factory=list)
    
    # Все убийства
    kills: List[Kill] = field(default_factory=list)
    
    # Все гранаты
    grenades: List[Grenade] = field(default_factory=list)
    
    def add_player(self, player: Player):
        """Добавить игрока"""
        self.players[player.steam_id] = player
    
    def add_round(self, round_obj: Round):
        """Добавить раунд"""
        self.rounds.append(round_obj)
    
    def add_kill(self, kill: Kill):
        """Добавить убийство"""
        self.kills.append(kill)
    
    def add_grenade(self, grenade: Grenade):
        """Добавить гранату"""
        self.grenades.append(grenade)
    
    def get_player(self, steam_id: int) -> Optional[Player]:
        """Получить игрока по Steam ID"""
        return self.players.get(steam_id)
    
    def get_team_players(self, team: Team) -> List[Player]:
        """Получить игроков команды"""
        return [p for p in self.players.values() if p.team == team]
    
    def get_team_stats(self, team: Team) -> dict:
        """Статистика команды"""
        team_players = [
            p for p in self.players.values() 
            if p.team == team
        ]
        
        if not team_players:
            return {
                "players_count": 0,
                "total_kills": 0,
                "total_deaths": 0,
                "total_damage": 0,
                "avg_kills": 0.0,
                "avg_deaths": 0.0,
                "avg_damage": 0.0,
                "kd_ratio": 0.0,
            }
        
        total_kills = sum(p.kills for p in team_players)
        total_deaths = sum(p.deaths for p in team_players)
        total_damage = sum(p.damage_dealt for p in team_players)
        
        return {
            "players_count": len(team_players),
            "total_kills": total_kills,
            "total_deaths": total_deaths,
            "total_damage": total_damage,
            "avg_kills": total_kills / len(team_players),
            "avg_deaths": total_deaths / len(team_players),
            "avg_damage": total_damage / len(team_players),
            "kd_ratio": total_kills / total_deaths if total_deaths > 0 else total_kills,
        }
    
    @property
    def total_rounds(self) -> int:
        """Всего раундов"""
        return len(self.rounds)
    
    @property
    def total_kills(self) -> int:
        """Всего убийств"""
        return len(self.kills)