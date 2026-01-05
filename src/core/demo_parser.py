
from pathlib import Path
from typing import Dict, List, Optional
import pandas as pd
from loguru import logger

from .models import (
    Player,
    Round,
    Kill,
    MatchInfo
)


def parse_demo(demo_path: str) -> Dict:
    """
    Парсинг демо-файла
    
    Args:
        demo_path: Путь к .dem файлу
        
    Returns:
        Словарь с данными демки
    """
    from demoparser2 import DemoParser
    
    logger.info(f"Parsing demo: {demo_path}")
    
    try:
        # Инициализация парсера
        parser = DemoParser(demo_path)
        
        # Получаем базовую информацию
        header = parser.parse_header()
        logger.debug(f"Header parsed: {header.get('map_name', 'unknown')}")
        
        # Парсим события (demoparser2 требует указать какие)
        logger.debug("Parsing events...")
        player_death = parser.parse_event("player_death")
        round_end = parser.parse_event("round_end")
        round_start = parser.parse_event("round_start")
        
        # Собираем все события
        events = {
            "player_death": player_death,
            "round_end": round_end,
            "round_start": round_start
        }
        
        logger.debug(f"Events parsed: {len(player_death)} kills, {len(round_end)} rounds")
        
        # Парсим позиции игроков (для 2D визуализации)
        logger.debug("Parsing player positions...")
        positions_df = parser.parse_ticks([
            "X", "Y", "Z", "yaw", "pitch",
            "health", "armor", "team_name", "name", "steamid"
        ])
        
        logger.debug(f"Positions parsed: {len(positions_df)} ticks")
        
        # Извлекаем информацию о матче
        match_info = _extract_match_info(header, events)
        
        # Извлекаем игроков
        players = _extract_players(events)
        
        # Извлекаем раунды
        rounds = _extract_rounds(events)
        
        # Извлекаем убийства
        kills = _extract_kills(events)
        
        logger.info(f"Parsing completed: {len(players)} players, {len(rounds)} rounds, {len(kills)} kills")
        
        return {
            "info": match_info,
            "players": players,
            "rounds": rounds,
            "kills": kills,
            "positions": positions_df,
            "map_name": header.get("map_name", "unknown")
        }
        
    except Exception as e:
        logger.error(f"Error parsing demo: {e}")
        raise


def _extract_match_info(header: Dict, events: Dict) -> MatchInfo:
    """Извлечение информации о матче"""
    return MatchInfo(
        map_name=header.get("map_name", "unknown"),
        duration=0,  # Будет вычислено позже
        date=header.get("date", ""),
        server_name=header.get("server_name", ""),
        tick_rate=header.get("tickrate", 64)
    )


def _extract_players(events: Dict) -> List[Player]:
    """Извлечение информации об игроках"""
    # Получаем уникальных игроков из событий
    player_map = {}
    
    # Из событий убийств (теперь это DataFrame)
    if "player_death" in events:
        deaths_df = events["player_death"]
        
        # Итерируемся по DataFrame
        for _, event in deaths_df.iterrows():
            # Убийца
            attacker_steamid = event.get("attacker_steamid")
            if attacker_steamid and attacker_steamid not in player_map:
                player_map[attacker_steamid] = Player(
                    steamid=str(attacker_steamid),
                    name=str(event.get("attacker_name", "Unknown")),
                    team=str(event.get("attacker_team_name", "Unknown")),
                    kills=0,
                    deaths=0,
                    assists=0,
                    damage=0,
                    headshots=0
                )
            
            # Жертва
            victim_steamid = event.get("user_steamid")
            if victim_steamid and victim_steamid not in player_map:
                player_map[victim_steamid] = Player(
                    steamid=str(victim_steamid),
                    name=str(event.get("user_name", "Unknown")),
                    team=str(event.get("user_team_name", "Unknown")),
                    kills=0,
                    deaths=0,
                    assists=0,
                    damage=0,
                    headshots=0
                )
    
    # Подсчитываем статистику
    if "player_death" in events:
        deaths_df = events["player_death"]
        for _, event in deaths_df.iterrows():
            # Убийства
            attacker_steamid = event.get("attacker_steamid")
            if attacker_steamid in player_map:
                player_map[attacker_steamid].kills += 1
                if event.get("headshot", False):
                    player_map[attacker_steamid].headshots += 1
            
            # Смерти
            victim_steamid = event.get("user_steamid")
            if victim_steamid in player_map:
                player_map[victim_steamid].deaths += 1
    
    logger.debug(f"Extracted {len(player_map)} players")
    return list(player_map.values())


