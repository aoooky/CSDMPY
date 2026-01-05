
from typing import Optional, Sequence
from pathlib import Path

from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload

from .models import (
    MatchModel, PlayerModel, RoundModel, KillModel, WeaponStatsModel,
    TeamEnum, DemoTypeEnum, RoundEndReasonEnum
)
from .database import db
from ..core.models import Match, Player, Round, Kill, Team
from ..utils.logger import log, log_async_execution_time


class MatchRepository:
    """Репозиторий для работы с матчами"""
    
    @staticmethod
    @log_async_execution_time
    async def create_from_match(match: Match) -> MatchModel:
        """
        Сохранить Match объект в БД
        
        Args:
            match: Match объект из парсера
        
        Returns:
            MatchModel - сохранённая модель
        """
        async with db.session() as session:
            # Создаём модель матча
            match_model = MatchModel(
                demo_path=match.demo_path,
                demo_filename=Path(match.demo_path).name,
                map_name=match.map_name,
                demo_type=DemoTypeEnum.CS2 if match.demo_type == "CS2" else DemoTypeEnum.CSGO,
                server_name=match.server_name,
                parsed_at=match.parsed_at,
                duration_seconds=match.duration_seconds,
                tick_rate=match.tick_rate,
                t_score=match.t_score,
                ct_score=match.ct_score,
                total_rounds=match.total_rounds,
                winner=match.winner.value if match.winner else None,
                total_kills=match.total_kills,
                total_players=len(match.players),
            )
            
            session.add(match_model)
            await session.flush()  # Получаем ID
            
            # Создаём игроков
            player_models = {}
            for steam_id, player in match.players.items():
                player_model = PlayerModel(
                    match_id=match_model.id,
                    steam_id=player.steam_id,
                    name=player.name,
                    team=player.team.value,
                    kills=player.kills,
                    deaths=player.deaths,
                    assists=player.assists,
                    headshots=player.headshots,
                    damage_dealt=player.damage_dealt,
                    damage_taken=player.damage_taken,
                    kd_ratio=player.kills / player.deaths if player.deaths > 0 else player.kills,
                    hs_percentage=(player.headshots / player.kills * 100) if player.kills > 0 else 0,
                    adr=player.damage_dealt / len(match.rounds) if match.rounds else 0,
                )
                session.add(player_model)
                player_models[steam_id] = player_model
            
            await session.flush()
            
            # Создаём раунды и убийства
            for round_obj in match.rounds:
                round_model = RoundModel(
                    match_id=match_model.id,
                    number=round_obj.number,
                    start_tick=round_obj.start_tick,
                    end_tick=round_obj.end_tick,
                    winner=round_obj.winner.value,
                    end_reason=round_obj.end_reason.value,
                    duration_seconds=round_obj.duration_seconds,
                    t_start_money=round_obj.t_start_money,
                    ct_start_money=round_obj.ct_start_money,
                    bomb_planted=round_obj.bomb_planted,
                    bomb_plant_tick=round_obj.bomb_plant_tick,
                    bomb_plant_site=round_obj.bomb_plant_site,
                    bomb_defused=round_obj.bomb_defused,
                    bomb_defuse_tick=round_obj.bomb_defuse_tick,
                    total_kills=len(round_obj.kills),
                    t_kills=round_obj.t_kills,
                    ct_kills=round_obj.ct_kills,
                    headshot_percentage=round_obj.headshot_percentage,
                )
                session.add(round_model)
                await session.flush()
                
                # Создаём убийства
                for kill in round_obj.kills:
                    killer_model = player_models.get(kill.killer.steam_id)
                    victim_model = player_models.get(kill.victim.steam_id)
                    
                    if not killer_model or not victim_model:
                        continue
                    
                    kill_model = KillModel(
                        round_id=round_model.id,
                        killer_id=killer_model.id,
                        victim_id=victim_model.id,
                        tick=kill.tick,
                        time_seconds=kill.time_seconds,
                        weapon=kill.weapon,
                        is_headshot=bool(kill.is_headshot),
                        is_wallbang=bool(kill.is_wallbang),
                        is_noscope=bool(kill.is_noscope),
                        killer_x=kill.killer_position.x if kill.killer_position else None,
                        killer_y=kill.killer_position.y if kill.killer_position else None,
                        killer_z=kill.killer_position.z if kill.killer_position else None,
                        victim_x=kill.victim_position.x if kill.victim_position else None,
                        victim_y=kill.victim_position.y if kill.victim_position else None,
                        victim_z=kill.victim_position.z if kill.victim_position else None,
                        distance=kill.distance,
                    )
                    session.add(kill_model)
            
            await session.commit()
            
            log.info(f"Match saved to database: {match_model.id}")
            return match_model
    
    @staticmethod
    async def get_by_id(match_id: int) -> Optional[MatchModel]:
        """Получить матч по ID"""
        async with db.session() as session:
            result = await session.execute(
                select(MatchModel)
                .options(
                    selectinload(MatchModel.players),
                    selectinload(MatchModel.rounds)
                )
                .where(MatchModel.id == match_id)
            )
            return result.scalar_one_or_none()
    
    @staticmethod
    async def get_by_demo_path(demo_path: str) -> Optional[MatchModel]:
        """Получить матч по пути к демо файлу"""
        async with db.session() as session:
            result = await session.execute(
                select(MatchModel)
                .where(MatchModel.demo_path == demo_path)
            )
            return result.scalar_one_or_none()
    
    @staticmethod
    async def exists(demo_path: str) -> bool:
        """Проверить существует ли матч в БД"""
        async with db.session() as session:
            result = await session.execute(
                select(func.count(MatchModel.id))
                .where(MatchModel.demo_path == demo_path)
            )
            count = result.scalar()
            return count > 0
    
    @staticmethod
    async def get_all(
        limit: int = 100,
        offset: int = 0,
        map_name: Optional[str] = None,
        demo_type: Optional[str] = None
    ) -> Sequence[MatchModel]:
        """
        Получить список матчей с фильтрацией
        
        Args:
            limit: Максимальное количество
            offset: Смещение
            map_name: Фильтр по карте
            demo_type: Фильтр по типу демо
        """
        async with db.session() as session:
            query = select(MatchModel).order_by(MatchModel.parsed_at.desc())
            
            if map_name:
                query = query.where(MatchModel.map_name == map_name)
            
            if demo_type:
                query = query.where(MatchModel.demo_type == demo_type)
            
            query = query.limit(limit).offset(offset)
            
            result = await session.execute(query)
            return result.scalars().all()
    
    @staticmethod
    async def count(
        map_name: Optional[str] = None,
        demo_type: Optional[str] = None
    ) -> int:
        """Подсчитать количество матчей"""
        async with db.session() as session:
            query = select(func.count(MatchModel.id))
            
            if map_name:
                query = query.where(MatchModel.map_name == map_name)
            
            if demo_type:
                query = query.where(MatchModel.demo_type == demo_type)
            
            result = await session.execute(query)
            return result.scalar()
    
    @staticmethod
    async def delete(match_id: int) -> bool:
        """
        Удалить матч
        
        Returns:
            True если удалён успешно
        """
        async with db.session() as session:
            match = await session.get(MatchModel, match_id)
            
            if not match:
                return False
            
            await session.delete(match)
            await session.commit()
            
            log.info(f"Match {match_id} deleted from database")
            return True
    
    @staticmethod
    async def search(query: str, limit: int = 50) -> Sequence[MatchModel]:
        """
        Поиск матчей
        
        Args:
            query: Поисковый запрос
            limit: Максимальное количество результатов
        """
        async with db.session() as session:
            search_pattern = f"%{query}%"
            
            result = await session.execute(
                select(MatchModel)
                .where(
                    or_(
                        MatchModel.map_name.ilike(search_pattern),
                        MatchModel.demo_filename.ilike(search_pattern),
                        MatchModel.server_name.ilike(search_pattern)
                    )
                )
                .order_by(MatchModel.parsed_at.desc())
                .limit(limit)
            )
            
            return result.scalars().all()


