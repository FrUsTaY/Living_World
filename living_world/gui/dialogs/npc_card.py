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
        self._init_relationships_tab()
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

        data = self.npc.to_dict(self.city)
        for key, value in data.items():
            val_label = QLabel(str(value))
            self.labels[key] = val_label
            self.form.addRow(QLabel(f"<b>{key}:</b>"), val_label)

        layout.addLayout(self.form)
        self.tabs.addTab(tab, "Общая информация")

    def _init_traits_tab(self):
        tab = QWidget()
        layout = QFormLayout(tab)

        traits_map = {
            'sociability': 'Общительность',
            'friendliness': 'Дружелюбие',
            'conflict': 'Конфликтность',
            'empathy': 'Эмпатия',
            'boldness': 'Смелость',
            'patience': 'Терпеливость'
        }

        for key, name in traits_map.items():
            val = self.npc.traits.get(key, 0.0)
            # Convert -1.0 to 1.0 to 0-100 for display
            percent = int((val + 1.0) / 2.0 * 100)

            bar = QProgressBar()
            bar.setRange(0, 100)
            bar.setValue(percent)

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
            self.rel_table.setItem(row, 1, QTableWidgetItem(f"{int(rel['familiarity'])}%"))
            self.rel_table.setItem(row, 2, QTableWidgetItem(f"{int(rel['affinity'])}%"))
            self.rel_table.setItem(row, 3, QTableWidgetItem(f"{int(rel['trust'])}%"))

    def _populate_memories(self):
        if not self.sim: return
        memories = self.sim.memory_manager.get_memories_for(self.npc.id)

        self.mem_list.clear()
        for mem in reversed(memories): # Show newest first
            target = next((n for n in self.sim.npcs if n.id == mem['target_npc_id']), None)
            target_name = target.get_full_name() if target else ""

            item_text = f"[{mem['sim_time']}] {mem['event_type']}: {mem['description']}"
            self.mem_list.addItem(item_text)

    def update_data(self):
        data = self.npc.to_dict(self.city)
        for key, value in data.items():
            if key in self.labels:
                self.labels[key].setText(str(value))

        # To avoid UI flickering, we only fully re-populate if tab is visible,
        # but for simplicity let's just re-populate
        if self.tabs.currentIndex() == 2:
            self._populate_relationships()
        elif self.tabs.currentIndex() == 3:
            self._populate_memories()
