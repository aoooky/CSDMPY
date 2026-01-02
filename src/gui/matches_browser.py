
import asyncio
from typing import Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QLineEdit, QLabel, QComboBox,
    QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal

from ..database.repository import MatchRepository, StatsRepository
from ..database.models import MatchModel
from ..utils.logger import log


class MatchesBrowser(QWidget):
    """Виджет для просмотра сохранённых матчей"""
    
    # Сигналы
    match_selected = pyqtSignal(int)  # match_id
    match_deleted = pyqtSignal(int)  # match_id
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.matches: list[MatchModel] = []
        self.current_page = 0
        self.page_size = 50
        self.total_matches = 0
        
        self._init_ui()
        
        log.debug("MatchesBrowser initialized")
    
    def _init_ui(self):
        """Инициализация UI"""
        layout = QVBoxLayout(self)
        
        # Заголовок и статистика
        header_layout = QHBoxLayout()
        
        title = QLabel("💾 Saved Matches")
        title.setStyleSheet("font-size: 14px; font-weight: bold;")
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        self.stats_label = QLabel("Total: 0 matches")
        header_layout.addWidget(self.stats_label)
        
        layout.addLayout(header_layout)
        
        # Фильтры и поиск
        filters_layout = QHBoxLayout()
        
        # Поиск
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search by map, filename, server...")
        self.search_input.returnPressed.connect(self._on_search)
        filters_layout.addWidget(self.search_input, stretch=1)
        
        search_btn = QPushButton("🔍 Search")
        search_btn.clicked.connect(self._on_search)
        filters_layout.addWidget(search_btn)
        
        # Фильтр по карте
        filters_layout.addWidget(QLabel("Map:"))
        self.map_filter = QComboBox()
        self.map_filter.addItem("All maps", None)
        for map_name in ["de_dust2", "de_mirage", "de_train", "de_ancient", "de_nuke", "de_overpass", "de_inferno"]:
            self.map_filter.addItem(map_name, map_name)
        self.map_filter.currentIndexChanged.connect(self._on_filter_changed)
        filters_layout.addWidget(self.map_filter)
        
        # Кнопка обновления
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.clicked.connect(self.refresh)
        filters_layout.addWidget(refresh_btn)
        
        layout.addLayout(filters_layout)
        
        # Таблица матчей
        self.matches_table = QTableWidget()
        self.matches_table.setColumnCount(8)
        self.matches_table.setHorizontalHeaderLabels([
            "ID", "Map", "Type", "Score", "Rounds", "Players", "Parsed At", "Actions"
        ])
        
        # Настройка таблицы
        header = self.matches_table.horizontalHeader()
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        for i in [0, 2, 3, 4, 5, 6, 7]:
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)
        
        self.matches_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.matches_table.setAlternatingRowColors(True)
        self.matches_table.cellDoubleClicked.connect(self._on_row_double_clicked)
        
        layout.addWidget(self.matches_table)
        
        # Пагинация
        pagination_layout = QHBoxLayout()
        
        self.prev_btn = QPushButton("◀ Previous")
        self.prev_btn.clicked.connect(self._on_prev_page)
        self.prev_btn.setEnabled(False)
        pagination_layout.addWidget(self.prev_btn)
        
        self.page_label = QLabel("Page 1")
        pagination_layout.addWidget(self.page_label)
        
        self.next_btn = QPushButton("Next ▶")
        self.next_btn.clicked.connect(self._on_next_page)
        self.next_btn.setEnabled(False)
        pagination_layout.addWidget(self.next_btn)
        
        layout.addLayout(pagination_layout)
    
    def refresh(self):
        """Обновить список матчей"""
        log.debug("Refreshing matches list...")
        
        # Получаем фильтры
        map_name = self.map_filter.currentData()
        
        # Загружаем матчи из БД
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Получаем общее количество
            self.total_matches = loop.run_until_complete(
                MatchRepository.count(map_name=map_name)
            )
            
            # Получаем матчи для текущей страницы
            self.matches = loop.run_until_complete(
                MatchRepository.get_all(
                    limit=self.page_size,
                    offset=self.current_page * self.page_size,
                    map_name=map_name
                )
            )
            
            # Обновляем UI
            self._update_table()
            self._update_pagination()
            self._update_stats()
            
            log.info(f"Loaded {len(self.matches)} matches")
            
        except Exception as e:
            log.error(f"Failed to load matches: {e}")
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to load matches from database:\n{e}"
            )
    
    def _update_table(self):
        """Обновить таблицу"""
        self.matches_table.setRowCount(len(self.matches))
        
        for row, match in enumerate(self.matches):
            # ID
            self.matches_table.setItem(row, 0, QTableWidgetItem(str(match.id)))
            
            # Map
            self.matches_table.setItem(row, 1, QTableWidgetItem(match.map_name))
            
            # Type
            self.matches_table.setItem(row, 2, QTableWidgetItem(match.demo_type))
            
            # Score
            score = f"{match.t_score}:{match.ct_score}"
            self.matches_table.setItem(row, 3, QTableWidgetItem(score))
            
            # Rounds
            self.matches_table.setItem(row, 4, QTableWidgetItem(str(match.total_rounds)))
            
            # Players
            self.matches_table.setItem(row, 5, QTableWidgetItem(str(match.total_players)))
            
            # Parsed At
            parsed_str = match.parsed_at.strftime("%Y-%m-%d %H:%M")
            self.matches_table.setItem(row, 6, QTableWidgetItem(parsed_str))
            
            # Actions - кнопка удаления
            delete_btn = QPushButton("🗑️ Delete")
            delete_btn.clicked.connect(lambda checked, m_id=match.id: self._on_delete_clicked(m_id))
            self.matches_table.setCellWidget(row, 7, delete_btn)
    
    def _update_pagination(self):
        """Обновить пагинацию"""
        total_pages = (self.total_matches + self.page_size - 1) // self.page_size
        current_page_display = self.current_page + 1
        
        self.page_label.setText(f"Page {current_page_display} of {total_pages}")
        
        self.prev_btn.setEnabled(self.current_page > 0)
        self.next_btn.setEnabled(current_page_display < total_pages)
    
    def _update_stats(self):
        """Обновить статистику"""
        self.stats_label.setText(f"Total: {self.total_matches} matches")
    
    def _on_prev_page(self):
        """Предыдущая страница"""
        if self.current_page > 0:
            self.current_page -= 1
            self.refresh()
    
    def _on_next_page(self):
        """Следующая страница"""
        total_pages = (self.total_matches + self.page_size - 1) // self.page_size
        if self.current_page < total_pages - 1:
            self.current_page += 1
            self.refresh()
    
    def _on_filter_changed(self):
        """Обработка изменения фильтра"""
        self.current_page = 0
        self.refresh()
    
    def _on_search(self):
        """Обработка поиска"""
        query = self.search_input.text().strip()
        
        if not query:
            self.refresh()
            return
        
        log.debug(f"Searching for: {query}")
        
        # Поиск в БД
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            self.matches = loop.run_until_complete(
                MatchRepository.search(query, limit=self.page_size)
            )
            
            self.total_matches = len(self.matches)
            self._update_table()
            self._update_stats()
            
            log.info(f"Found {len(self.matches)} matches")
            
        except Exception as e:
            log.error(f"Search failed: {e}")
            QMessageBox.critical(self, "Error", f"Search failed:\n{e}")
    
    def _on_row_double_clicked(self, row: int, column: int):
        """Обработка двойного клика на строку"""
        match_id = int(self.matches_table.item(row, 0).text())
        self.match_selected.emit(match_id)
        log.debug(f"Match {match_id} selected")
    
    def _on_delete_clicked(self, match_id: int):
        """Обработка удаления матча"""
        reply = QMessageBox.question(
            self,
            "Confirm Deletion",
            f"Are you sure you want to delete match #{match_id}?\nThis cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        log.info(f"Deleting match {match_id}")
        
        # Удаляем из БД
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            success = loop.run_until_complete(MatchRepository.delete(match_id))
            
            if success:
                QMessageBox.information(self, "Deleted", f"Match #{match_id} deleted successfully")
                self.match_deleted.emit(match_id)
                self.refresh()
            else:
                QMessageBox.warning(self, "Error", f"Failed to delete match #{match_id}")
        
        except Exception as e:
            log.error(f"Failed to delete match: {e}")
            QMessageBox.critical(self, "Error", f"Failed to delete match:\n{e}")