
from typing import Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QTableWidget, QTableWidgetItem, QTabWidget,
    QHeaderView, QPushButton, QGroupBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from ..core.models import Match
from ..core.data_processor import DataProcessor
from ..utils.logger import log


class StatsPanel(QWidget):
    """Панель со статистикой матча"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.match: Optional[Match] = None
        self.processor: Optional[DataProcessor] = None
        
        self._init_ui()
        
        log.debug("StatsPanel initialized")
    
    def _init_ui(self):
        """Инициализация UI"""
        layout = QVBoxLayout(self)
        
        # Заголовок
        title = QLabel("📊 Match Statistics")
        title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        layout.addWidget(title)
        
        # Табы для разных видов статистики
        self.tabs = QTabWidget()
        
        # Таб 1: Общая информация
        self.overview_tab = self._create_overview_tab()
        self.tabs.addTab(self.overview_tab, "Overview")
        
        # Таб 2: Игроки
        self.players_tab = self._create_players_tab()
        self.tabs.addTab(self.players_tab, "Players")
        
        # Таб 3: Раунды
        self.rounds_tab = self._create_rounds_tab()
        self.tabs.addTab(self.rounds_tab, "Rounds")
        
        # Таб 4: Оружие
        self.weapons_tab = self._create_weapons_tab()
        self.tabs.addTab(self.weapons_tab, "Weapons")
        
        layout.addWidget(self.tabs)
        
        # Placeholder
        self.placeholder = QLabel(
            "No data\n\nParse a demo to see statistics"
        )
        self.placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.placeholder.setStyleSheet("""
            QLabel {
                color: #999;
                font-size: 14px;
                padding: 50px;
            }
        """)
        layout.addWidget(self.placeholder)
        
        # Изначально показываем placeholder
        self.tabs.hide()
    
    def _create_overview_tab(self) -> QWidget:
        """Создание таба с общей информацией"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Информация о матче
        self.match_info_label = QLabel()
        self.match_info_label.setWordWrap(True)
        self.match_info_label.setStyleSheet("font-size: 12px; padding: 10px;")
        layout.addWidget(self.match_info_label)
        
        # Сравнение команд
        teams_group = QGroupBox("Team Comparison")
        teams_layout = QHBoxLayout(teams_group)
        
        # Террористы
        self.t_stats_label = QLabel()
        self.t_stats_label.setStyleSheet("""
            background-color: #ffebcd;
            padding: 15px;
            border-radius: 5px;
            font-size: 11px;
        """)
        teams_layout.addWidget(self.t_stats_label)
        
        # КТ
        self.ct_stats_label = QLabel()
        self.ct_stats_label.setStyleSheet("""
            background-color: #e6f3ff;
            padding: 15px;
            border-radius: 5px;
            font-size: 11px;
        """)
        teams_layout.addWidget(self.ct_stats_label)
        
        layout.addWidget(teams_group)
        layout.addStretch()
        
        return widget
    
    def _create_players_tab(self) -> QWidget:
        """Создание таба с игроками"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Таблица игроков
        self.players_table = QTableWidget()
        self.players_table.setColumnCount(8)
        self.players_table.setHorizontalHeaderLabels([
            "Name", "Team", "K", "D", "A", "K/D", "HS%", "ADR"
        ])
        
        # Настройка таблицы
        header = self.players_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for i in range(1, 8):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)
        
        self.players_table.setAlternatingRowColors(True)
        self.players_table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        
        layout.addWidget(self.players_table)
        
        return widget
    
    def _create_rounds_tab(self) -> QWidget:
        """Создание таба с раундами"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Таблица раундов
        self.rounds_table = QTableWidget()
        self.rounds_table.setColumnCount(6)
        self.rounds_table.setHorizontalHeaderLabels([
            "Round", "Winner", "Reason", "Duration", "Kills", "HS%"
        ])
        
        # Настройка таблицы
        header = self.rounds_table.horizontalHeader()
        for i in range(6):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.Stretch)
        
        self.rounds_table.setAlternatingRowColors(True)
        
        layout.addWidget(self.rounds_table)
        
        return widget
    
    def _create_weapons_tab(self) -> QWidget:
        """Создание таба с оружием"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Таблица оружия
        self.weapons_table = QTableWidget()
        self.weapons_table.setColumnCount(4)
        self.weapons_table.setHorizontalHeaderLabels([
            "Weapon", "Kills", "Headshots", "HS%"
        ])
        
        # Настройка таблицы
        header = self.weapons_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for i in range(1, 4):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)
        
        self.weapons_table.setAlternatingRowColors(True)
        
        layout.addWidget(self.weapons_table)
        
        return widget
    
    def load_match(self, match: Match):
        """
        Загрузить статистику матча
        
        Args:
            match: Match объект
        """
        self.match = match
        self.processor = DataProcessor(match)
        
        # Скрываем placeholder, показываем табы
        self.placeholder.hide()
        self.tabs.show()
        
        # Обновляем все табы
        self._update_overview()
        self._update_players()
        self._update_rounds()
        self._update_weapons()
        
        log.info(f"Stats loaded for match: {match.map_name}")
    
    def _update_overview(self):
        """Обновление таба Overview"""
        if not self.match or not self.processor:
            return
        
        # Информация о матче
        summary = self.processor.generate_summary()
        
        info_text = f"""
        <b>Map:</b> {summary['map']}<br>
        <b>Type:</b> {summary['demo_type']}<br>
        <b>Score:</b> {summary['score']}<br>
        <b>Winner:</b> {summary['winner']}<br>
        <b>Total Rounds:</b> {summary['total_rounds']}<br>
        <b>Total Kills:</b> {summary['total_kills']}<br>
        <b>Players:</b> {summary['players_count']}<br>
        """
        
        if 'top_fragger' in summary:
            tf = summary['top_fragger']
            info_text += f"""
            <br>
            <b>🏆 Top Fragger:</b> {tf['name']}<br>
            <b>Kills:</b> {tf['kills']} | <b>Deaths:</b> {tf['deaths']} | <b>K/D:</b> {tf['kd_ratio']}
            """
        
        self.match_info_label.setText(info_text)
        
        # Сравнение команд
        comparison = self.processor.get_team_comparison()
        
        t_text = f"""
        <b>🔴 TERRORISTS</b><br>
        Score: {comparison['terrorists']['score']}<br>
        Players: {comparison['terrorists']['players_count']}<br>
        Kills: {comparison['terrorists']['total_kills']}<br>
        Deaths: {comparison['terrorists']['total_deaths']}<br>
        K/D: {comparison['terrorists']['kd_ratio']:.2f}<br>
        Avg Damage: {comparison['terrorists']['avg_damage']:.0f}
        """
        self.t_stats_label.setText(t_text)
        
        ct_text = f"""
        <b>🔵 COUNTER-TERRORISTS</b><br>
        Score: {comparison['counter_terrorists']['score']}<br>
        Players: {comparison['counter_terrorists']['players_count']}<br>
        Kills: {comparison['counter_terrorists']['total_kills']}<br>
        Deaths: {comparison['counter_terrorists']['total_deaths']}<br>
        K/D: {comparison['counter_terrorists']['kd_ratio']:.2f}<br>
        Avg Damage: {comparison['counter_terrorists']['avg_damage']:.0f}
        """
        self.ct_stats_label.setText(ct_text)
    
    def _update_players(self):
        """Обновление таба Players"""
        if not self.processor:
            return
        
        leaderboard = self.processor.get_leaderboard("kills")
        
        self.players_table.setRowCount(len(leaderboard))
        
        for row, stats in enumerate(leaderboard):
            self.players_table.setItem(row, 0, QTableWidgetItem(stats['name']))
            self.players_table.setItem(row, 1, QTableWidgetItem(stats['team']))
            self.players_table.setItem(row, 2, QTableWidgetItem(str(stats['kills'])))
            self.players_table.setItem(row, 3, QTableWidgetItem(str(stats['deaths'])))
            self.players_table.setItem(row, 4, QTableWidgetItem(str(stats['assists'])))
            self.players_table.setItem(row, 5, QTableWidgetItem(f"{stats['kd_ratio']:.2f}"))
            self.players_table.setItem(row, 6, QTableWidgetItem(f"{stats['hs_percentage']:.1f}%"))
            self.players_table.setItem(row, 7, QTableWidgetItem(f"{stats['adr']:.0f}"))
    
    def _update_rounds(self):
        """Обновление таба Rounds"""
        if not self.processor:
            return
        
        rounds_stats = self.processor.get_all_rounds_stats()
        
        self.rounds_table.setRowCount(len(rounds_stats))
        
        for row, stats in enumerate(rounds_stats):
            self.rounds_table.setItem(row, 0, QTableWidgetItem(str(stats['number'])))
            self.rounds_table.setItem(row, 1, QTableWidgetItem(stats['winner']))
            self.rounds_table.setItem(row, 2, QTableWidgetItem(stats['end_reason']))
            self.rounds_table.setItem(row, 3, QTableWidgetItem(f"{stats['duration_seconds']:.1f}s"))
            self.rounds_table.setItem(row, 4, QTableWidgetItem(str(stats['total_kills'])))
            self.rounds_table.setItem(row, 5, QTableWidgetItem(f"{stats['headshot_percentage']:.1f}%"))
    
    def _update_weapons(self):
        """Обновление таба Weapons"""
        if not self.processor:
            return
        
        weapons_stats = self.processor.get_weapon_stats()
        
        self.weapons_table.setRowCount(len(weapons_stats))
        
        for row, (weapon, stats) in enumerate(weapons_stats.items()):
            self.weapons_table.setItem(row, 0, QTableWidgetItem(weapon))
            self.weapons_table.setItem(row, 1, QTableWidgetItem(str(stats['kills'])))
            self.weapons_table.setItem(row, 2, QTableWidgetItem(str(stats['headshots'])))
            self.weapons_table.setItem(row, 3, QTableWidgetItem(f"{stats['hs_percentage']:.1f}%"))
    
    def clear(self):
        """Очистить статистику"""
        self.match = None
        self.processor = None
        
        self.tabs.hide()
        self.placeholder.show()
        
        # Очистка таблиц
        self.players_table.setRowCount(0)
        self.rounds_table.setRowCount(0)
        self.weapons_table.setRowCount(0)