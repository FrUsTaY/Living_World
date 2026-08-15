from PySide6.QtWidgets import (QWidget, QVBoxLayout, QLabel,
                               QTableWidget, QTableWidgetItem, QHeaderView)
from PySide6.QtCore import Qt

class PopulationTab(QWidget):
    def __init__(self, simulation, main_window):
        super().__init__()
        self.simulation = simulation
        self.main_window = main_window # Для вызова карточки NPC

        self.layout = QVBoxLayout(self)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Имя", "Возраст", "Профессия", "Статус"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.itemDoubleClicked.connect(self.on_item_double_clicked)

        self.layout.addWidget(self.table)

    def update_data(self):
        npcs = self.simulation.npcs
        self.table.setRowCount(len(npcs))

        for row, npc in enumerate(npcs):
            name_item = QTableWidgetItem(npc.get_full_name())
            # Сохраняем объект npc в item для карточки
            name_item.setData(Qt.UserRole, npc)

            age = npc.get_age(self.simulation.time.current_datetime)
            status = npc.state if npc.is_alive else "Умер"
            if not npc.is_alive:
                name_item.setForeground(Qt.gray)

            self.table.setItem(row, 0, name_item)

            age_item = QTableWidgetItem(f"{age} лет")
            if not npc.is_alive: age_item.setForeground(Qt.gray)
            self.table.setItem(row, 1, age_item)

            prof_item = QTableWidgetItem(npc.profession)
            if not npc.is_alive: prof_item.setForeground(Qt.gray)
            self.table.setItem(row, 2, prof_item)

            state_item = QTableWidgetItem(status)
            if not npc.is_alive: state_item.setForeground(Qt.gray)
            self.table.setItem(row, 3, state_item)

    def on_item_double_clicked(self, item):
        row = item.row()
        name_item = self.table.item(row, 0)
        npc = name_item.data(Qt.UserRole)
        if npc:
            self.main_window.show_npc_card(npc)
