from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QWidget, QFrame, QGridLayout
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from living_world.engine.genetics.family_tree_builder import FamilyTreeBuilder

class FamilyTreeDialog(QDialog):
    """
    Интерактивное визуальное древо семьи и династии.
    Позволяет исследовать предков и потомков любого жителя.
    """
    def __init__(self, npc_id: str, simulation, parent=None):
        super().__init__(parent)
        self.npc_id = npc_id
        self.simulation = simulation
        self.setWindowTitle("Генеалогическое древо династии")
        self.resize(880, 680)

        main_layout = QVBoxLayout(self)

        # Заголовок
        self.header_label = QLabel()
        self.header_label.setAlignment(Qt.AlignCenter)
        font = QFont()
        font.setPointSize(14)
        font.setBold(True)
        self.header_label.setFont(font)
        main_layout.addWidget(self.header_label)

        # Скролл-область для визуализации поколений
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.content_widget = QWidget()
        self.tree_layout = QVBoxLayout(self.content_widget)
        self.tree_layout.setSpacing(15)
        scroll.setWidget(self.content_widget)
        main_layout.addWidget(scroll)

        # Закрыть
        btn_close = QPushButton("Закрыть")
        btn_close.clicked.connect(self.accept)
        main_layout.addWidget(btn_close)

        self.render_tree(self.npc_id)

    def render_tree(self, npc_id: str):
        # Очистить предыдущее отображение
        while self.tree_layout.count():
            item = self.tree_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        tree_data = FamilyTreeBuilder.build_tree(npc_id, self.simulation)
        if not tree_data:
            self.header_label.setText("Данные о жителе не найдены")
            return

        subject = tree_data["subject"]
        self.header_label.setText(f"🌳 Родословное древо: {subject['full_name']} ({subject['age']} лет)")

        # 1. Поколение: Дедушки и Бабушки
        gp = tree_data["grandparents"]
        gp_list = [gp["paternal_grandfather"], gp["paternal_grandmother"], gp["maternal_grandfather"], gp["maternal_grandmother"]]
        gp_list = [g for g in gp_list if g]
        if gp_list:
            self.tree_layout.addWidget(self._create_generation_section("👵 Дедушки и бабушки", gp_list))

        # 2. Поколение: Родители
        p_list = [tree_data["parents"]["father"], tree_data["parents"]["mother"]]
        p_list = [p for p in p_list if p]
        if p_list:
            self.tree_layout.addWidget(self._create_generation_section("👨‍👩‍👦 Родители", p_list))

        # 3. Текущее поколение: Житель, Супруг(а) и Братья/Сестры
        cur_gen_layout = QVBoxLayout()
        lbl = QLabel("👤 Текущее поколение")
        lbl.setStyleSheet("font-weight: bold; color: #2b5b84; font-size: 13px;")
        cur_gen_layout.addWidget(lbl)

        h_box = QHBoxLayout()
        # Сам житель (выделен рамкой)
        h_box.addWidget(self._create_npc_card(subject, is_focus=True))

        # Супруг(а)
        if tree_data.get("spouse"):
            h_box.addWidget(self._create_npc_card(tree_data["spouse"], subtitle="Супруг(а)"))

        # Братья и сестры
        for sib in tree_data.get("siblings", []):
            h_box.addWidget(self._create_npc_card(sib, subtitle="Брат/Сестра"))

        h_box.addStretch()
        cur_gen_widget = QWidget()
        cur_gen_widget.setLayout(h_box)
        cur_gen_layout.addWidget(cur_gen_widget)

        cur_frame = QFrame()
        cur_frame.setFrameShape(QFrame.StyledPanel)
        cur_frame.setLayout(cur_gen_layout)
        self.tree_layout.addWidget(cur_frame)

        # 4. Поколение: Дети
        if tree_data.get("children"):
            self.tree_layout.addWidget(self._create_generation_section("👶 Дети", tree_data["children"]))

        # 5. Поколение: Внуки
        if tree_data.get("grandchildren"):
            self.tree_layout.addWidget(self._create_generation_section("🍼 Внуки", tree_data["grandchildren"]))

        self.tree_layout.addStretch()

    def _create_generation_section(self, title: str, npcs: list) -> QWidget:
        frame = QFrame()
        frame.setFrameShape(QFrame.StyledPanel)
        v_box = QVBoxLayout(frame)

        lbl = QLabel(title)
        lbl.setStyleSheet("font-weight: bold; color: #2b5b84; font-size: 13px;")
        v_box.addWidget(lbl)

        h_box = QHBoxLayout()
        for n in npcs:
            h_box.addWidget(self._create_npc_card(n))
        h_box.addStretch()

        w = QWidget()
        w.setLayout(h_box)
        v_box.addWidget(w)
        return frame

    def _create_npc_card(self, n_info: dict, is_focus: bool = False, subtitle: str = None) -> QWidget:
        card = QFrame()
        card.setFixedSize(190, 130)

        border_color = "#1976D2" if is_focus else "#CCCCCC"
        bg_color = "#E3F2FD" if is_focus else ("#F9F9F9" if n_info['is_alive'] else "#EAEAEA")
        card.setStyleSheet(f"QFrame {{ background-color: {bg_color}; border: 2px solid {border_color}; border-radius: 6px; padding: 4px; }}")

        layout = QVBoxLayout(card)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(2)

        status_icon = "🟢" if n_info['is_alive'] else "✝"
        name_btn = QPushButton(f"{status_icon} {n_info['full_name']}")
        name_btn.setStyleSheet("text-align: left; font-weight: bold; border: none; background: transparent; color: #1565C0;")
        name_btn.setCursor(Qt.PointingHandCursor)
        name_btn.clicked.connect(lambda checked=False, target_id=n_info['id']: self.render_tree(target_id))
        layout.addWidget(name_btn)

        if subtitle:
            sub_lbl = QLabel(f"<i>{subtitle}</i>")
            sub_lbl.setStyleSheet("color: #777; font-size: 10px; border: none;")
            layout.addWidget(sub_lbl)

        age_text = f"Возраст: {n_info['age']} лет" if n_info['is_alive'] else f"Умер в {n_info['age']} л."
        layout.addWidget(QLabel(age_text))

        pheno_text = f"Глаза: {n_info['eye_color']} | Волосы: {n_info['hair_color']}"
        lbl_pheno = QLabel(pheno_text)
        lbl_pheno.setStyleSheet("font-size: 10px; color: #555; border: none;")
        layout.addWidget(lbl_pheno)

        lbl_prof = QLabel(f"{n_info['profession']} ({n_info['height_cm']} см)")
        lbl_prof.setStyleSheet("font-size: 10px; color: #666; border: none;")
        layout.addWidget(lbl_prof)

        layout.addStretch()
        return card
