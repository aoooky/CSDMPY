
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    String, Integer, Float, Boolean, DateTime, Text, ForeignKey, Enum as SQLEnum
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
import enum


class Base(DeclarativeBase):
    """Базовый класс для всех моделей"""
    pass


class TeamEnum(str, enum.Enum):
    """Команды"""
    T = "T"
    CT = "CT"
    SPECTATOR = "SPECTATOR"
    UNASSIGNED = "UNASSIGNED"


class DemoTypeEnum(str, enum.Enum):
    """Тип демо"""
    CSGO = "CS:GO"
    CS2 = "CS2"


class RoundEndReasonEnum(str, enum.Enum):
    """Причины окончания раунда"""
    TARGET_BOMBED = "target_bombed"
    BOMB_DEFUSED = "bomb_defused"
    T_ELIMINATED = "terrorists_eliminated"
    CT_ELIMINATED = "cts_eliminated"
    TIME_EXPIRED = "time_expired"
    TARGET_SAVED = "target_saved"


class MatchModel(Base):
    """Модель матча"""
    __tablename__ = "matches"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    
    # Основная информация
    demo_path: Mapped[str] = mapped_column(String(500), unique=True, index=True)
    demo_filename: Mapped[str] = mapped_column(String(255))
    map_name: Mapped[str] = mapped_column(String(50), index=True)
    demo_type: Mapped[str] = mapped_column(SQLEnum(DemoTypeEnum))
    server_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Временные метки
    parsed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    demo_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    duration_seconds: Mapped[float] = mapped_column(Float)
    tick_rate: Mapped[int] = mapped_column(Integer)
    
    # Счёт
    t_score: Mapped[int] = mapped_column(Integer)
    ct_score: Mapped[int] = mapped_column(Integer)
    total_rounds: Mapped[int] = mapped_column(Integer)
    winner: Mapped[Optional[str]] = mapped_column(SQLEnum(TeamEnum), nullable=True)
    
    # Статистика
    total_kills: Mapped[int] = mapped_column(Integer, default=0)
    total_players: Mapped[int] = mapped_column(Integer, default=0)
    
    # Связи
    players: Mapped[list["PlayerModel"]] = relationship(
        back_populates="match",
        cascade="all, delete-orphan"
    )
    rounds: Mapped[list["RoundModel"]] = relationship(
        back_populates="match",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        return f"<Match {self.id}: {self.map_name} {self.t_score}:{self.ct_score}>"


class PlayerModel(Base):
    """Модель игрока"""
    __tablename__ = "players"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    match_id: Mapped[int] = mapped_column(ForeignKey("matches.id", ondelete="CASCADE"))
    
    # Информация об игроке
    steam_id: Mapped[str] = mapped_column(String(50), index=True)
    name: Mapped[str] = mapped_column(String(100))
    team: Mapped[str] = mapped_column(SQLEnum(TeamEnum))
    
    # Статистика
    kills: Mapped[int] = mapped_column(Integer, default=0)
    deaths: Mapped[int] = mapped_column(Integer, default=0)
    assists: Mapped[int] = mapped_column(Integer, default=0)
    headshots: Mapped[int] = mapped_column(Integer, default=0)
    damage_dealt: Mapped[int] = mapped_column(Integer, default=0)
    damage_taken: Mapped[int] = mapped_column(Integer, default=0)
    
    # Вычисляемые поля
    kd_ratio: Mapped[float] = mapped_column(Float, default=0.0)
    hs_percentage: Mapped[float] = mapped_column(Float, default=0.0)
    adr: Mapped[float] = mapped_column(Float, default=0.0)
    
    # Связи
    match: Mapped["MatchModel"] = relationship(back_populates="players")
    kills_as_killer: Mapped[list["KillModel"]] = relationship(
        foreign_keys="KillModel.killer_id",
        back_populates="killer",
        cascade="all, delete-orphan"
    )
    kills_as_victim: Mapped[list["KillModel"]] = relationship(
        foreign_keys="KillModel.victim_id",
        back_populates="victim",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        return f"<Player {self.id}: {self.name} ({self.team})>"


class RoundModel(Base):
    """Модель раунда"""
    __tablename__ = "rounds"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    match_id: Mapped[int] = mapped_column(ForeignKey("matches.id", ondelete="CASCADE"))
    
    # Информация о раунде
    number: Mapped[int] = mapped_column(Integer)
    start_tick: Mapped[int] = mapped_column(Integer)
    end_tick: Mapped[int] = mapped_column(Integer)
    winner: Mapped[str] = mapped_column(SQLEnum(TeamEnum))
    end_reason: Mapped[str] = mapped_column(SQLEnum(RoundEndReasonEnum))
    duration_seconds: Mapped[float] = mapped_column(Float)
    
    # Экономика
    t_start_money: Mapped[int] = mapped_column(Integer, default=0)
    ct_start_money: Mapped[int] = mapped_column(Integer, default=0)
    
    # Бомба
    bomb_planted: Mapped[bool] = mapped_column(Boolean, default=False)
    bomb_plant_tick: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    bomb_plant_site: Mapped[Optional[str]] = mapped_column(String(1), nullable=True)
    bomb_defused: Mapped[bool] = mapped_column(Boolean, default=False)
    bomb_defuse_tick: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Статистика
    total_kills: Mapped[int] = mapped_column(Integer, default=0)
    t_kills: Mapped[int] = mapped_column(Integer, default=0)
    ct_kills: Mapped[int] = mapped_column(Integer, default=0)
    headshot_percentage: Mapped[float] = mapped_column(Float, default=0.0)
    
    # Связи
    match: Mapped["MatchModel"] = relationship(back_populates="rounds")
    kills: Mapped[list["KillModel"]] = relationship(
        back_populates="round",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        return f"<Round {self.id}: Match {self.match_id} Round {self.number}>"


class KillModel(Base):
    """Модель убийства"""
    __tablename__ = "kills"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    round_id: Mapped[int] = mapped_column(ForeignKey("rounds.id", ondelete="CASCADE"))
    
    # Игроки
    killer_id: Mapped[int] = mapped_column(ForeignKey("players.id", ondelete="CASCADE"))
    victim_id: Mapped[int] = mapped_column(ForeignKey("players.id", ondelete="CASCADE"))
    assister_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("players.id", ondelete="SET NULL"),
        nullable=True
    )
    
    # Информация об убийстве
    tick: Mapped[int] = mapped_column(Integer)
    time_seconds: Mapped[float] = mapped_column(Float)
    weapon: Mapped[str] = mapped_column(String(50))
    
    # Модификаторы
    is_headshot: Mapped[bool] = mapped_column(Boolean, default=False)
    is_wallbang: Mapped[bool] = mapped_column(Boolean, default=False)
    is_noscope: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Позиции
    killer_x: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    killer_y: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    killer_z: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    victim_x: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    victim_y: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    victim_z: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    distance: Mapped[float] = mapped_column(Float, default=0.0)
    
    # Связи
    round: Mapped["RoundModel"] = relationship(back_populates="kills")
    killer: Mapped["PlayerModel"] = relationship(
        foreign_keys=[killer_id],
        back_populates="kills_as_killer"
    )
    victim: Mapped["PlayerModel"] = relationship(
        foreign_keys=[victim_id],
        back_populates="kills_as_victim"
    )
    
    def __repr__(self) -> str:
        return f"<Kill {self.id}: {self.weapon}>"


class WeaponStatsModel(Base):
    """Статистика по оружию для матча"""
    __tablename__ = "weapon_stats"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    match_id: Mapped[int] = mapped_column(ForeignKey("matches.id", ondelete="CASCADE"))
    
    weapon_name: Mapped[str] = mapped_column(String(50), index=True)
    kills: Mapped[int] = mapped_column(Integer, default=0)
    headshots: Mapped[int] = mapped_column(Integer, default=0)
    hs_percentage: Mapped[float] = mapped_column(Float, default=0.0)
    unique_users: Mapped[int] = mapped_column(Integer, default=0)
    
    def __repr__(self) -> str:
        return f"<WeaponStats {self.weapon_name}: {self.kills} kills>"