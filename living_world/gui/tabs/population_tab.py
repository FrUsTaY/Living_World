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
        self.table.setHorizontalHeaderLabels(["Имя", "Возраст", "Профессия", "Состояние"])
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

            self.table.setItem(row, 0, name_item)
            self.table.setItem(row, 1, QTableWidgetItem(str(npc.age)))
            self.table.setItem(row, 2, QTableWidgetItem(npc.profession))
            self.table.setItem(row, 3, QTableWidgetItem(npc.state))

    def on_item_double_clicked(self, item):
        row = item.row()
        name_item = self.table.item(row, 0)
        npc = name_item.data(Qt.UserRole)
        if npc:
            self.main_window.show_npc_card(npc)
