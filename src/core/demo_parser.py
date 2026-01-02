"""
Парсер CS:GO/CS2 демо файлов
Использует demoparser2 для извлечения данных
"""
import asyncio
from pathlib import Path
from typing import Optional

from demoparser2 import DemoParser

from .models import (
    Match, Round, Player, Kill, Damage, Position,
    Team, RoundEndReason, PlayerFrame, GameFrame
)
from ..utils.logger import log, log_async_execution_time
from ..utils.config import config


class DemoParserWrapper:
    """Обёртка над demoparser2 для удобной работы"""
    
    def __init__(self, demo_path: str):
        self.demo_path = Path(demo_path)
        self.parser: Optional[DemoParser] = None
        self.match: Optional[Match] = None
        
        if not self.demo_path.exists():
            raise FileNotFoundError(f"Demo file not found: {demo_path}")
        
        log.info(f"Initialized parser for: {self.demo_path.name}")
    
    @log_async_execution_time
    async def parse(self) -> Match:
        """
        Парсинг демо файла
        Извлекает всю информацию о матче
        """
        log.info(f"Starting parse: {self.demo_path.name}")
        
        try:
            # Создаём парсер
            self.parser = DemoParser(str(self.demo_path))
            
            # Получаем базовую информацию
            header = await self._parse_header()
            
            # Создаём объект матча
            self.match = Match(
                demo_path=str(self.demo_path),
                map_name=header["map_name"],
                demo_type=header["demo_type"],
                server_name=header.get("server_name"),
                tick_rate=header.get("tick_rate", 64),
            )
            
            # Парсим события и данные
            await self._parse_players()
            await self._parse_rounds()
            
            log.info(
                f"Parse completed: {self.match.map_name}, "
                f"{self.match.total_rounds} rounds, "
                f"{len(self.match.players)} players"
            )
            
            return self.match
            
        except Exception as e:
            log.exception(f"Failed to parse demo: {e}")
            raise
    
    async def _parse_header(self) -> dict:
        """Извлечение информации из заголовка"""
        try:
            # Парсим заголовок
            header = self.parser.parse_header()
            
            return {
                "map_name": header.get("map_name", "unknown"),
                "demo_type": "CS2" if "cs2" in str(self.demo_path).lower() else "CS:GO",
                "server_name": header.get("server_name"),
                "tick_rate": header.get("tick_rate", 64),
            }
        except Exception as e:
            log.warning(f"Failed to parse header, using defaults: {e}")
            return {
                "map_name": "unknown",
                "demo_type": "CS:GO",
                "server_name": None,
                "tick_rate": 64,
            }
    
    async def _parse_players(self):
        """Извлечение информации об игроках"""
        log.debug("Parsing players...")
        
        # Используем demoparser2 для получения списка игроков
        # Парсим события для определения игроков
        df = self.parser.parse_event("player_death")
        
        if df is None or df.empty:
            log.warning("No player_death events found")
            return
        
        # Извлекаем уникальных игроков
        unique_players = {}
        
        # Из колонок attacker и victim
        for col in ["attacker_steamid", "attacker_name", "attacker_team_name"]:
            if col in df.columns:
                for idx, row in df.iterrows():
                    steam_id = str(row.get("attacker_steamid", ""))
                    if steam_id and steam_id != "0" and steam_id not in unique_players:
                        unique_players[steam_id] = {
                            "name": row.get("attacker_name", "Unknown"),
                            "team": self._parse_team(row.get("attacker_team_name", "")),
                        }
        
        for col in ["user_steamid", "user_name", "user_team_name"]:
            if col in df.columns:
                for idx, row in df.iterrows():
                    steam_id = str(row.get("user_steamid", ""))
                    if steam_id and steam_id != "0" and steam_id not in unique_players:
                        unique_players[steam_id] = {
                            "name": row.get("user_name", "Unknown"),
                            "team": self._parse_team(row.get("user_team_name", "")),
                        }
        
        # Создаём объекты игроков
        for steam_id, data in unique_players.items():
            player = Player(
                steam_id=steam_id,
                name=data["name"],
                team=data["team"],
            )
            self.match.players[steam_id] = player
            
            # Распределяем по командам
            if player.team == Team.T:
                if steam_id not in self.match.t_players:
                    self.match.t_players.append(steam_id)
            elif player.team == Team.CT:
                if steam_id not in self.match.ct_players:
                    self.match.ct_players.append(steam_id)
        
        log.debug(f"Found {len(self.match.players)} players")
    
    async def _parse_rounds(self):
        """Парсинг раундов и событий"""
        log.debug("Parsing rounds and events...")
        
        # Парсим события завершения раундов
        round_end_df = self.parser.parse_event("round_end")
        
        if round_end_df is None or round_end_df.empty:
            log.warning("No round_end events found")
            return
        
        # Парсим убийства
        kills_df = self.parser.parse_event("player_death")
        
        # Обрабатываем каждый раунд
        for round_num, row in enumerate(round_end_df.itertuples(), start=1):
            round_obj = await self._parse_round(round_num, row, kills_df)
            if round_obj:
                self.match.rounds.append(round_obj)
        
        # Обновляем счёт
        self._update_match_score()
        
        log.debug(f"Parsed {len(self.match.rounds)} rounds")
    
    async def _parse_round(self, round_num: int, round_data, kills_df) -> Optional[Round]:
        """Парсинг одного раунда"""
        try:
            # Определяем победителя
            winner_team = self._parse_team(getattr(round_data, "winner", ""))
            
            # Создаём раунд
            round_obj = Round(
                number=round_num,
                start_tick=getattr(round_data, "tick", 0) - 5000,  # Примерно
                end_tick=getattr(round_data, "tick", 0),
                winner=winner_team,
                end_reason=self._parse_round_end_reason(getattr(round_data, "reason", 0)),
                duration_seconds=0.0,  # Вычислим позже
            )
            
            # Парсим убийства для этого раунда
            if kills_df is not None and not kills_df.empty:
                round_kills = await self._parse_kills_for_round(round_obj, kills_df)
                round_obj.kills = round_kills
            
            return round_obj
            
        except Exception as e:
            log.error(f"Failed to parse round {round_num}: {e}")
            return None
    
    async def _parse_kills_for_round(self, round_obj: Round, kills_df) -> list[Kill]:
        """Извлечение убийств для раунда"""
        kills = []
        
        for idx, row in kills_df.iterrows():
            try:
                tick = row.get("tick", 0)
                
                # Проверяем что убийство в этом раунде
                if not (round_obj.start_tick <= tick <= round_obj.end_tick):
                    continue
                
                # Получаем игроков
                attacker_id = str(row.get("attacker_steamid", ""))
                victim_id = str(row.get("user_steamid", ""))
                
                attacker = self.match.players.get(attacker_id)
                victim = self.match.players.get(victim_id)
                
                if not attacker or not victim:
                    continue
                
                # Создаём событие убийства
                kill = Kill(
                    tick=tick,
                    time_seconds=tick / self.match.tick_rate,
                    killer=attacker,
                    victim=victim,
                    weapon=row.get("weapon", "unknown"),
                    is_headshot=row.get("headshot", False),
                    is_wallbang=row.get("penetrated", False),
                )
                
                kills.append(kill)
                
                # Обновляем статистику игроков
                attacker.kills += 1
                if kill.is_headshot:
                    attacker.headshots += 1
                victim.deaths += 1
                
            except Exception as e:
                log.warning(f"Failed to parse kill: {e}")
                continue
        
        return kills
    
    def _parse_team(self, team_name: str) -> Team:
        """Парсинг названия команды"""
        team_name = str(team_name).upper()
        
        if "TERRORIST" in team_name or team_name == "T":
            return Team.T
        elif "CT" in team_name or "COUNTER" in team_name:
            return Team.CT
        elif "SPEC" in team_name:
            return Team.SPECTATOR
        else:
            return Team.UNASSIGNED
    
    def _parse_round_end_reason(self, reason: int) -> RoundEndReason:
        """Парсинг причины окончания раунда"""
        # Маппинг причин (могут отличаться в CS:GO и CS2)
        reason_map = {
            1: RoundEndReason.TARGET_BOMBED,
            7: RoundEndReason.BOMB_DEFUSED,
            8: RoundEndReason.CT_ELIMINATED,
            9: RoundEndReason.T_ELIMINATED,
            12: RoundEndReason.TIME_EXPIRED,
        }
        
        return reason_map.get(reason, RoundEndReason.TIME_EXPIRED)
    
    def _update_match_score(self):
        """Обновление счёта матча"""
        for round_obj in self.match.rounds:
            if round_obj.winner == Team.T:
                self.match.t_score += 1
            elif round_obj.winner == Team.CT:
                self.match.ct_score += 1
    
    @log_async_execution_time
    async def parse_positions(self, tick_interval: int = 16) -> list[GameFrame]:
        """
        Парсинг позиций игроков (для визуализации)
        tick_interval: интервал между снимками (16 = ~4 frames/sec при 64 tick)
        """
        log.info(f"Parsing player positions (interval: {tick_interval} ticks)...")
        
        try:
            # Определяем диапазон тиков для парсинга
            if not self.match.rounds:
                log.warning("No rounds found, cannot parse positions")
                return []
            
            # Находим min и max тики из раундов
            min_tick = min(r.start_tick for r in self.match.rounds)
            max_tick = max(r.end_tick for r in self.match.rounds)
            
            # Создаём список тиков для парсинга (только внутри раундов)
            ticks_to_parse = []
            for tick in range(min_tick, max_tick, tick_interval):
                # Проверяем что тик внутри какого-то раунда
                for round_obj in self.match.rounds:
                    if round_obj.start_tick <= tick <= round_obj.end_tick:
                        ticks_to_parse.append(tick)
                        break
            
            log.debug(f"Parsing {len(ticks_to_parse)} ticks from {min_tick} to {max_tick}")
            
            # Парсим тики с позициями
            df = self.parser.parse_ticks(
                ["X", "Y", "Z", "yaw", "health", "armor", "is_alive", "team_name", "active_weapon_name"],
                ticks=ticks_to_parse
            )
            
            if df is None or df.empty:
                log.warning("No position data found")
                return []
            
            frames = []
            
            # Группируем по тикам
            grouped = df.groupby('tick')
            
            for tick, tick_data in grouped:
                # Определяем раунд для этого тика
                round_number = self._get_round_for_tick(tick)
                
                if round_number == 0:
                    continue
                
                game_frame = GameFrame(
                    tick=tick,
                    time_seconds=tick / self.match.tick_rate,
                    round_number=round_number,
                )
                
                # Добавляем позиции игроков
                for idx, row in tick_data.iterrows():
                    steam_id = str(row.get("steamid", ""))
                    player = self.match.players.get(steam_id)
                    
                    if not player:
                        continue
                    
                    # Проверяем наличие координат
                    x = row.get("X")
                    y = row.get("Y")
                    z = row.get("Z")
                    
                    if x is None or y is None or z is None:
                        continue
                    
                    position = Position(
                        x=float(x),
                        y=float(y),
                        z=float(z),
                    )
                    
                    player_frame = PlayerFrame(
                        tick=tick,
                        time_seconds=tick / self.match.tick_rate,
                        player=player,
                        position=position,
                        view_angle=float(row.get("yaw", 0)),
                        health=int(row.get("health", 100)),
                        armor=int(row.get("armor", 0)),
                        is_alive=bool(row.get("is_alive", True)),
                        active_weapon=row.get("active_weapon_name"),
                    )
                    
                    game_frame.players.append(player_frame)
                
                if game_frame.players:
                    frames.append(game_frame)
            
            log.info(f"Parsed {len(frames)} position frames")
            return frames
            
        except Exception as e:
            log.exception(f"Failed to parse positions: {e}")
            return []
    
    def _get_round_for_tick(self, tick: int) -> int:
        """Определение номера раунда по тику"""
        for round_obj in self.match.rounds:
            if round_obj.start_tick <= tick <= round_obj.end_tick:
                return round_obj.number
        return 0


# Удобная функция для быстрого парсинга
async def parse_demo(demo_path: str) -> Match:
    """
    Быстрый парсинг демо файла
    
    Args:
        demo_path: Путь к .dem файлу
    
    Returns:
        Match объект с данными о матче
    """
    parser = DemoParserWrapper(demo_path)
    return await parser.parse()