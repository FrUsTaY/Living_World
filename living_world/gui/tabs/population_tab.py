from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                               QLineEdit, QTableWidget, QTableWidgetItem, QHeaderView)
from PySide6.QtCore import Qt

class PopulationTab(QWidget):
    """
    Вкладка 'Жители':
    Таблица жителей с подробной информацией (имя, возраст, профессия, район,
    капитал, настроение, текущий статус) и поиском.
    """
    def __init__(self, simulation, main_window):
        super().__init__()
        self.simulation = simulation
        self.main_window = main_window

        self.layout = QVBoxLayout(self)

        top_layout = QHBoxLayout()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Поиск жителей по имени или профессии...")
        self.search_edit.textChanged.connect(self.update_data)

        self.lbl_count = QLabel("Жителей: 0")
        self.lbl_count.setStyleSheet("font-weight: bold;")

        top_layout.addWidget(QLabel("Поиск:"))
        top_layout.addWidget(self.search_edit)
        top_layout.addSpacing(20)
        top_layout.addWidget(self.lbl_count)

        self.layout.addLayout(top_layout)

        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "Имя", "Возраст", "Профессия", "Район", "Деньги", "Здоровье", "Настроение", "Статус"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.itemDoubleClicked.connect(self.on_item_double_clicked)

        self.layout.addWidget(self.table)

    def update_data(self):
        npcs = self.simulation.npcs
        query = self.search_edit.text().strip().lower()
        city = getattr(self.simulation, "city", None)
        cur_date = self.simulation.time.current_datetime

        filtered = []
        for npc in npcs:
            if query:
                full_name = npc.get_full_name().lower()
                prof = npc.profession.lower()
                if query not in full_name and query not in prof:
                    continue
            filtered.append(npc)

        alive_cnt = sum(1 for n in filtered if n.is_alive)
        self.lbl_count.setText(f"Жителей: {len(filtered)} (живых: {alive_cnt})")

        self.table.setRowCount(len(filtered))

        for row, npc in enumerate(filtered):
            # 0. Имя
            name_item = QTableWidgetItem(npc.get_full_name())
            name_item.setData(Qt.UserRole, npc)
            if not npc.is_alive:
                name_item.setForeground(Qt.gray)
            self.table.setItem(row, 0, name_item)

            # 1. Возраст
            age = npc.get_age(cur_date)
            age_item = QTableWidgetItem(f"{age} лет")
            if not npc.is_alive:
                age_item.setForeground(Qt.gray)
            self.table.setItem(row, 1, age_item)

            # 2. Профессия
            prof_item = QTableWidgetItem(npc.profession)
            if not npc.is_alive:
                prof_item.setForeground(Qt.gray)
            self.table.setItem(row, 2, prof_item)

            # 3. Район
            d = city.get_district_for_building(npc.home_id) if city else None
            district_name = d.name if d else "Центральный район"
            dist_item = QTableWidgetItem(district_name)
            if not npc.is_alive:
                dist_item.setForeground(Qt.gray)
            self.table.setItem(row, 3, dist_item)

            # 4. Деньги
            money_item = QTableWidgetItem(f"{npc.money:,.0f} ₽")
            if not npc.is_alive:
                money_item.setForeground(Qt.gray)
            self.table.setItem(row, 4, money_item)

            # 5. Здоровье
            health_val = getattr(npc, 'health', 100.0)
            health_str = f"{int(health_val)}%" if npc.is_alive else "—"
            health_item = QTableWidgetItem(health_str)
            if not npc.is_alive:
                health_item.setForeground(Qt.gray)
            self.table.setItem(row, 5, health_item)

            # 6. Настроение
            mood_str = f"{int(npc.mood)}%" if npc.is_alive else "—"
            mood_item = QTableWidgetItem(mood_str)
            if not npc.is_alive:
                mood_item.setForeground(Qt.gray)
            self.table.setItem(row, 6, mood_item)

            # 7. Статус
            status = npc.state if npc.is_alive else "Умер"
            state_item = QTableWidgetItem(status)
            if not npc.is_alive:
                state_item.setForeground(Qt.gray)
            self.table.setItem(row, 7, state_item)

    def on_item_double_clicked(self, item):
        row = item.row()
        name_item = self.table.item(row, 0)
        npc = name_item.data(Qt.UserRole)
        if npc and self.main_window:
            self.main_window.show_npc_card(npc)
