from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QFormLayout, QTabWidget, QWidget, QProgressBar, QListWidget, QTableWidget, QTableWidgetItem, QHeaderView
from PySide6.QtCore import QTimer, Qt

class NPCCardDialog(QDialog):
    def __init__(self, npc, city=None, parent=None):
        super().__init__(parent)
        self.npc = npc
        self.city = city
        self.sim = parent.sim if hasattr(parent, 'sim') else None

        self.setWindowTitle(f"Карточка жителя: {npc.get_full_name()}")
        self.resize(500, 600)

        layout = QVBoxLayout(self)

        self.tabs = QTabWidget()

        self._init_general_tab()
        self._init_traits_tab()
        self._init_education_tab()
        self._init_relationships_tab()
        self._init_family_tab()
        self._init_memory_tab()

        layout.addWidget(self.tabs)

        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.update_data)
        self.update_timer.start(1000)

    def _init_general_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        self.form = QFormLayout()
        self.labels = {}



        current_date = self.sim.time.current_datetime if self.sim else None
        data = self.npc.to_dict(self.city, current_world_date=current_date)

        if self.sim:
            mother = next((n for n in self.sim.npcs if n.id == self.npc.mother_id), None) if getattr(self.npc, 'mother_id', None) else None
            father = next((n for n in self.sim.npcs if n.id == self.npc.father_id), None) if getattr(self.npc, 'father_id', None) else None
            data['Мать'] = mother.get_full_name() if mother else "Неизвестна"
            data['Отец'] = father.get_full_name() if father else "Неизвестен"

            if self.npc.gender == 'Ж' and getattr(self.sim, 'reproduction_manager', None):
                active_preg = next((p for p in self.sim.reproduction_manager.active_pregnancies if p.mother_id == self.npc.id and p.status == 'active'), None)
                if active_preg:
                     data['Беременность'] = 'Да'
                     data['Ожидаемая дата родов'] = active_preg.expected_birth_date.strftime("%d.%m.%Y")

        for key, value in data.items():
            val_label = QLabel(str(value))
            self.labels[key] = val_label
            self.form.addRow(QLabel(f"<b>{key}:</b>"), val_label)



        layout.addLayout(self.form)
        self.tabs.addTab(tab, "Общая информация")

    def _init_education_tab(self):
        self.edu_tab = QWidget()
        layout = QVBoxLayout(self.edu_tab)

        self.edu_info = QLabel("Загрузка...")
        self.edu_info.setWordWrap(True)
        layout.addWidget(self.edu_info)

        self.edu_history_table = QTableWidget()
        self.edu_history_table.setColumnCount(4)
        self.edu_history_table.setHorizontalHeaderLabels(["Учреждение", "Программа", "Статус", "Квалификация"])
        self.edu_history_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.edu_history_table.setEditTriggers(QTableWidget.NoEditTriggers)

        layout.addWidget(self.edu_history_table)
        self.tabs.addTab(self.edu_tab, "Образование")
        self._populate_education()

    def _populate_education(self):
        if not self.sim or not getattr(self.sim, 'education_manager', None):
            self.edu_info.setText("Система образования недоступна.")
            return

        em = self.sim.education_manager

        status_text = "<b>Текущее состояние:</b><br>"
        if getattr(self.npc, 'education_status', None) == "Обучается" and getattr(self.npc, 'current_education_id', None):
            prog = em.programs.get(self.npc.current_education_id)
            if prog:
                inst = em.institutions.get(prog.institution_id)
                inst_name = inst.name if inst else "Неизвестно"
                status_text += f"Учится в {inst_name} на программе '{prog.name}'."
            else:
                status_text += "Обучается (программа неизвестна)."
        else:
            status_text += "Не обучается в данный момент."

        self.edu_info.setText(status_text)

        # История
        records = [r for r in em.history if r.npc_id == self.npc.id]
        self.edu_history_table.setRowCount(len(records))
        for row, r in enumerate(records):
            inst = em.institutions.get(r.institution_id)
            prog = em.programs.get(r.program_id)

            inst_name = inst.name if inst else "Неизвестно"
            prog_name = prog.name if prog else "Неизвестно"

            self.edu_history_table.setItem(row, 0, QTableWidgetItem(inst_name))
            self.edu_history_table.setItem(row, 1, QTableWidgetItem(prog_name))
            self.edu_history_table.setItem(row, 2, QTableWidgetItem(r.status))
            self.edu_history_table.setItem(row, 3, QTableWidgetItem(r.qualification or "-"))

    def _init_traits_tab(self):
        tab = QWidget()
        layout = QFormLayout(tab)

        traits_map = {
            'sociability': 'Общительность',
            'friendliness': 'Дружелюбие',
            'conflict': 'Конфликтность',
            'empathy': 'Эмпатия',
            'boldness': 'Смелость',
            'patience': 'Терпение'
        }

        for key, name in traits_map.items():
            val = self.npc.traits.get(key, 0)
            bar = QProgressBar()
            bar.setRange(-100, 100)
            bar.setValue(int(val * 100))
            layout.addRow(QLabel(name), bar)

        self.tabs.addTab(tab, "Характер")

    def _init_relationships_tab(self):
        self.rel_tab = QWidget()
        layout = QVBoxLayout(self.rel_tab)

        self.rel_table = QTableWidget()
        self.rel_table.setColumnCount(4)
        self.rel_table.setHorizontalHeaderLabels(["NPC", "Знакомство", "Симпатия", "Доверие"])
        self.rel_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.rel_table.setEditTriggers(QTableWidget.NoEditTriggers)

        layout.addWidget(self.rel_table)
        self.tabs.addTab(self.rel_tab, "Отношения")
        self._populate_relationships()

    def _init_memory_tab(self):
        self.mem_tab = QWidget()
        layout = QVBoxLayout(self.mem_tab)

        self.mem_list = QListWidget()
        layout.addWidget(self.mem_list)

        self.tabs.addTab(self.mem_tab, "Память")
        self._populate_memories()

    def _init_family_tab(self):
        self.family_tab = QWidget()
        layout = QVBoxLayout(self.family_tab)

        # Блок "Домохозяйство"
        self.household_info = QLabel("Домохозяйство: загрузка...")
        self.household_info.setWordWrap(True)
        layout.addWidget(self.household_info)

        self.household_table = QTableWidget()
        self.household_table.setColumnCount(4)
        self.household_table.setHorizontalHeaderLabels(["Роль", "Имя", "Возраст/Этап", "Статус"])
        self.household_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.household_table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.household_table)

        layout.addWidget(QLabel("<b>Биологические связи</b>"))

        # Блок "Семья" (биологическая)
        self.family_table = QTableWidget()
        self.family_table.setColumnCount(4)
        self.family_table.setHorizontalHeaderLabels(["Роль", "Имя", "Возраст/Этап", "Статус"])
        self.family_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.family_table.setEditTriggers(QTableWidget.NoEditTriggers)

        layout.addWidget(self.family_table)
        self.tabs.addTab(self.family_tab, "Семья")
        self._populate_family()

    def _populate_family(self):
        if not self.sim: return
        current_date = self.sim.time.current_datetime
        from living_world.engine.life_cycle_manager import LifeCycleManager

        # Populate Household
        if getattr(self.sim, 'household_manager', None) and getattr(self.npc, 'household_id', None):
            hm = self.sim.household_manager
            hh_id = self.npc.household_id

            home_b = self.city.get_building(self.npc.home_id) if self.city else None
            home_name = home_b.name if home_b else "Неизвестно"

            total_wealth = hm.get_total_wealth(hh_id)
            hh_text = f"<b>Домохозяйство:</b> Проживает в {home_name} <br><b>Общие ресурсы (сумма денег):</b> {total_wealth:.2f} ₽"
            self.household_info.setText(hh_text)

            adults = hm.get_adults(hh_id)
            children = hm.get_children(hh_id)

            # Все остальные, кто не попал в adults и children, но жив (например TEEN)
            members = hm.get_household_members(hh_id)
            others = [m for m in members if m not in adults and m not in children and m.is_alive]

            hh_rows = []
            for a in adults: hh_rows.append(("Взрослый", a))
            for c in children: hh_rows.append(("Иждивенец", c))
            for o in others: hh_rows.append(("Член домохозяйства", o))

            # Добавим и умерших, которые числились в этом домохозяйстве (для истории)
            dead_members = [m for m in members if not m.is_alive]
            for d in dead_members: hh_rows.append(("В архиве", d))

            self.household_table.setRowCount(len(hh_rows))
            for row, (role, rel_npc) in enumerate(hh_rows):
                age = rel_npc.get_age(current_date)
                stage_str = LifeCycleManager.format_life_stage_ru(rel_npc.get_life_stage(current_date))

                self.household_table.setItem(row, 0, QTableWidgetItem(role))
                self.household_table.setItem(row, 1, QTableWidgetItem(rel_npc.get_full_name()))
                self.household_table.setItem(row, 2, QTableWidgetItem(f"{age} ({stage_str})"))
                self.household_table.setItem(row, 3, QTableWidgetItem("Жив" if rel_npc.is_alive else "Умер"))
        else:
            self.household_info.setText("Нет данных о домохозяйстве.")
            self.household_table.setRowCount(0)

        # Populate Family (Biological)
        if getattr(self.sim, 'family_manager', None):
            fm = self.sim.family_manager
            parents = fm.get_parents(self.npc.id)
            children = fm.get_children(self.npc.id)
            siblings = fm.get_siblings(self.npc.id)

            rows = []
            for p in parents: rows.append(("Мать" if p.gender == 'Ж' else "Отец", p))
            for c in children: rows.append(("Сын" if c.gender == 'М' else "Дочь", c))
            for s in siblings: rows.append(("Брат" if s.gender == 'М' else "Сестра", s))

            self.family_table.setRowCount(len(rows))
            for row, (role, rel_npc) in enumerate(rows):
                age = rel_npc.get_age(current_date)
                stage_str = LifeCycleManager.format_life_stage_ru(rel_npc.get_life_stage(current_date))

                self.family_table.setItem(row, 0, QTableWidgetItem(role))
                self.family_table.setItem(row, 1, QTableWidgetItem(rel_npc.get_full_name()))
                self.family_table.setItem(row, 2, QTableWidgetItem(f"{age} ({stage_str})"))
                self.family_table.setItem(row, 3, QTableWidgetItem("Жив" if rel_npc.is_alive else "Умер"))

    def _populate_relationships(self):
        if not self.sim: return
        rels = self.sim.relationship_manager.get_all_relationships_for(self.npc.id)
        # Filter only non-zero familiarity
        rels = [r for r in rels if r['familiarity'] > 0]

        self.rel_table.setRowCount(len(rels))
        for row, rel in enumerate(rels):
            target = next((n for n in self.sim.npcs if n.id == rel['target_npc_id']), None)
            name = target.get_full_name() if target else "Неизвестный"

            self.rel_table.setItem(row, 0, QTableWidgetItem(name))
            self.rel_table.setItem(row, 1, QTableWidgetItem(f"{rel['familiarity']:.1f}"))
            self.rel_table.setItem(row, 2, QTableWidgetItem(f"{rel['affinity']:.1f}"))
            self.rel_table.setItem(row, 3, QTableWidgetItem(f"{rel['trust']:.1f}"))

    def _populate_memories(self):
        if not self.sim: return
        self.mem_list.clear()
        memories = self.sim.memory_manager.get_memories(self.npc.id)
        for mem in reversed(memories[-50:]): # Show last 50
            target_str = ""
            if mem['target_npc_id']:
                target = next((n for n in self.sim.npcs if n.id == mem['target_npc_id']), None)
                if target:
                    target_str = f" → {target.get_full_name()}"

            item_text = f"[{mem['time']}] {mem['event_type']}{target_str}\n{mem['description']}"
            self.mem_list.addItem(item_text)

    def update_data(self):
        current_date = self.sim.time.current_datetime if self.sim else None
        data = self.npc.to_dict(self.city, current_world_date=current_date)

        if self.sim:
            mother = next((n for n in self.sim.npcs if n.id == self.npc.mother_id), None) if getattr(self.npc, 'mother_id', None) else None
            father = next((n for n in self.sim.npcs if n.id == self.npc.father_id), None) if getattr(self.npc, 'father_id', None) else None
            data['Мать'] = mother.get_full_name() if mother else "Неизвестна"
            data['Отец'] = father.get_full_name() if father else "Неизвестен"

            if self.npc.gender == 'Ж' and getattr(self.sim, 'reproduction_manager', None):
                active_preg = next((p for p in self.sim.reproduction_manager.active_pregnancies if p.mother_id == self.npc.id and p.status == 'active'), None)
                if active_preg:
                     data['Беременность'] = 'Да'
                     data['Ожидаемая дата родов'] = active_preg.expected_birth_date.strftime("%d.%m.%Y")

        for key, value in data.items():
            if key in self.labels:
                self.labels[key].setText(str(value))
            else:
                val_label = QLabel(str(value))
                self.labels[key] = val_label
                self.form.addRow(QLabel(f"<b>{key}:</b>"), val_label)

        # To avoid UI flickering, we only fully re-populate if tab is visible,
        # but for simplicity let's just re-populate
        if self.tabs.currentIndex() == 2:
            self._populate_education()
        elif self.tabs.currentIndex() == 3:
            self._populate_relationships()
        elif self.tabs.currentIndex() == 4:
            self._populate_family()
        elif self.tabs.currentIndex() == 5:
            self._populate_memories()
