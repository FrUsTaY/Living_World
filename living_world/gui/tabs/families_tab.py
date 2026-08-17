from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                               QScrollArea, QFrame, QGridLayout)
from PySide6.QtCore import Qt
from living_world.engine.life_cycle_manager import LifeCycleManager

class FamilyWidget(QFrame):
    def __init__(self, family, sim):
        super().__init__()
        self.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        self.setLineWidth(2)

        self.family = family
        self.sim = sim
        self.layout = QVBoxLayout(self)

        # Получаем данные о семье (супруги, дети) - Биологическая семья
        spouses = [n for n in self.sim.npcs if n.family_id == family['id'] and n.is_alive]

        if not spouses:
            self.layout.addWidget(QLabel("Семья архивирована (нет живых супругов)"))
            return

        # Название семьи по первому супругу
        family_name = spouses[0].last_name
        title = QLabel(f"<b>Семья {family_name}</b>")
        title.setStyleSheet("font-size: 16px;")
        self.layout.addWidget(title)

        # Секция: Биологические / брачные связи
        bio_label = QLabel("<i>Биологические / брачные связи</i>")
        bio_label.setStyleSheet("color: gray;")
        self.layout.addWidget(bio_label)

        for sp in spouses:
            age = sp.get_age(self.sim.time.current_datetime)
            role = "Мать" if sp.gender == 'Ж' else "Отец"
            self.layout.addWidget(QLabel(f"• {sp.get_full_name()} ({role}, {age} лет)"))

        # Дети
        children = []
        if getattr(self.sim, 'family_manager', None):
            for sp in spouses:
                ch = self.sim.family_manager.get_children(sp.id)
                for c in ch:
                    if c not in children and c.is_alive:
                        children.append(c)

        for c in children:
            age = c.get_age(self.sim.time.current_datetime)
            role = "Дочь" if c.gender == 'Ж' else "Сын"
            self.layout.addWidget(QLabel(f"  └─ {c.get_full_name()} ({role}, {age} лет)"))

        self.layout.addWidget(QLabel("")) # Отступ

        # Секция: Домохозяйство
        hh_label = QLabel("<i>Домохозяйство</i>")
        hh_label.setStyleSheet("color: gray;")
        self.layout.addWidget(hh_label)

        # Определяем домохозяйство по первому супругу
        hh_id = spouses[0].household_id
        if hh_id and getattr(self.sim, 'household_manager', None):
            hh = self.sim.household_manager.get_household(hh_id)
            if hh:
                home_b = self.sim.city.get_building(hh.home_id) if getattr(self.sim, 'city', None) else None
                home_name = home_b.name if home_b else hh.home_id

                wealth = self.sim.household_manager.get_total_wealth(hh_id)

                self.layout.addWidget(QLabel(f"🏠 {home_name}"))
                self.layout.addWidget(QLabel(f"💰 Общий капитал: {wealth:.2f} ₽"))
                self.layout.addWidget(QLabel(f"⚠️ Стресс: {hh.stress:.1f}"))

                self.layout.addWidget(QLabel("Проживают:"))
                members = self.sim.household_manager.get_household_members(hh_id)
                for m in members:
                    if m.is_alive:
                        # Если это не член биологической семьи, помечаем как "сожитель"
                        role_str = ""
                        if m not in spouses and m not in children:
                            role_str = " (сожитель)"
                        self.layout.addWidget(QLabel(f"  • {m.get_full_name()}{role_str}"))
        else:
            self.layout.addWidget(QLabel("Нет общего домохозяйства"))


class FamiliesTab(QWidget):
    def __init__(self, simulation, main_window):
        super().__init__()
        self.simulation = simulation
        self.main_window = main_window

        self.layout = QVBoxLayout(self)

        stats_layout = QHBoxLayout()
        self.lbl_total = QLabel("Всего семей: 0")
        stats_layout.addWidget(self.lbl_total)
        stats_layout.addStretch()
        self.layout.addLayout(stats_layout)

        # Scroll Area for families
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll_content = QWidget()
        # Использование Grid Layout для размещения карточек по несколько в ряд
        self.grid_layout = QGridLayout(self.scroll_content)
        self.scroll.setWidget(self.scroll_content)

        self.layout.addWidget(self.scroll)

    def update_data(self):
        all_families = getattr(self.simulation, 'families', [])
        active_families = [f for f in all_families if f.get('is_active', 1) == 1]

        self.lbl_total.setText(f"Всего активных семей: {len(active_families)}")

        # Очистка старых карточек
        while self.grid_layout.count():
            child = self.grid_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        # Размещаем по 2-3 карточки в ряд (допустим, 3)
        cols = 3
        row = 0
        col = 0
        for family in active_families:
            widget = FamilyWidget(family, self.simulation)
            self.grid_layout.addWidget(widget, row, col)
            col += 1
            if col >= cols:
                col = 0
                row += 1

