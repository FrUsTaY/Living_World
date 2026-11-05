from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                               QTableWidget, QTableWidgetItem, QHeaderView,
                               QComboBox, QGroupBox)
from PySide6.QtCore import Qt

class CityTab(QWidget):
    """
    Вкладка 'Город':
    Отображает список всех зданий города, их типы, вместимость,
    население/сотрудников и привязанные предприятия.
    """
    def __init__(self, simulation, main_window):
        super().__init__()
        self.simulation = simulation
        self.main_window = main_window

        self.layout = QVBoxLayout(self)

        # Верхняя панель фильтров и статистики
        top_bar = QHBoxLayout()
        self.cb_filter = QComboBox()
        self.cb_filter.addItems(["Все здания", "Жилые дома", "Предприятия и работа", "Общественные места"])
        self.cb_filter.currentIndexChanged.connect(self.update_data)

        self.lbl_summary = QLabel()
        self.lbl_summary.setStyleSheet("font-weight: bold;")

        top_bar.addWidget(QLabel("Фильтр:"))
        top_bar.addWidget(self.cb_filter)
        top_bar.addSpacing(20)
        top_bar.addWidget(self.lbl_summary)
        top_bar.addStretch()

        self.layout.addLayout(top_bar)

        # Таблица зданий
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Название", "Тип", "Вместимость", "Занято", "Предприятие / Баланс"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)

        self.layout.addWidget(self.table)

    def update_data(self):
        city = self.simulation.city
        all_buildings = city.buildings

        # Подсчет статистики
        homes = city.get_homes()
        works = city.get_workplaces()
        publics = city.get_public_places()

        self.lbl_summary.setText(
            f"Всего зданий: {len(all_buildings)} | Домов: {len(homes)} | Предприятий: {len(works)} | Общ. мест: {len(publics)}"
        )

        filter_idx = self.cb_filter.currentIndex()
        if filter_idx == 1:
            filtered = homes
        elif filter_idx == 2:
            filtered = works
        elif filter_idx == 3:
            filtered = publics
        else:
            filtered = all_buildings

        self.table.setRowCount(len(filtered))

        for row, b in enumerate(filtered):
            # Название
            self.table.setItem(row, 0, QTableWidgetItem(b.name))

            # Тип
            type_names = {
                "home": "Жилой дом",
                "work": "Предприятие",
                "park": "Парк",
                "cafe": "Кафе",
                "shop": "Магазин",
                "public": "Общественное"
            }
            type_str = type_names.get(b.b_type, b.b_type)
            self.table.setItem(row, 1, QTableWidgetItem(type_str))

            # Вместимость
            self.table.setItem(row, 2, QTableWidgetItem(str(b.capacity)))

            # Занято (жителями или работниками)
            if b.b_type == "home":
                occupants = sum(1 for n in self.simulation.npcs if n.is_alive and n.home_id == b.id)
                self.table.setItem(row, 3, QTableWidgetItem(f"{occupants} / {b.capacity} жителей"))
            elif b.b_type == "work":
                workers = sum(1 for n in self.simulation.npcs if n.is_alive and n.work_id == b.id)
                self.table.setItem(row, 3, QTableWidgetItem(f"{workers} работников"))
            else:
                visitors = sum(1 for n in self.simulation.npcs if n.is_alive and n.current_location == b.id)
                self.table.setItem(row, 3, QTableWidgetItem(f"{visitors} посетителей"))

            # Предприятие / Баланс
            ent_info = "—"
            if hasattr(self.simulation, "economy_manager"):
                ent = self.simulation.economy_manager.get_enterprise_for_building(b.id)
                if ent:
                    ent_info = f"{ent.name} ({ent.budget:.0f} ₽)"
            self.table.setItem(row, 4, QTableWidgetItem(ent_info))
