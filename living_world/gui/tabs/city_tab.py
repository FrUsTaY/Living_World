from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                               QTableWidget, QTableWidgetItem, QHeaderView,
                               QComboBox, QGroupBox)
from PySide6.QtCore import Qt

class CityTab(QWidget):
    """
    Вкладка 'Город':
    Отображает районы, здания города, их типы, вместимость,
    население/сотрудников, привязанные предприятия и текущие строительные проекты.
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

        # Секция активного строительства
        self.lbl_construction = QLabel("Активные стройки: нет")
        self.lbl_construction.setStyleSheet("color: #d35400; font-weight: bold; padding: 4px;")
        self.layout.addWidget(self.lbl_construction)

        # Таблица зданий
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["Название", "Район", "Тип", "Вместимость", "Занято", "Предприятие / Баланс"])
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
        districts_cnt = len(city.districts)

        self.lbl_summary.setText(
            f"Районов: {districts_cnt} | Всего зданий: {len(all_buildings)} | Домов: {len(homes)} | Предприятий: {len(works)} | Общ. мест: {len(publics)}"
        )

        # Отображение текущего строительства
        cm = getattr(self.simulation, "construction_manager", None)
        if cm and cm.active_projects:
            active_info = []
            for p in cm.active_projects:
                d = city.get_district(p.district_id) if p.district_id else None
                d_name = d.name if d else "Город"
                active_info.append(f"🏗 {p.name} [{d_name}] — {p.progress:.1f}%")
            self.lbl_construction.setText("В процессе строительства: " + " | ".join(active_info))
        else:
            self.lbl_construction.setText("Активные стройки: нет новых проектов (город полностью обеспечен)")

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

            # Район
            d = city.get_district_for_building(b.id)
            d_name = d.name if d else "Центральный район"
            self.table.setItem(row, 1, QTableWidgetItem(d_name))

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
            self.table.setItem(row, 2, QTableWidgetItem(type_str))

            # Вместимость
            self.table.setItem(row, 3, QTableWidgetItem(str(b.capacity)))

            # Занято (жителями или работниками)
            if b.b_type == "home":
                occupants = sum(1 for n in self.simulation.npcs if n.is_alive and n.home_id == b.id)
                self.table.setItem(row, 4, QTableWidgetItem(f"{occupants} / {b.capacity} жителей"))
            elif b.b_type == "work":
                workers = sum(1 for n in self.simulation.npcs if n.is_alive and n.work_id == b.id)
                self.table.setItem(row, 4, QTableWidgetItem(f"{workers} работников"))
            else:
                visitors = sum(1 for n in self.simulation.npcs if n.is_alive and n.current_location == b.id)
                self.table.setItem(row, 4, QTableWidgetItem(f"{visitors} посетителей"))

            # Предприятие / Баланс
            ent_info = "—"
            if hasattr(self.simulation, "economy_manager"):
                ent = self.simulation.economy_manager.get_enterprise_for_building(b.id)
                if ent:
                    ent_info = f"{ent.name} ({ent.budget:.0f} ₽)"
            self.table.setItem(row, 5, QTableWidgetItem(ent_info))
