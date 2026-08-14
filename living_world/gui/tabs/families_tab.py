from PySide6.QtWidgets import QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, QHeaderView, QLabel, QHBoxLayout

class FamiliesTab(QWidget):
    def __init__(self, simulation, parent=None):
        super().__init__(parent)
        self.simulation = simulation
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        # Stats layout
        stats_layout = QHBoxLayout()
        self.lbl_total = QLabel("Всего семей: 0")
        stats_layout.addWidget(self.lbl_total)
        stats_layout.addStretch()
        layout.addLayout(stats_layout)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["ID Семьи", "Дата основания", "Супруги", "Статус проживания"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)

        layout.addWidget(self.table)

    def update_data(self):
        all_families = getattr(self.simulation, 'families', [])
        families = [f for f in all_families if f.get('is_active', 1) == 1]

        self.lbl_total.setText(f"Всего активных семей: {len(families)}")

        self.table.setRowCount(len(families))

        for row, family in enumerate(families):
            # Find spouses
            spouses = [n for n in self.simulation.npcs if n.family_id == family['id']]
            spouse_names = ", ".join([n.get_full_name() for n in spouses])

            # Check living status
            living_status = "Раздельно"
            if len(spouses) == 2:
                if spouses[0].home_id == spouses[1].home_id:
                    living_status = "Вместе"

            self.table.setItem(row, 0, QTableWidgetItem(family['id'][:8] + "..."))
            self.table.setItem(row, 1, QTableWidgetItem(family['creation_time']))
            self.table.setItem(row, 2, QTableWidgetItem(spouse_names))
            self.table.setItem(row, 3, QTableWidgetItem(living_status))
