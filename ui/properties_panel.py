from __future__ import annotations

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QFormLayout, QLabel,
                              QDoubleSpinBox, QSpinBox, QLineEdit, QComboBox,
                              QGroupBox, QCheckBox, QPushButton,
                              QScrollArea, QFrame, QSizePolicy)
from PyQt6.QtCore import Qt, pyqtSignal

from models.reaction import ElementaryReaction, ReactionType


class PropertiesPanel(QWidget):
    """Right-hand panel: shows and edits the selected reactor's parameters."""

    run_requested = pyqtSignal(object)   # emits the BatchReactorItem

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(260)
        self.setMaximumWidth(320)
        self._item = None       # current BatchReactorItem
        self._loading = False   # suppress callbacks while populating

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Coloured header bar
        self._title = QLabel("  Properties")
        self._title.setFixedHeight(30)
        self._title.setStyleSheet(
            "background-color: #2c5f8a; color: white;"
            "font-size: 12px; font-weight: bold;")
        outer.addWidget(self._title)

        # Scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        outer.addWidget(scroll)

        content = QWidget()
        content.setStyleSheet("background-color: white;")
        scroll.setWidget(content)
        self._layout = QVBoxLayout(content)
        self._layout.setContentsMargins(10, 10, 10, 10)
        self._layout.setSpacing(10)

        # Placeholder (shown when nothing is selected)
        self._placeholder = QLabel(
            "Select a unit operation\non the flowsheet to\nview its properties.")
        self._placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._placeholder.setStyleSheet(
            "color: #95a5a6; font-size: 12px; margin: 30px 0;")
        self._layout.addWidget(self._placeholder)
        self._layout.addStretch()

        # Build all form widgets (hidden initially)
        self._form_widget = QWidget()
        self._form_widget.setVisible(False)
        self._layout.insertWidget(0, self._form_widget)
        self._build_form()

    # ── form construction ─────────────────────────────────────────────────

    def _build_form(self):
        layout = QVBoxLayout(self._form_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # — General —
        gen_grp = QGroupBox("General")
        gen_form = QFormLayout(gen_grp)
        gen_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        self._name_edit = QLineEdit()
        self._name_edit.textChanged.connect(self._on_name_changed)
        gen_form.addRow("Name:", self._name_edit)
        layout.addWidget(gen_grp)

        # — Reaction type —
        rxn_grp = QGroupBox("Reaction")
        rxn_form = QFormLayout(rxn_grp)
        rxn_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        self._type_combo = QComboBox()
        for rt in ReactionType:
            self._type_combo.addItem(rt.value, rt)
        self._type_combo.currentIndexChanged.connect(self._on_type_changed)
        rxn_form.addRow("Type:", self._type_combo)
        layout.addWidget(rxn_grp)

        # — Kinetics —
        kin_grp = QGroupBox("Kinetics")
        kin_form = QFormLayout(kin_grp)
        kin_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self._arrh_check = QCheckBox("Use Arrhenius equation")
        self._arrh_check.toggled.connect(self._on_arrhenius_toggled)
        kin_form.addRow("", self._arrh_check)

        self._k_lbl = QLabel("k (1/s):")
        self._k_spin = self._dspin(1e-9, 1e6, 0.05, 6)
        self._k_spin.setStepType(QDoubleSpinBox.StepType.AdaptiveDecimalStepType)
        kin_form.addRow(self._k_lbl, self._k_spin)
        self._k_spin.valueChanged.connect(self._update)

        self._A_lbl = QLabel("A (1/s):")
        self._A_spin = self._dspin(1.0, 1e15, 1e8, 4)
        self._A_spin.setStepType(QDoubleSpinBox.StepType.AdaptiveDecimalStepType)
        kin_form.addRow(self._A_lbl, self._A_spin)
        self._A_spin.valueChanged.connect(self._update)

        self._Ea_lbl = QLabel("Ea (J/mol):")
        self._Ea_spin = self._dspin(0.0, 500_000.0, 50_000.0, 1)
        self._Ea_spin.setStepType(QDoubleSpinBox.StepType.AdaptiveDecimalStepType)
        kin_form.addRow(self._Ea_lbl, self._Ea_spin)
        self._Ea_spin.valueChanged.connect(self._update)

        self._T_lbl = QLabel("T (K):")
        self._T_spin = self._dspin(1.0, 2000.0, 298.15, 2)
        kin_form.addRow(self._T_lbl, self._T_spin)
        self._T_spin.valueChanged.connect(self._update)

        layout.addWidget(kin_grp)

        # — Feed conditions —
        feed_grp = QGroupBox("Feed Conditions")
        feed_form = QFormLayout(feed_grp)
        feed_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self._Ca0_spin = self._dspin(1e-6, 1000.0, 1.0, 4)
        feed_form.addRow("CA₀ (mol/L):", self._Ca0_spin)
        self._Ca0_spin.valueChanged.connect(self._update)

        self._Cb0_lbl = QLabel("CB₀ (mol/L):")
        self._Cb0_spin = self._dspin(1e-6, 1000.0, 1.0, 4)
        feed_form.addRow(self._Cb0_lbl, self._Cb0_spin)
        self._Cb0_spin.valueChanged.connect(self._update)

        layout.addWidget(feed_grp)

        # — Simulation settings —
        sim_grp = QGroupBox("Simulation Settings")
        sim_form = QFormLayout(sim_grp)
        sim_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self._tend_spin = self._dspin(0.1, 1e6, 100.0, 1)
        self._tend_spin.setStepType(QDoubleSpinBox.StepType.AdaptiveDecimalStepType)
        sim_form.addRow("End time (s):", self._tend_spin)
        self._tend_spin.valueChanged.connect(self._update)

        self._npts_spin = QSpinBox()
        self._npts_spin.setRange(50, 5000)
        self._npts_spin.setValue(500)
        self._npts_spin.setSingleStep(50)
        sim_form.addRow("Points:", self._npts_spin)
        self._npts_spin.valueChanged.connect(self._update)

        layout.addWidget(sim_grp)

        # Run button
        self._run_btn = QPushButton("▶  Run Simulation")
        self._run_btn.setObjectName("run_btn")
        self._run_btn.setFixedHeight(36)
        self._run_btn.clicked.connect(self._on_run)
        layout.addWidget(self._run_btn)

        layout.addStretch()

        # Set initial visibility
        self._set_arrhenius_visible(False)
        self._set_cb0_visible(False)

    # ── public slots ──────────────────────────────────────────────────────

    def load_reactor(self, item):
        """Populate the panel from a BatchReactorItem."""
        self._loading = True
        self._item = item

        self._placeholder.setVisible(False)
        self._form_widget.setVisible(True)

        r: ElementaryReaction = item.reaction
        self._name_edit.setText(item.name)

        for i in range(self._type_combo.count()):
            if self._type_combo.itemData(i) == r.reaction_type:
                self._type_combo.setCurrentIndex(i)
                break

        self._arrh_check.setChecked(r.use_arrhenius)
        self._k_spin.setValue(r.k)
        self._A_spin.setValue(r.A_factor)
        self._Ea_spin.setValue(r.Ea)
        self._T_spin.setValue(r.T)
        self._Ca0_spin.setValue(r.Ca0)
        self._Cb0_spin.setValue(r.Cb0)
        self._tend_spin.setValue(r.t_end)
        self._npts_spin.setValue(r.n_points)

        self._set_arrhenius_visible(r.use_arrhenius)
        self._set_cb0_visible(r.reaction_type == ReactionType.SECOND_ORDER_A_B_TO_C)
        self._update_k_label(r.reaction_type)

        self._loading = False

    def clear(self):
        self._item = None
        self._form_widget.setVisible(False)
        self._placeholder.setVisible(True)

    # ── callbacks ─────────────────────────────────────────────────────────

    def _on_name_changed(self, text: str):
        if self._item and not self._loading:
            self._item.name = text
            self._item.update()

    def _on_type_changed(self, _idx: int):
        if self._loading:
            return
        rt = self._type_combo.currentData()
        self._set_cb0_visible(rt == ReactionType.SECOND_ORDER_A_B_TO_C)
        self._update_k_label(rt)
        self._update()

    def _on_arrhenius_toggled(self, checked: bool):
        self._set_arrhenius_visible(checked)
        self._update()

    def _on_run(self):
        if self._item:
            self.run_requested.emit(self._item)

    def _update(self):
        if self._item is None or self._loading:
            return
        r = self._item.reaction
        r.reaction_type = self._type_combo.currentData()
        r.k = self._k_spin.value()
        r.use_arrhenius = self._arrh_check.isChecked()
        r.A_factor = self._A_spin.value()
        r.Ea = self._Ea_spin.value()
        r.T = self._T_spin.value()
        r.Ca0 = self._Ca0_spin.value()
        r.Cb0 = self._Cb0_spin.value()
        r.t_end = self._tend_spin.value()
        r.n_points = self._npts_spin.value()
        self._item.update()   # redraw reaction label on canvas

    # ── helpers ───────────────────────────────────────────────────────────

    @staticmethod
    def _dspin(lo: float, hi: float, val: float, dec: int) -> QDoubleSpinBox:
        w = QDoubleSpinBox()
        w.setRange(lo, hi)
        w.setValue(val)
        w.setDecimals(dec)
        return w

    def _set_arrhenius_visible(self, show: bool):
        self._k_lbl.setVisible(not show)
        self._k_spin.setVisible(not show)
        self._A_lbl.setVisible(show)
        self._A_spin.setVisible(show)
        self._Ea_lbl.setVisible(show)
        self._Ea_spin.setVisible(show)
        self._T_lbl.setVisible(show)
        self._T_spin.setVisible(show)

    def _set_cb0_visible(self, show: bool):
        self._Cb0_lbl.setVisible(show)
        self._Cb0_spin.setVisible(show)

    def _update_k_label(self, rt: ReactionType):
        is_second = rt in (ReactionType.SECOND_ORDER_A_B_TO_C,
                           ReactionType.SECOND_ORDER_2A_TO_B)
        unit = "L/(mol·s)" if is_second else "1/s"
        self._k_lbl.setText(f"k ({unit}):")
        self._A_lbl.setText(f"A ({unit}):")
