from PySide6.QtWidgets import (QMainWindow, QDialog, QWidget, QVBoxLayout, QHBoxLayout,
                               QPushButton, QLabel, QTabWidget, QListWidget, QMessageBox,
                               QToolBar, QComboBox)
from PySide6.QtCore import QTimer, Qt

from living_world.engine.simulation import Simulation
from living_world.population.generation import generate_initial_world
from living_world.gui.tabs.population_tab import PopulationTab
from living_world.gui.tabs.families_tab import FamiliesTab
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

        self.map_tab = QWidget()
        self.map_layout = QVBoxLayout(self.map_tab)
        self.map_layout.addWidget(QLabel("Карта города (в разработке)"))

        self.pop_tab = PopulationTab(self.sim, self)

        self.tabs.addTab(self.map_tab, "Мир")
        self.tabs.addTab(self.pop_tab, "Жители")
        self.fam_tab = FamiliesTab(self.sim, self)
        self.tabs.addTab(self.fam_tab, "Семьи")

        main_layout.addWidget(self.tabs, stretch=3)

        main_layout.addWidget(QLabel("Журнал событий:"))
        self.log_list = QListWidget()
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

            if self.tabs.currentIndex() == 1:
                self.pop_tab.update_data()
            elif self.tabs.currentIndex() == 2:
                self.fam_tab.update_data()

            self.update_log()

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
        self.sim = Simulation()
        self.pop_tab.simulation = self.sim
        self.fam_tab.simulation = self.sim
        generate_initial_world(self.sim.city, self.sim, 25)
        self.pop_tab.update_data()
        self.update_log()
        self.lbl_time.setText(self.sim.time.format_time())
        QMessageBox.information(self, "Новый мир", "Мир успешно создан!")

    def save_world(self):
        name, ok = QInputDialog.getText(self, "Сохранение мира", "Введите имя сохранения:")
        if ok and name:
            file_path = os.path.join(self.saves_dir, name + ".db")
            db = Database(file_path)
            try:
                edu_inst = getattr(self.sim, 'education_manager', None)
                db.save_world(
                    self.sim.time.get_time_dict(),
                    self.sim.npcs,
                    self.sim.city.buildings,
                    self.sim.full_history,
                    getattr(self.sim, 'families', []),
                    self.sim.relationship_manager.get_all_relationships(),
                    self.sim.memory_manager.get_all_memories(),
                    list(edu_inst.institutions.values()) if edu_inst else [],
                    list(edu_inst.programs.values()) if edu_inst else [],
                    [r.to_dict() for r in getattr(edu_inst, 'history', [])] if edu_inst else [],
                    getattr(self.sim, 'reproduction_manager', None).active_pregnancies if hasattr(self.sim, 'reproduction_manager') else []
                )
                QMessageBox.information(self, "Сохранение", f"Мир успешно сохранен: {name}")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Ошибка сохранения: {e}")

    def load_world(self):
        dialog = LoadWorldDialog(self.saves_dir, self)
        if dialog.exec() == QDialog.Accepted and dialog.selected_file:
            db = Database(dialog.selected_file)
            try:
                time_dict, b_dicts, npc_dicts, events, families, relationships, memories, edu_inst_dicts, edu_prog_dicts, edu_hist_dicts, pregnancies_dicts = db.load_world()
                if not time_dict:
                    QMessageBox.warning(self, "Загрузка", "В файле нет сохраненного мира.")
                    return

                self.sim = Simulation()
                self.sim.time.set_time_from_dict(time_dict)

                from living_world.city.city import Building
                for b in b_dicts:
                    self.sim.city.add_building(Building(b['name'], b['type'], b['capacity'], b['id']))

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

                    npc.money = nd['money']
                    npc.hunger = nd['hunger']
                    npc.energy = nd['energy']
                    npc.mood = nd['mood']
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
                        'patience': nd.get('trait_patience', 0.0)
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

                self.pop_tab.simulation = self.sim
                self.fam_tab.simulation = self.sim

                self.lbl_time.setText(self.sim.time.format_time())
                self.pop_tab.update_data()
                self.update_log()

                QMessageBox.information(self, "Загрузка", "Мир успешно загружен!")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Ошибка загрузки: {e}")
