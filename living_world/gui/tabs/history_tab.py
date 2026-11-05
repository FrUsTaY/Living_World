from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                               QLineEdit, QComboBox, QTableWidget, QTableWidgetItem,
                               QHeaderView)
from PySide6.QtCore import Qt
from living_world.engine.observer.world_event import EventImportance, EventType

class HistoryTab(QWidget):
    """
    Вкладка 'История':
    Летопись ключевых исторических событий мира (рождения, браки, смерти,
    основание предприятий, важные социальные решения).
    """
    def __init__(self, simulation, main_window):
        super().__init__()
        self.simulation = simulation
        self.main_window = main_window

        self.layout = QVBoxLayout(self)

        # Панель фильтров
        top_layout = QHBoxLayout()

        self.cb_filter = QComboBox()
        self.cb_filter.addItems([
            "Все важные события",
            "Судьбоносные (CRITICAL)",
            "Значимые (HIGH)",
            "Демография (Рождения / Смерти)",
            "Семья и брак",
            "Экономика и карьера"
        ])
        self.cb_filter.currentIndexChanged.connect(self.update_data)

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Поиск по имени или ключевому слову...")
        self.search_edit.textChanged.connect(self.update_data)

        top_layout.addWidget(QLabel("Категория:"))
        top_layout.addWidget(self.cb_filter)
        top_layout.addWidget(QLabel("Поиск:"))
        top_layout.addWidget(self.search_edit)

        self.layout.addLayout(top_layout)

        # Таблица истории
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Время / Дата", "Важность", "Историческое событие"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)

        self.layout.addWidget(self.table)

    def update_data(self):
        journal = getattr(self.simulation, "event_journal", None)
        if not journal:
            return

        events = journal.get_all_events()

        filter_idx = self.cb_filter.currentIndex()
        query = self.search_edit.text().strip().lower()

        filtered_events = []
        for ev in reversed(events):
            # Фильтр по важности или типу
            if filter_idx == 1 and ev.importance != EventImportance.CRITICAL:
                continue
            elif filter_idx == 2 and ev.importance not in [EventImportance.CRITICAL, EventImportance.HIGH]:
                continue
            elif filter_idx == 3 and ev.event_type not in [EventType.BIRTH, EventType.DEATH, EventType.PREGNANCY]:
                continue
            elif filter_idx == 4 and ev.event_type not in [EventType.MARRIAGE, EventType.DIVORCE, EventType.FAMILY_CREATED, EventType.ROMANCE_START]:
                continue
            elif filter_idx == 5 and ev.event_type not in [EventType.JOB_CHANGE, getattr(EventType, 'ECONOMIC', None)]:
                continue

            # Поисковый запрос
            if query and query not in ev.message.lower():
                continue

            filtered_events.append(ev)

        self.table.setRowCount(len(filtered_events))

        importance_names = {
            EventImportance.CRITICAL: ("КРИТИЧЕСКОЕ", "#e74c3c"),
            EventImportance.HIGH: ("ВАЖНОЕ", "#e67e22"),
            EventImportance.MEDIUM: ("Обычное", "#3498db"),
            EventImportance.LOW: ("Мелкое", "#7f8c8d")
        }

        for row, ev in enumerate(filtered_events):
            # Время
            self.table.setItem(row, 0, QTableWidgetItem(ev.timestamp))

            # Важность
            imp_label, color = importance_names.get(ev.importance, ("—", "#000000"))
            imp_item = QTableWidgetItem(imp_label)
            self.table.setItem(row, 1, imp_item)

            # Сообщение
            msg_item = QTableWidgetItem(ev.message)
            self.table.setItem(row, 2, msg_item)