def _extract_rounds(events: Dict) -> List[Round]:
    """Извлечение информации о раундах"""
    rounds = []
    
    if "round_end" in events:
        rounds_df = events["round_end"]
        for idx, event in enumerate(rounds_df.iterrows(), 1):
            _, row = event  # iterrows возвращает (index, row)
            rounds.append(Round(
                round_num=idx,
                winner=str(row.get("winner", "Unknown")),
                reason=str(row.get("reason", "")),
                duration=0,  # Будет вычислено
                start_tick=0,
                end_tick=int(row.get("tick", 0))
            ))
    
    logger.debug(f"Extracted {len(rounds)} rounds")
    return rounds


def _extract_kills(events: Dict) -> List[Kill]:
    """Извлечение информации об убийствах"""
    kills = []
    
    if "player_death" in events:
        deaths_df = events["player_death"]
        for _, event in deaths_df.iterrows():
            kills.append(Kill(
                tick=int(event.get("tick", 0)),
                attacker_steamid=str(event.get("attacker_steamid", "")),
                attacker_name=str(event.get("attacker_name", "Unknown")),
                victim_steamid=str(event.get("user_steamid", "")),
                victim_name=str(event.get("user_name", "Unknown")),
                weapon=str(event.get("weapon", "")),
                headshot=bool(event.get("headshot", False)),
                victim_X=float(event.get("user_X", 0)),
                victim_Y=float(event.get("user_Y", 0)),
                victim_Z=float(event.get("user_Z", 0))
            ))
    
    logger.debug(f"Extracted {len(kills)} kills")
    return kills


def parse_demo_async(demo_path: str, callback=None):
    """
    Асинхронный парсинг демо-файла
    
    Args:
        demo_path: Путь к .dem файлу
        callback: Функция для вызова после завершения парсинга
    """
    import threading
    
    def _parse():
        try:
            result = parse_demo(demo_path)
            if callback:
                callback(result)
        except Exception as e:
            logger.error(f"Async parsing error: {e}")
            if callback:
                callback(None)
    
    thread = threading.Thread(target=_parse, daemon=True)
    thread.start()
    
    return thread


class DemoParserWrapper:
    """
    Обёртка для парсера с поддержкой прогресса и отмены
    """
    
    def __init__(self, demo_path: str):
        """
        Инициализация обёртки
        
        Args:
            demo_path: Путь к .dem файлу
        """
        self.demo_path = demo_path
        self.is_cancelled = False
        self.progress = 0.0
        self.status = "idle"
        
        logger.debug(f"DemoParserWrapper initialized for {demo_path}")
    
    async def parse(self, progress_callback=None):
        """
        Асинхронный парсинг с поддержкой прогресса
        
        Args:
            progress_callback: Функция для обновления прогресса (progress, status)
            
        Returns:
            Результат парсинга или None если отменено
        """
        import asyncio
        
        try:
            self.status = "parsing"
            self.progress = 0.0
            
            if progress_callback:
                progress_callback(0.0, "Starting parser...")
            
            logger.info(f"Starting parse: {self.demo_path}")
            
            # Запускаем парсинг в отдельном потоке
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,  # default executor
                self._parse_sync
            )
            
            if self.is_cancelled:
                self.status = "cancelled"
                logger.info("Parse cancelled")
                return None
            
            self.status = "completed"
            self.progress = 1.0
            
            if progress_callback:
                progress_callback(1.0, "Completed")
            
            logger.info(f"Parse completed: {self.demo_path}")
            
            return result
            
        except Exception as e:
            self.status = "error"
            logger.error(f"Parse error: {e}")
            raise
    
    def _parse_sync(self):
        """Синхронный парсинг (выполняется в отдельном потоке)"""
        try:
            # Обновляем прогресс
            self.progress = 0.1
            self.status = "Loading demo file..."
            
            result = parse_demo(self.demo_path)
            
            # Обновляем прогресс
            self.progress = 0.9
            self.status = "Processing data..."
            
            return result
            
        except Exception as e:
            logger.error(f"Sync parse error: {e}")
            raise
    
    def cancel(self):
        """Отмена парсинга"""
        self.is_cancelled = True
        self.status = "cancelled"
        logger.info(f"Parse cancelled: {self.demo_path}")
    
    def get_progress(self) -> tuple[float, str]:
        """
        Получить текущий прогресс
        
        Returns:
            Tuple (progress, status)
        """

        return self.progress, self.status
