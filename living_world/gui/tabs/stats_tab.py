from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                               QGroupBox, QGridLayout, QScrollArea, QFrame)
from PySide6.QtCore import Qt
from living_world.engine.life_cycle_manager import LifeStage

class StatsTab(QWidget):
    """
    Вкладка 'Статистика':
    Подробная сводная аналитика по демографии, семьям, экономике и городской инфраструктуре.
    """
    def __init__(self, simulation, main_window):
        super().__init__()
        self.simulation = simulation
        self.main_window = main_window

        main_layout = QVBoxLayout(self)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        self.grid = QGridLayout(container)

        # 1. Демография
        self.demo_group = QGroupBox("Демография и население")
        demo_layout = QVBoxLayout(self.demo_group)
        self.lbl_demo = QLabel("Загрузка...")
        self.lbl_demo.setStyleSheet("font-size: 13px; line-height: 1.4;")
        demo_layout.addWidget(self.lbl_demo)
        self.grid.addWidget(self.demo_group, 0, 0)

        # 2. Семьи и домохозяйства
        self.family_group = QGroupBox("Семьи и общество")
        family_layout = QVBoxLayout(self.family_group)
        self.lbl_family = QLabel("Загрузка...")
        self.lbl_family.setStyleSheet("font-size: 13px; line-height: 1.4;")
        family_layout.addWidget(self.lbl_family)
        self.grid.addWidget(self.family_group, 0, 1)

        # 3. Экономика и финансы
        self.econ_group = QGroupBox("Экономика и благосостояние")
        econ_layout = QVBoxLayout(self.econ_group)
        self.lbl_econ = QLabel("Загрузка...")
        self.lbl_econ.setStyleSheet("font-size: 13px; line-height: 1.4;")
        econ_layout.addWidget(self.lbl_econ)
        self.grid.addWidget(self.econ_group, 1, 0)

        # 4. Инфраструктура города
        self.infra_group = QGroupBox("Городская инфраструктура")
        infra_layout = QVBoxLayout(self.infra_group)
        self.lbl_infra = QLabel("Загрузка...")
        self.lbl_infra.setStyleSheet("font-size: 13px; line-height: 1.4;")
        infra_layout.addWidget(self.lbl_infra)
        self.grid.addWidget(self.infra_group, 1, 1)

        scroll.setWidget(container)
        main_layout.addWidget(scroll)

    def update_data(self):
        npcs = self.simulation.npcs
        alive_npcs = [n for n in npcs if n.is_alive]
        cur_date = self.simulation.time.current_datetime

        # 1. Демография
        total = len(npcs)
        alive = len(alive_npcs)
        dead = total - alive
        men = sum(1 for n in alive_npcs if n.gender == "М")
        women = sum(1 for n in alive_npcs if n.gender == "Ж")

        babies = sum(1 for n in alive_npcs if n.get_life_stage(cur_date) == LifeStage.BABY)
        children = sum(1 for n in alive_npcs if n.get_life_stage(cur_date) == LifeStage.CHILD)
        teens = sum(1 for n in alive_npcs if n.get_life_stage(cur_date) == LifeStage.TEEN)
        adults = sum(1 for n in alive_npcs if n.get_life_stage(cur_date) in [LifeStage.YOUNG_ADULT, LifeStage.ADULT])
        elders = sum(1 for n in alive_npcs if n.get_life_stage(cur_date) == LifeStage.ELDER)

        avg_age = (sum(n.get_age(cur_date) for n in alive_npcs) / alive) if alive > 0 else 0.0

        self.lbl_demo.setText(
            f"<b>Всего за историю:</b> {total}<br>"
            f"<b>Живых жителей:</b> {alive} (М: {men}, Ж: {women})<br>"
            f"<b>Умерших:</b> {dead}<br>"
            f"<b>Средний возраст:</b> {avg_age:.1f} лет<br><br>"
            f"<b>Возрастной состав:</b><br>"
            f"• Младенцы (0-2): {babies}<br>"
            f"• Дети (3-12): {children}<br>"
            f"• Подростки (13-17): {teens}<br>"
            f"• Взрослые (18-59): {adults}<br>"
            f"• Пожилые (60+): {elders}"
        )

        # 2. Семьи
        families_cnt = len(getattr(self.simulation, "families", []))
        households_cnt = len(self.simulation.household_manager.households) if hasattr(self.simulation, "household_manager") else 0
        dating_cnt = sum(1 for n in alive_npcs if getattr(n, 'dating_partner_id', None) is not None) // 2

        self.lbl_family.setText(
            f"<b>Официальных семей:</b> {families_cnt}<br>"
            f"<b>Домохозяйств (домов):</b> {households_cnt}<br>"
            f"<b>Пары в отношениях:</b> {dating_cnt}<br>"
            f"<b>Одинокие жители:</b> {alive - dating_cnt * 2}<br><br>"
            f"<b>Социальный климат:</b><br>"
            f"• Среднее настроение: {sum(n.mood for n in alive_npcs) / alive if alive else 0:.1f}%<br>"
            f"• Средняя энергия: {sum(n.energy for n in alive_npcs) / alive if alive else 0:.1f}%<br>"
            f"• Средняя сытость: {sum(n.hunger for n in alive_npcs) / alive if alive else 0:.1f}%"
        )

        # 3. Экономика
        total_wealth = sum(n.money for n in alive_npcs)
        avg_wealth = total_wealth / alive if alive else 0.0
        econ_mgr = getattr(self.simulation, "economy_manager", None)
        total_biz = sum(e.budget for e in econ_mgr.enterprises.values()) if econ_mgr else 0.0
        active_enterprises = sum(1 for e in econ_mgr.enterprises.values() if e.is_active) if econ_mgr else 0

        richest = sorted(alive_npcs, key=lambda n: n.money, reverse=True)[:3]
        richest_str = ", ".join([f"{n.get_full_name()} ({n.money:.0f} ₽)" for n in richest]) if richest else "Нет"

        self.lbl_econ.setText(
            f"<b>Общий капитал жителей:</b> {total_wealth:,.0f} ₽<br>"
            f"<b>Среднее богатство жителя:</b> {avg_wealth:,.0f} ₽<br>"
            f"<b>Капитал предприятий:</b> {total_biz:,.0f} ₽<br>"
            f"<b>Действующих предприятий:</b> {active_enterprises}<br><br>"
            f"<b>Самые состоятельные жители:</b><br>"
            f"{richest_str}"
        )

        # 4. Инфраструктура
        city = self.simulation.city
        total_homes = len(city.get_homes())
        total_works = len(city.get_workplaces())
        home_capacity = sum(h.capacity for h in city.get_homes())
        occupied_slots = sum(1 for n in alive_npcs if n.home_id)

        self.lbl_infra.setText(
            f"<b>Жилых домов:</b> {total_homes}<br>"
            f"<b>Вместимость жилья:</b> {home_capacity} мест<br>"
            f"<b>Занято жилья:</b> {occupied_slots} ({occupied_slots / home_capacity * 100 if home_capacity else 0:.1f}%)<br>"
            f"<b>Рабочих площадок:</b> {total_works}<br>"
            f"<b>Общественных зон:</b> {len(city.get_public_places())}"
        )
