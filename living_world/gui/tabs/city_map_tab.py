from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QGraphicsView, QGraphicsScene, QGraphicsRectItem,
    QGraphicsEllipseItem, QGraphicsTextItem, QFrame, QSplitter,
    QListWidget, QListWidgetItem, QGraphicsDropShadowEffect
)
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QColor, QBrush, QPen, QFont, QRadialGradient
from living_world.gui.dialogs.family_tree_dialog import FamilyTreeDialog

class BuildingGraphicsItem(QGraphicsRectItem):
    def __init__(self, building, map_tab, x, y, w, h):
        super().__init__(x, y, w, h)
        self.building = building
        self.map_tab = map_tab
        self.setAcceptHoverEvents(True)
        self.setCursor(Qt.PointingHandCursor)

    def mousePressEvent(self, event):
        self.map_tab.select_building(self.building)
        super().mousePressEvent(event)


class NPCGraphicsItem(QGraphicsEllipseItem):
    def __init__(self, npc, map_tab, x, y, r=6):
        super().__init__(x - r, y - r, r * 2, r * 2)
        self.npc = npc
        self.map_tab = map_tab
        self.setAcceptHoverEvents(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip(f"{npc.get_full_name()} ({npc.profession})\nСтатус: {npc.state}\nДеньги: {npc.money:.0f} ₽\nНастроение: {int(npc.mood)}%")

    def mousePressEvent(self, event):
        self.map_tab.open_npc_family_tree(self.npc.id)
        super().mousePressEvent(event)


class CityMapTab(QWidget):
    """
    Интерактивная 2D-карта города в реальном времени.
    Отображает план районов, контуры зданий, перемещение жителей,
    ночное освещение и аналитические тепловые карты (Heatmaps).
    """
    BUILDING_COLORS = {
        'home': QColor("#3498DB"),         # Жилой дом (лазурный)
        'shop': QColor("#E67E22"),         # Магазин (оранжевый)
        'cafe': QColor("#D35400"),         # Кафе / пекарня
        'work': QColor("#E67E22"),         # Предприятие
        'farm': QColor("#795548"),         # Ферма (коричневый)
        'workshop': QColor("#7F8C8D"),     # Мастерская
        'construction': QColor("#F39C12"), # Стройка
        'park': QColor("#27AE60"),         # Парк (зеленый)
        'hospital': QColor("#16A085"),     # Больница (бирюзовый)
        'school': QColor("#9B59B6"),       # Школа
        'police': QColor("#1B2A47"),       # Полиция (темно-синий)
        'library': QColor("#8E44AD"),      # Библиотека
        'cinema': QColor("#9B59B6"),       # Кинотеатр
        'stadium': QColor("#2980B9")       # Стадион
    }

    def __init__(self, simulation, main_window):
        super().__init__()
        self.simulation = simulation
        self.main_window = main_window
        self.selected_building = None
        self.current_mode = "Обычный план"

        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(6, 6, 6, 6)

        # Верхняя панель управления
        top_bar = QHBoxLayout()

        lbl_mode = QLabel("Режим отображения:")
        lbl_mode.setStyleSheet("font-weight: bold;")
        self.cb_mode = QComboBox()
        self.cb_mode.addItems([
            "Обычный план",
            "Плотность населения (Теплокарта)",
            "Уровень достатка (Теплокарта)",
            "Уровень преступности (Теплокарта)",
            "Технический износ фонда (Теплокарта)"
        ])
        self.cb_mode.currentIndexChanged.connect(self._on_mode_changed)

        self.lbl_env = QLabel("☀️ День · 20°C")
        self.lbl_env.setStyleSheet("font-weight: bold; color: #2C3E50; margin-left: 15px;")

        self.lbl_stats = QLabel()
        self.lbl_stats.setStyleSheet("color: #555; margin-left: 15px;")

        btn_zoom_in = QPushButton("🔍 +")
        btn_zoom_in.setFixedWidth(40)
        btn_zoom_in.clicked.connect(lambda: self.view.scale(1.2, 1.2))

        btn_zoom_out = QPushButton("🔍 -")
        btn_zoom_out.setFixedWidth(40)
        btn_zoom_out.clicked.connect(lambda: self.view.scale(0.8, 0.8))

        top_bar.addWidget(lbl_mode)
        top_bar.addWidget(self.cb_mode)
        top_bar.addWidget(self.lbl_env)
        top_bar.addWidget(self.lbl_stats)
        top_bar.addStretch()
        top_bar.addWidget(btn_zoom_in)
        top_bar.addWidget(btn_zoom_out)

        main_layout.addLayout(top_bar)

        # Сплиттер: слева интерактивная сцена карты, справа карточка выбранного здания
        splitter = QSplitter(Qt.Horizontal)

        self.scene = QGraphicsScene()
        self.view = QGraphicsView(self.scene)
        self.view.setRenderHints(self.view.renderHints())
        self.view.setDragMode(QGraphicsView.ScrollHandDrag)
        splitter.addWidget(self.view)

        # Боковая карточка инспекции здания
        self.side_panel = QFrame()
        self.side_panel.setFixedWidth(280)
        self.side_panel.setFrameShape(QFrame.StyledPanel)
        side_layout = QVBoxLayout(self.side_panel)

        self.lbl_building_title = QLabel("Выберите объект на карте")
        self.lbl_building_title.setStyleSheet("font-weight: bold; font-size: 14px; color: #1565C0;")
        self.lbl_building_title.setWordWrap(True)
        side_layout.addWidget(self.lbl_building_title)

        self.lbl_building_info = QLabel("Кликните на любое здание для просмотра жильцов, сотрудников и ресурсов.")
        self.lbl_building_info.setWordWrap(True)
        self.lbl_building_info.setStyleSheet("color: #444; font-size: 11px;")
        side_layout.addWidget(self.lbl_building_info)

        lbl_occ = QLabel("Присутствующие граждане:")
        lbl_occ.setStyleSheet("font-weight: bold; margin-top: 8px;")
        side_layout.addWidget(lbl_occ)

        self.occupants_list = QListWidget()
        self.occupants_list.itemDoubleClicked.connect(self._on_occupant_double_clicked)
        side_layout.addWidget(self.occupants_list)

        self.btn_tree = QPushButton("🌳 Древо семьи выбранного")
        self.btn_tree.clicked.connect(self._open_selected_occupant_tree)
        side_layout.addWidget(self.btn_tree)

        splitter.addWidget(self.side_panel)
        splitter.setStretchFactor(0, 4)
        splitter.setStretchFactor(1, 1)

        main_layout.addWidget(splitter)

    def _on_mode_changed(self, idx):
        self.current_mode = self.cb_mode.currentText()
        self.update_data()

    def select_building(self, building):
        self.selected_building = building
        self.lbl_building_title.setText(f"🏢 {building.name}")

        city = self.simulation.city
        dist = city.get_district_for_building(building.id) if hasattr(city, 'get_district_for_building') else None
        dist_name = dist.name if dist else "Центральный район"

        econ = getattr(self.simulation, 'economy_manager', None)
        ent = econ.get_enterprise_for_building(building.id) if econ else None

        info_lines = [
            f"Район: {dist_name}",
            f"Тип: {building.b_type}",
            f"Вместимость: {building.capacity} чел.",
            f"Износ: {100.0 - building.condition:.1f}% (Состояние: {building.condition:.1f}%)"
        ]

        if ent:
            info_lines.append(f"Предприятие: «{ent.name}»")
            info_lines.append(f"Бюджет: {ent.budget:,.0f} ₽")
            if getattr(ent, 'raw_materials', 0) > 0:
                info_lines.append(f"Склад сырья: {ent.raw_materials:.1f} ед.")
            if getattr(ent, 'finished_goods', 0) > 0:
                info_lines.append(f"Готовая продукция: {ent.finished_goods:.1f} ед.")

        self.lbl_building_info.setText("\n".join(info_lines))

        # Наполнение списка жильцов
        self.occupants_list.clear()
        occupants = [n for n in self.simulation.npcs if n.is_alive and n.current_location == building.id]
        for occ in occupants:
            item = QListWidgetItem(f"👤 {occ.get_full_name()} — {occ.profession} ({occ.state})")
            item.setData(Qt.UserRole, occ.id)
            self.occupants_list.addItem(item)

        if not occupants:
            self.occupants_list.addItem(QListWidgetItem("Внутри никого нет"))

    def _on_occupant_double_clicked(self, item):
        npc_id = item.data(Qt.UserRole)
        if npc_id:
            self.open_npc_family_tree(npc_id)

    def _open_selected_occupant_tree(self):
        cur_item = self.occupants_list.currentItem()
        if cur_item:
            npc_id = cur_item.data(Qt.UserRole)
            if npc_id:
                self.open_npc_family_tree(npc_id)

    def open_npc_family_tree(self, npc_id: str):
        dlg = FamilyTreeDialog(npc_id, self.simulation, self)
        dlg.exec()

    def update_data(self):
        """Перерисовка графической сцены карты города."""
        self.scene.clear()

        time_dict = self.simulation.time.get_time_dict()
        hour = time_dict['hour']
        is_night = hour < 7 or hour >= 21

        # Погода и освещение
        wm = getattr(self.simulation, 'weather_manager', None)
        temp = wm.temperature if wm else 20.0
        weather_cond = getattr(wm, "weather_condition", "Ясно") if wm else "Ясно"
        time_icon = "🌙" if is_night else "☀️"
        self.lbl_env.setText(f"{time_icon} {time_dict['hour']:02d}:{time_dict['minute']:02d} · {temp:+.1f}°C ({weather_cond})")

        # Фон сцены
        bg_color = QColor("#141A29") if is_night else QColor("#EDF2F7")
        self.scene.setBackgroundBrush(QBrush(bg_color))

        city = self.simulation.city
        buildings = city.buildings
        if not buildings:
            return

        # Назначаем координаты зданиям, если они еще не расставлены (0, 0)
        self._ensure_coordinates(buildings)

        # 1. Сетка дорог
        self._draw_road_grid(is_night)

        # 2. Отрисовка районов
        self._draw_districts(city, is_night)

        # 3. Отрисовка зданий
        for b in buildings:
            self._draw_building(b, is_night)

        # 4. Отрисовка жителей
        self._draw_npcs()

        # Статистика
        alive_npcs = [n for n in self.simulation.npcs if n.is_alive]
        outdoor_npcs = [n for n in alive_npcs if n.current_location not in [b.id for b in buildings]]
        self.lbl_stats.setText(f"Зданий: {len(buildings)} | Жителей: {len(alive_npcs)} | На улице: {len(outdoor_npcs)}")

    def _ensure_coordinates(self, buildings):
        """Гарантирует красивое структурированное распределение зданий по кварталам."""
        need_layout = any(b.x == 0.0 and b.y == 0.0 for b in buildings)
        if not need_layout:
            return

        col_w = 120
        row_h = 100
        homes = [b for b in buildings if b.b_type == 'home']
        works = [b for b in buildings if b.b_type in ['work', 'farm', 'workshop', 'construction']]
        services = [b for b in buildings if b.b_type in ['shop', 'cafe', 'hospital', 'school', 'police', 'library', 'cinema', 'stadium', 'park']]

        # Жилой квартал (слева)
        for idx, h in enumerate(homes):
            col = idx % 3
            row = idx // 3
            h.x = 60 + col * col_w
            h.y = 80 + row * row_h

        # Общественный центр (посередине)
        for idx, s in enumerate(services):
            col = idx % 2
            row = idx // 2
            s.x = 480 + col * col_w
            s.y = 80 + row * row_h

        # Промзона и рабочие предприятия (справа)
        for idx, w in enumerate(works):
            col = idx % 2
            row = idx // 2
            w.x = 780 + col * col_w
            w.y = 80 + row * row_h

    def _draw_road_grid(self, is_night: bool):
        road_pen = QPen(QColor("#252E42") if is_night else QColor("#CBD5E0"), 36)
        dash_pen = QPen(QColor("#F1C40F" if is_night else "#FFFFFF"), 2, Qt.DashLine)

        # Проспекты
        for y in [160, 360, 560]:
            self.scene.addLine(20, y, 1050, y, road_pen)
            self.scene.addLine(20, y, 1050, y, dash_pen)
        for x in [420, 720]:
            self.scene.addLine(x, 20, x, 680, road_pen)
            self.scene.addLine(x, 20, x, 680, dash_pen)

    def _draw_districts(self, city, is_night: bool):
        # Названия кварталов
        d_color = QColor(255, 255, 255, 120) if is_night else QColor(40, 50, 70, 160)
        font = QFont("Arial", 11, QFont.Bold)

        t1 = self.scene.addText("🏡 ЖИЛОЙ КВАРТАЛ", font)
        t1.setDefaultTextColor(d_color)
        t1.setPos(120, 25)

        t2 = self.scene.addText("🏛 ГОРОДСКОЙ ЦЕНТР", font)
        t2.setDefaultTextColor(d_color)
        t2.setPos(480, 25)

        t3 = self.scene.addText("🏭 ПРОМЫШЛЕННАЯ ЗОНА", font)
        t3.setDefaultTextColor(d_color)
        t3.setPos(780, 25)

    def _draw_building(self, b, is_night: bool):
        bw, bh = 85, 60
        x, y = b.x, b.y

        color = self._get_building_color(b)
        border_pen = QPen(QColor("#FFFFFF" if is_night else "#2D3748"), 2)

        rect_item = BuildingGraphicsItem(b, self, x, y, bw, bh)
        rect_item.setBrush(QBrush(color))
        rect_item.setPen(border_pen)
        self.scene.addItem(rect_item)

        # Окна (ночное освещение)
        occupants = [n for n in self.simulation.npcs if n.is_alive and n.current_location == b.id]
        if is_night and occupants:
            win_brush = QBrush(QColor("#F1C40F"))
            for wx, wy in [(x + 12, y + 14), (x + 36, y + 14), (x + 60, y + 14),
                           (x + 12, y + 36), (x + 36, y + 36), (x + 60, y + 36)]:
                win_item = self.scene.addRect(wx, wy, 12, 10, QPen(Qt.NoPen), win_brush)

        # Подпись названия здания
        font_name = QFont("Arial", 8, QFont.Bold)
        text_item = self.scene.addText(b.name, font_name)
        text_item.setDefaultTextColor(QColor("#E2E8F0" if is_night else "#2D3748"))
        text_item.setPos(x - 5, y + bh + 2)

        # Бейдж числа людей внутри
        if occupants:
            badge_r = 10
            badge = self.scene.addEllipse(x + bw - 12, y - 6, badge_r * 2, badge_r * 2,
                                         QPen(Qt.NoPen), QBrush(QColor("#E74C3C")))
            t_cnt = self.scene.addText(str(len(occupants)), QFont("Arial", 7, QFont.Bold))
            t_cnt.setDefaultTextColor(QColor("white"))
            t_cnt.setPos(x + bw - 9, y - 9)

    def _get_building_color(self, b) -> QColor:
        if self.current_mode == "Плотность населения (Теплокарта)":
            occ_count = sum(1 for n in self.simulation.npcs if n.is_alive and n.current_location == b.id)
            if occ_count == 0:
                return QColor("#7F8C8D")
            elif occ_count <= 2:
                return QColor("#2ECC71")
            elif occ_count <= 5:
                return QColor("#F1C40F")
            else:
                return QColor("#E74C3C")

        elif self.current_mode == "Уровень достатка (Теплокарта)":
            econ = getattr(self.simulation, 'economy_manager', None)
            ent = econ.get_enterprise_for_building(b.id) if econ else None
            wealth = ent.budget if ent else 0.0
            occ_wealth = sum(n.money for n in self.simulation.npcs if n.is_alive and n.current_location == b.id)
            total_w = wealth + occ_wealth
            if total_w < 5000:
                return QColor("#95A5A6")
            elif total_w < 35000:
                return QColor("#3498DB")
            elif total_w < 100000:
                return QColor("#F39C12")
            else:
                return QColor("#27AE60")

        elif self.current_mode == "Уровень преступности (Теплокарта)":
            cm = getattr(self.simulation, 'crime_manager', None)
            crime_cnt = sum(1 for c in cm.crime_history if c.get('location_id') == b.id) if cm else 0
            if crime_cnt == 0:
                return QColor("#2ECC71")
            elif crime_cnt <= 2:
                return QColor("#E67E22")
            else:
                return QColor("#C0392B")

        elif self.current_mode == "Технический износ фонда (Теплокарта)":
            if b.condition >= 80.0:
                return QColor("#2ECC71")
            elif b.condition >= 60.0:
                return QColor("#F39C12")
            else:
                return QColor("#E74C3C")

        # Обычный режим
        return self.BUILDING_COLORS.get(b.b_type, QColor("#3498DB"))

    def _draw_npcs(self):
        """Отрисовка жителей на карте."""
        city = self.simulation.city
        b_map = {b.id: b for b in city.buildings}

        for idx, npc in enumerate(self.simulation.npcs):
            if not npc.is_alive:
                continue

            b = b_map.get(npc.current_location)
            if b:
                # Внутри здания: расставляем небольшим смещением
                slot = idx % 6
                nx = b.x + 18 + (slot % 3) * 22
                ny = b.y + 20 + (slot // 3) * 18
            else:
                # На улице / в пути
                nx = 420 + (idx % 8) * 35
                ny = 160 + (idx // 8) * 45

            # Цвет маркера
            if getattr(npc, 'jail_days', 0) > 0:
                color = QColor("#C0392B") # Красный (в тюрьме)
            elif npc.profession == "Мэр":
                color = QColor("#F1C40F") # Золотой (Мэр)
            elif npc.profession in ["Полицейский", "Участковый"]:
                color = QColor("#2980B9") # Синий шериф
            elif npc.gender == "Ж":
                color = QColor("#E84393") # Малиновый
            else:
                color = QColor("#0984E3") # Голубой

            npc_item = NPCGraphicsItem(npc, self, nx, ny, r=5)
            npc_item.setBrush(QBrush(color))
            npc_item.setPen(QPen(QColor("#FFFFFF"), 1))
            self.scene.addItem(npc_item)
