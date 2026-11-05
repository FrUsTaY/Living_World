from PySide6.QtWidgets import (QMainWindow, QDialog, QWidget, QVBoxLayout, QHBoxLayout,
                               QPushButton, QLabel, QTabWidget, QListWidget, QMessageBox,
                               QToolBar, QComboBox)
from PySide6.QtCore import QTimer, Qt

from living_world.engine.simulation import Simulation
from living_world.population.generation import generate_initial_world
from living_world.gui.tabs.population_tab import PopulationTab
from living_world.gui.tabs.families_tab import FamiliesTab
from living_world.gui.tabs.world_tab import WorldTab
from living_world.gui.tabs.city_tab import CityTab
from living_world.gui.tabs.stats_tab import StatsTab
from living_world.gui.tabs.history_tab import HistoryTab
from living_world.gui.tabs.events_tab import EventsTab
from living_world.gui.tabs.settings_tab import SettingsTab
from living_world.gui.dialogs.npc_card import NPCCardDialog
from living_world.gui.dialogs.load_world import LoadWorldDialog
from living_world.database.repository import Database
from PySide6.QtWidgets import QInputDialog
import os

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Живой Мир (Living World) v0.1")
        self.resize(1000, 700)

        self.sim = Simulation()
        self.saves_dir = "saves"
        if not os.path.exists(self.saves_dir):
            os.makedirs(self.saves_dir)

        self._init_ui()

        self.timer = QTimer()
        self.timer.timeout.connect(self._on_tick)

        self.timer_interval = 1000
        self.ticks_per_update = 1
        self.timer.start(self.timer_interval)

        self.change_speed()

    def _init_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)

        top_layout = QHBoxLayout()
        self.lbl_time = QLabel("День 1 · 08:00")
        self.lbl_time.setStyleSheet("font-weight: bold; font-size: 16px;")

        self.btn_play_pause = QPushButton("▶ Запустить")
        self.btn_play_pause.clicked.connect(self.toggle_pause)

        self.cb_speed = QComboBox()
        self.cb_speed.addItems(["1x", "10x", "100x", "1000x"])
        self.cb_speed.currentIndexChanged.connect(self.change_speed)

        btn_save = QPushButton("Сохранить")
        btn_save.clicked.connect(self.save_world)
        btn_load = QPushButton("Загрузить")
        btn_load.clicked.connect(self.load_world)
        btn_new = QPushButton("Новый мир")
        btn_new.clicked.connect(self.new_world)

        top_layout.addWidget(self.lbl_time)
        top_layout.addStretch()
        top_layout.addWidget(self.btn_play_pause)
        top_layout.addWidget(QLabel("Скорость:"))
        top_layout.addWidget(self.cb_speed)
        top_layout.addWidget(btn_save)
        top_layout.addWidget(btn_load)
        top_layout.addWidget(btn_new)

        main_layout.addLayout(top_layout)

        self.tabs = QTabWidget()

        self.world_tab = WorldTab(self.sim, self)
        self.pop_tab = PopulationTab(self.sim, self)
        self.fam_tab = FamiliesTab(self.sim, self)
        self.city_tab = CityTab(self.sim, self)
        self.stats_tab = StatsTab(self.sim, self)
        self.history_tab = HistoryTab(self.sim, self)
        self.events_tab = EventsTab(self.sim, self)
        self.settings_tab = SettingsTab(self.sim, self)

        self.tabs.addTab(self.world_tab, "Мир")
        self.tabs.addTab(self.pop_tab, "Жители")
        self.tabs.addTab(self.fam_tab, "Семьи")
        self.tabs.addTab(self.city_tab, "Город")
        self.tabs.addTab(self.stats_tab, "Статистика")
        self.tabs.addTab(self.history_tab, "История")
        self.tabs.addTab(self.events_tab, "События")
        self.tabs.addTab(self.settings_tab, "Настройки")
        self.tabs.currentChanged.connect(self._on_tab_changed)

        main_layout.addWidget(self.tabs, stretch=3)

        main_layout.addWidget(QLabel("Журнал событий (технический лог):"))
        self.log_list = QListWidget()
        # Для UI сделаем лог поменьше, чтобы акцент был на вкладку "Мир"
        main_layout.addWidget(self.log_list, stretch=1)

    def toggle_pause(self):
        self.sim.time.paused = not self.sim.time.paused
        if self.sim.time.paused:
            self.btn_play_pause.setText("▶ Запустить")
        else:
            self.btn_play_pause.setText("Ⅱ Пауза")

    def change_speed(self):
        speed_str = self.cb_speed.currentText()
        if speed_str == "1x":
            self.timer_interval = 1000
            self.ticks_per_update = 1
        elif speed_str == "10x":
            self.timer_interval = 100
            self.ticks_per_update = 1
        elif speed_str == "100x":
            self.timer_interval = 10
            self.ticks_per_update = 1
        elif speed_str == "1000x":
            self.timer_interval = 10
            self.ticks_per_update = 10

        self.timer.setInterval(self.timer_interval)

    def _on_tick(self):
        if not self.sim.time.paused:
            for _ in range(self.ticks_per_update):
                self.sim.update()

            self.lbl_time.setText(self.sim.time.format_time())

            current_tab = self.tabs.currentWidget()
            if hasattr(current_tab, 'update_data'):
                current_tab.update_data()

            self.update_log()

    def _on_tab_changed(self, index):
        widget = self.tabs.widget(index)
        if hasattr(widget, 'update_data'):
            widget.update_data()

    def update_log(self):
        self.log_list.clear()
        display_events = self.sim.events_log[-200:]
        for ev in display_events:
            self.log_list.addItem(f"[{ev['time']}] {ev['msg']}")
        self.log_list.scrollToBottom()

    def show_npc_card(self, npc):
        dialog = NPCCardDialog(npc, self.sim.city, self)
        dialog.exec()

    def new_world(self):
        self.sim.close()
        self.sim = Simulation()
        for tab in [self.world_tab, self.pop_tab, self.fam_tab, self.city_tab, self.stats_tab, self.history_tab, self.events_tab, self.settings_tab]:
            tab.simulation = self.sim

        generate_initial_world(self.sim.city, self.sim, 25)

        for tab in [self.world_tab, self.pop_tab, self.fam_tab, self.city_tab, self.stats_tab, self.history_tab, self.events_tab, self.settings_tab]:
            if hasattr(tab, 'update_data'):
                tab.update_data()

        self.update_log()
        self.lbl_time.setText(self.sim.time.format_time())
        QMessageBox.information(self, "Новый мир", "Мир успешно создан!")

    def save_world(self):
        name, ok = QInputDialog.getText(self, "Сохранение мира", "Введите имя сохранения:")
        if ok and name:
            file_path = os.path.join(self.saves_dir, name + ".db")
            try:
                self.sim.save_to_file(file_path)
                QMessageBox.information(self, "Сохранение", f"Мир успешно сохранен: {name}")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Ошибка сохранения: {e}")

    def load_world(self):
        dialog = LoadWorldDialog(self.saves_dir, self)
        if dialog.exec() == QDialog.Accepted and dialog.selected_file:
            db = Database(dialog.selected_file)
            try:
                load_res = db.load_world()
                city_treasury = 100000.0
                if len(load_res) >= 15:
                    time_dict, b_dicts, npc_dicts, events, families, relationships, memories, edu_inst_dicts, edu_prog_dicts, edu_hist_dicts, pregnancies_dicts, households_dicts, world_events_dicts, enterprises_dicts, city_treasury = load_res[:15]
                elif len(load_res) == 14:
                    time_dict, b_dicts, npc_dicts, events, families, relationships, memories, edu_inst_dicts, edu_prog_dicts, edu_hist_dicts, pregnancies_dicts, households_dicts, world_events_dicts, enterprises_dicts = load_res
                elif len(load_res) == 13:
                    time_dict, b_dicts, npc_dicts, events, families, relationships, memories, edu_inst_dicts, edu_prog_dicts, edu_hist_dicts, pregnancies_dicts, households_dicts, world_events_dicts = load_res
                    enterprises_dicts = []
                else:
                    # Обратная совместимость
                    time_dict, b_dicts, npc_dicts, events, families, relationships, memories, edu_inst_dicts, edu_prog_dicts, edu_hist_dicts, pregnancies_dicts, households_dicts = load_res[:12]
                    world_events_dicts = []
                    enterprises_dicts = []

                if not time_dict:
                    QMessageBox.warning(self, "Загрузка", "В файле нет сохраненного мира.")
                    return

                self.sim.close()
                self.sim = Simulation()
                self.sim.time.set_time_from_dict(time_dict)
                if hasattr(self.sim, 'economy_manager'):
                    self.sim.economy_manager.city_treasury = float(city_treasury)

                from living_world.city.city import Building
                for b in b_dicts:
                    self.sim.city.add_building(Building(b['name'], b['type'], b['capacity'], b['id']))

                # Recreate households
                if hasattr(self.sim, 'household_manager') and households_dicts:
                    from living_world.engine.social.household import Household
                    for hh_dict in households_dicts:
                        hh = Household.from_dict(hh_dict)
                        self.sim.household_manager.add_household(hh)

                from living_world.population.npc import NPC
                from datetime import datetime
                for nd in npc_dicts:
                    dob = None
                    if nd.get('date_of_birth'):
                        try:
                            dob = datetime.fromisoformat(nd['date_of_birth'])
                        except:
                            pass

                    if not dob:
                        # Fallback for very old saves that somehow bypassed migration
                        dob = self.sim.time.current_datetime

                    npc = NPC(nd['first_name'], nd['last_name'], dob, nd['gender'], nd['profession'], nd['home_id'], nd['work_id'], nd['id'],
                              mother_id=nd.get('mother_id'), father_id=nd.get('father_id'), children_desire=nd.get('children_desire'))

                    if nd.get('date_of_death'):
                        try:
                            npc.date_of_death = datetime.fromisoformat(nd['date_of_death'])
                        except:
                            pass

                    npc.is_alive = bool(nd.get('is_alive', 1))

                    npc.current_education_id = nd.get('current_education_id')
                    npc.education_status = nd.get('education_status')

                    npc.household_id = nd.get('household_id')
                    npc.dating_partner_id = nd.get('dating_partner_id')

                    npc.money = nd['money']
                    npc.hunger = nd['hunger']
                    npc.energy = nd['energy']
                    npc.mood = nd['mood']
                    npc.health = float(nd.get('health', 100.0))
                    npc.hygiene = float(nd.get('hygiene', 100.0))
                    npc.stress = float(nd.get('stress', 0.0))
                    npc.hobby = nd.get('hobby') or (random.choice(NPC.HOBBIES) if hasattr(NPC, 'HOBBIES') else 'Чтение')
                    npc.chronotype = nd.get('chronotype') or random.choice(['lark', 'owl'])
                    npc.is_sick = bool(nd.get('is_sick', 0))
                    npc.sick_days = int(nd.get('sick_days', 0))
                    npc.alimony_to_id = nd.get('alimony_to_id')
                    npc.career_level = int(nd.get('career_level', 1))
                    npc.work_experience_days = int(nd.get('work_experience_days', 0))
                    npc.is_renting = bool(nd.get('is_renting', 0))
                    npc.mortgage_debt = float(nd.get('mortgage_debt', 0.0))
                    npc.mortgage_payment = float(nd.get('mortgage_payment', 0.0))
                    npc.current_location = nd['current_location']
                    npc.state = nd['state']
                    npc._last_state = nd['state']
                    npc.family_id = nd.get('family_id')

                    npc.traits = {
                        'sociability': nd.get('trait_sociability', 0.0),
                        'friendliness': nd.get('trait_friendliness', 0.0),
                        'conflict': nd.get('trait_conflict', 0.0),
                        'empathy': nd.get('trait_empathy', 0.0),
                        'boldness': nd.get('trait_boldness', 0.0),
                        'patience': nd.get('trait_patience', 0.0),
                        'ambition': nd.get('trait_ambition', 0.0),
                        'frugality': nd.get('trait_frugality', 0.0),
                        'diligence': nd.get('trait_diligence', 0.0)
                    }

                    self.sim.add_npc(npc)

                self.sim.events_log = events[-200:] if len(events) > 200 else events
                self.sim.full_history = events

                from living_world.engine.education.models import EducationalInstitution, EducationProgram, EducationHistoryRecord
                if hasattr(self.sim, 'education_manager'):
                    for d in edu_inst_dicts:
                        self.sim.education_manager.add_institution(EducationalInstitution.from_dict(d))
                    for d in edu_prog_dicts:
                        self.sim.education_manager.add_program(EducationProgram.from_dict(d))
                    for d in edu_hist_dicts:
                        self.sim.education_manager.history.append(EducationHistoryRecord(
                            npc_id=d['npc_id'], institution_id=d['institution_id'],
                            program_id=d['program_id'], start_date=d['start_date'],
                            status=d['status'], end_date=d.get('end_date'),
                            qualification=d.get('qualification'), id=d['id']
                        ))

                if hasattr(self.sim, 'reproduction_manager') and pregnancies_dicts:
                    self.sim.reproduction_manager.load_pregnancies(pregnancies_dicts)

                # Загружаем социальные данные
                self.sim.relationship_manager.load_relationships(relationships)
                self.sim.memory_manager.load_memories(memories)
                self.sim.families = families
                self.sim.event_journal.load_from_dicts(world_events_dicts)

                if hasattr(self.sim, 'economy_manager') and enterprises_dicts:
                    from living_world.engine.economy.enterprise import Enterprise
                    for ed in enterprises_dicts:
                        ent = Enterprise(
                            name=ed['name'],
                            enterprise_type=ed['type'],
                            building_id=ed['building_id'],
                            owner_id=ed.get('owner_id'),
                            budget=ed.get('budget', 50000.0),
                            wage_rate=ed.get('wage_rate', 250.0),
                            enterprise_id=ed['id'],
                            is_active=bool(ed.get('is_active', 1)),
                            raw_materials=float(ed.get('raw_materials', 20.0)),
                            finished_goods=float(ed.get('finished_goods', 20.0))
                        )
                        self.sim.economy_manager.register_enterprise(ent)

                    for n in self.sim.npcs:
                        if n.is_alive and n.work_id:
                            w_ent = self.sim.economy_manager.get_enterprise_for_building(n.work_id)
                            if w_ent:
                                w_ent.add_employee(n.id)

                for tab in [self.world_tab, self.pop_tab, self.fam_tab, self.city_tab, self.stats_tab, self.history_tab, self.events_tab, self.settings_tab]:
                    tab.simulation = self.sim
                    if hasattr(tab, 'update_data'):
                        tab.update_data()

                self.lbl_time.setText(self.sim.time.format_time())
                self.update_log()

                QMessageBox.information(self, "Загрузка", "Мир успешно загружен!")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Ошибка загрузки: {e}")