class PlayerRepository:
    """Репозиторий для работы с игроками"""
    
    @staticmethod
    async def get_by_steam_id(steam_id: str) -> Sequence[PlayerModel]:
        """Получить все записи игрока по Steam ID"""
        async with db.session() as session:
            result = await session.execute(
                select(PlayerModel)
                .where(PlayerModel.steam_id == steam_id)
                .options(selectinload(PlayerModel.match))
                .order_by(PlayerModel.match_id.desc())
            )
            return result.scalars().all()
    
    @staticmethod
    async def get_player_stats(steam_id: str) -> dict:
        """
        Получить агрегированную статистику игрока
        
        Returns:
            Словарь со статистикой по всем матчам
        """
        async with db.session() as session:
            result = await session.execute(
                select(
                    func.count(PlayerModel.id).label("matches_played"),
                    func.sum(PlayerModel.kills).label("total_kills"),
                    func.sum(PlayerModel.deaths).label("total_deaths"),
                    func.sum(PlayerModel.assists).label("total_assists"),
                    func.sum(PlayerModel.headshots).label("total_headshots"),
                    func.sum(PlayerModel.damage_dealt).label("total_damage"),
                    func.avg(PlayerModel.kd_ratio).label("avg_kd"),
                    func.avg(PlayerModel.hs_percentage).label("avg_hs"),
                    func.avg(PlayerModel.adr).label("avg_adr"),
                )
                .where(PlayerModel.steam_id == steam_id)
            )
            
            row = result.one_or_none()
            
            if not row:
                return {}
            
            return {
                "matches_played": row.matches_played or 0,
                "total_kills": row.total_kills or 0,
                "total_deaths": row.total_deaths or 0,
                "total_assists": row.total_assists or 0,
                "total_headshots": row.total_headshots or 0,
                "total_damage": row.total_damage or 0,
                "avg_kd": float(row.avg_kd) if row.avg_kd else 0.0,
                "avg_hs": float(row.avg_hs) if row.avg_hs else 0.0,
                "avg_adr": float(row.avg_adr) if row.avg_adr else 0.0,
            }
    
    @staticmethod
    async def get_top_players(limit: int = 10) -> Sequence[tuple]:
        """
        Получить топ игроков
        
        Returns:
            Список кортежей (steam_id, name, total_kills, matches)
        """
        async with db.session() as session:
            result = await session.execute(
                select(
                    PlayerModel.steam_id,
                    PlayerModel.name,
                    func.sum(PlayerModel.kills).label("total_kills"),
                    func.count(PlayerModel.id).label("matches")
                )
                .group_by(PlayerModel.steam_id, PlayerModel.name)
                .order_by(func.sum(PlayerModel.kills).desc())
                .limit(limit)
            )
            
            return result.all()


