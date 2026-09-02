from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                               QListWidget, QGroupBox, QFrame)
from PySide6.QtCore import Qt
from living_world.engine.observer.world_event import EventImportance

class WorldTab(QWidget):
    def __init__(self, simulation, main_window):
        super().__init__()
        self.simulation = simulation
        self.main_window = main_window

        self.layout = QHBoxLayout(self)

        # Левая колонка: Статистика и Активность
        self.left_layout = QVBoxLayout()

        self.stats_group = QGroupBox("Статистика города")
        self.stats_layout = QVBoxLayout(self.stats_group)
        self.lbl_stats = QLabel("Загрузка...")
        self.stats_layout.addWidget(self.lbl_stats)
        self.left_layout.addWidget(self.stats_group)

        self.activity_group = QGroupBox("Текущая активность")
        self.activity_layout = QVBoxLayout(self.activity_group)
        self.activity_list = QListWidget()
        self.activity_layout.addWidget(self.activity_list)
        self.left_layout.addWidget(self.activity_group)

        # Правая колонка: Значимые события (Event Feed)
        self.right_layout = QVBoxLayout()
        self.feed_group = QGroupBox("Свежие события (Event Feed)")
        self.feed_layout = QVBoxLayout(self.feed_group)
        self.feed_list = QListWidget()
        self.feed_layout.addWidget(self.feed_list)
        self.right_layout.addWidget(self.feed_group)

        self.layout.addLayout(self.left_layout, stretch=1)
        self.layout.addLayout(self.right_layout, stretch=2)

    def update_data(self):
        self._update_stats()
        self._update_activity()
        self._update_feed()

    def _update_stats(self):
        total = len(self.simulation.npcs)
        alive = sum(1 for n in self.simulation.npcs if n.is_alive)
        working = sum(1 for n in self.simulation.npcs if n.is_alive and n.state == "Работает")
        sleeping = sum(1 for n in self.simulation.npcs if n.is_alive and n.state == "Спит")
        free = alive - working - sleeping

        households = len(self.simulation.household_manager.households)

        stats_text = (
            f"Всего жителей: {total}\n"
            f"Живых: {alive}\n"
            f"Домохозяйств: {households}\n\n"
            f"Сейчас работают: {working}\n"
            f"Спят: {sleeping}\n"
            f"Свободны: {free}"
        )
        self.lbl_stats.setText(stats_text)

    def _update_activity(self):
        # Очистка и заполнение "Текущей активности"
        # Для простоты выводим состояния всех активных не-спящих/не-работающих, либо агрегируем.
        self.activity_list.clear()

        activities = []
        for n in self.simulation.npcs:
            if n.is_alive and n.state not in ["Спит", "Работает"]:
                activities.append(f"{n.get_full_name()}: {n.state}")

        if not activities:
            self.activity_list.addItem("В городе сейчас спокойно...")
        else:
            for act in activities[:30]: # Показываем до 30 активностей
                self.activity_list.addItem(act)

    def _update_feed(self):
        self.feed_list.clear()
        # Извлекаем события MEDIUM и выше
        important_events = self.simulation.event_journal.get_events_by_importance(
            [EventImportance.MEDIUM, EventImportance.HIGH, EventImportance.CRITICAL]
        )

        # Показываем последние 50
        for ev in reversed(important_events[-50:]):
            marker = ""
            if ev.importance == EventImportance.CRITICAL:
                marker = "🔴 [СУДЬБОНОСНО] "
            elif ev.importance == EventImportance.HIGH:
                marker = "🟡 [ВАЖНО] "

            self.feed_list.addItem(f"{marker}[{ev.timestamp}] {ev.message}")
