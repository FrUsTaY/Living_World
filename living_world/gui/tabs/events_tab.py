from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                               QListWidget, QComboBox, QCheckBox, QPushButton)
from PySide6.QtCore import Qt
from living_world.engine.observer.world_event import has_emoji

class EventsTab(QWidget):
    """
    Вкладка 'События':
    Детальный поток текущих событий мира с фильтрацией по категориям
    и управлением прокруткой.
    """
    def __init__(self, simulation, main_window):
        super().__init__()
        self.simulation = simulation
        self.main_window = main_window

        self.layout = QVBoxLayout(self)

        top_layout = QHBoxLayout()
        self.cb_filter = QComboBox()
        self.cb_filter.addItems(["Все события", "Только с участием людей", "Только экономика", "Только демография"])
        self.cb_filter.currentIndexChanged.connect(self.update_data)

        self.chk_autoscroll = QCheckBox("Автопрокрутка вниз")
        self.chk_autoscroll.setChecked(True)

        self.lbl_count = QLabel("Событий: 0")

        top_layout.addWidget(QLabel("Категория:"))
        top_layout.addWidget(self.cb_filter)
        top_layout.addSpacing(15)
        top_layout.addWidget(self.chk_autoscroll)
        top_layout.addStretch()
        top_layout.addWidget(self.lbl_count)

        self.layout.addLayout(top_layout)

        self.list_widget = QListWidget()
        self.layout.addWidget(self.list_widget)

    def update_data(self):
        events = getattr(self.simulation, "events_log", [])
        filter_idx = self.cb_filter.currentIndex()

        displayed = []
        for ev in reversed(events):
            msg = ev.get("msg", "")
            if not has_emoji(msg):
                continue
            if filter_idx == 1 and not any(mark in msg for mark in ["женился", "родил", "скончался", "познакомился", "встреч", "рабо"]):
                continue
            elif filter_idx == 2 and not any(mark in msg for mark in ["₽", "дивиденд", "зарплат", "магазин", "предприят", "кафе"]):
                continue
            elif filter_idx == 3 and not any(mark in msg for mark in ["родил", "скончался", "возраст", "брак", "свадьб"]):
                continue
            displayed.append(ev)
            if len(displayed) >= 200:
                break

        displayed.reverse()

        self.lbl_count.setText(f"Отображено: {len(displayed)} (всего: {len(events)})")

        self.list_widget.setUpdatesEnabled(False)
        try:
            self.list_widget.clear()
            for ev in displayed:
                time_str = ev.get("time", "")
                msg = ev.get("msg", "")
                self.list_widget.addItem(f"[{time_str}] {msg}")

            if self.chk_autoscroll.isChecked():
                self.list_widget.scrollToBottom()
        finally:
            self.list_widget.setUpdatesEnabled(True)