class StatsRepository:
    """Репозиторий для статистики"""
    
    @staticmethod
    async def get_maps_stats() -> Sequence[tuple]:
        """
        Статистика по картам
        
        Returns:
            Список кортежей (map_name, matches_count, avg_t_score, avg_ct_score)
        """
        async with db.session() as session:
            result = await session.execute(
                select(
                    MatchModel.map_name,
                    func.count(MatchModel.id).label("matches"),
                    func.avg(MatchModel.t_score).label("avg_t_score"),
                    func.avg(MatchModel.ct_score).label("avg_ct_score")
                )
                .group_by(MatchModel.map_name)
                .order_by(func.count(MatchModel.id).desc())
            )
            
            return result.all()
    
    @staticmethod
    async def get_total_stats() -> dict:
        """Общая статистика по всем матчам"""
        async with db.session() as session:
            result = await session.execute(
                select(
                    func.count(MatchModel.id).label("total_matches"),
                    func.sum(MatchModel.total_kills).label("total_kills"),
                    func.sum(MatchModel.total_rounds).label("total_rounds"),
                )
            )
            
            row = result.one_or_none()
            
            if not row:
                return {}
            
            return {
                "total_matches": row.total_matches or 0,
                "total_kills": row.total_kills or 0,
                "total_rounds": row.total_rounds or 0,

            }
