from __future__ import annotations

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QFormLayout, QLabel,
                              QDoubleSpinBox, QSpinBox, QLineEdit, QComboBox,
                              QGroupBox, QCheckBox, QPushButton,
                              QScrollArea, QFrame, QSizePolicy,
                              QTableWidget, QTableWidgetItem, QHBoxLayout,
                              QHeaderView)
from PyQt6.QtCore import Qt, pyqtSignal

from models.reaction import ElementaryReaction, ReactionType, CustomReaction, SpeciesEntry


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

        # — Feed conditions (elementary reactions only) —
        self._feed_grp = QGroupBox("Feed Conditions")
        feed_form = QFormLayout(self._feed_grp)
        feed_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self._Ca0_spin = self._dspin(1e-6, 1000.0, 1.0, 4)
        feed_form.addRow("CA₀ (mol/L):", self._Ca0_spin)
        self._Ca0_spin.valueChanged.connect(self._update)

        self._Cb0_lbl = QLabel("CB₀ (mol/L):")
        self._Cb0_spin = self._dspin(1e-6, 1000.0, 1.0, 4)
        feed_form.addRow(self._Cb0_lbl, self._Cb0_spin)
        self._Cb0_spin.valueChanged.connect(self._update)

        layout.addWidget(self._feed_grp)

        # — Custom reaction species table —
        self._custom_grp = QGroupBox("Custom Reaction")
        cust_layout = QVBoxLayout(self._custom_grp)
        cust_layout.setContentsMargins(6, 6, 6, 6)
        cust_layout.setSpacing(6)

        self._custom_preview = QLabel("A → B")
        self._custom_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._custom_preview.setStyleSheet(
            "font-size: 11px; font-weight: bold; color: #1a3a5c;"
            "background: #eaf4fb; border-radius: 4px; padding: 4px;")
        cust_layout.addWidget(self._custom_preview)

        self._species_table = QTableWidget(0, 4)
        self._species_table.setHorizontalHeaderLabels(["Species", "Stoich", "Role", "C₀"])
        self._species_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch)
        self._species_table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows)
        self._species_table.setMinimumHeight(130)
        self._species_table.cellChanged.connect(self._on_species_changed)
        cust_layout.addWidget(self._species_table)

        btn_row = QHBoxLayout()
        add_btn = QPushButton("＋ Add")
        add_btn.setFixedHeight(26)
        add_btn.clicked.connect(self._add_species_row)
        rem_btn = QPushButton("－ Remove")
        rem_btn.setFixedHeight(26)
        rem_btn.clicked.connect(self._remove_species_row)
        btn_row.addWidget(add_btn)
        btn_row.addWidget(rem_btn)
        cust_layout.addLayout(btn_row)

        self._custom_grp.setVisible(False)
        layout.addWidget(self._custom_grp)

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

        self._name_edit.setText(item.name)

        if isinstance(item.reaction, CustomReaction):
            r = item.reaction
            for i in range(self._type_combo.count()):
                if self._type_combo.itemData(i) == ReactionType.CUSTOM:
                    self._type_combo.setCurrentIndex(i)
                    break
            self._arrh_check.setChecked(r.use_arrhenius)
            self._k_spin.setValue(r.k)
            self._A_spin.setValue(r.A_factor)
            self._Ea_spin.setValue(r.Ea)
            self._T_spin.setValue(r.T)
            self._tend_spin.setValue(r.t_end)
            self._npts_spin.setValue(r.n_points)
            self._set_arrhenius_visible(r.use_arrhenius)
            self._update_k_label(ReactionType.CUSTOM)
            self._feed_grp.setVisible(False)
            self._custom_grp.setVisible(True)
            self._load_custom(r)
        else:
            r: ElementaryReaction = item.reaction
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
            self._feed_grp.setVisible(True)
            self._custom_grp.setVisible(False)

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
        is_custom = (rt == ReactionType.CUSTOM)

        if is_custom and not isinstance(self._item.reaction, CustomReaction):
            old = self._item.reaction
            new_rxn = CustomReaction(
                k=old.k, use_arrhenius=old.use_arrhenius,
                A_factor=old.A_factor, Ea=old.Ea, T=old.T,
                t_end=old.t_end, n_points=old.n_points,
            )
            self._item.reaction = new_rxn
            self._loading = True
            self._load_custom(new_rxn)
            self._loading = False
        elif not is_custom and isinstance(self._item.reaction, CustomReaction):
            old = self._item.reaction
            new_rxn = ElementaryReaction(
                reaction_type=rt,
                k=old.k, use_arrhenius=old.use_arrhenius,
                A_factor=old.A_factor, Ea=old.Ea, T=old.T,
                t_end=old.t_end, n_points=old.n_points,
            )
            self._item.reaction = new_rxn

        self._custom_grp.setVisible(is_custom)
        self._feed_grp.setVisible(not is_custom)

        if not is_custom:
            self._set_cb0_visible(rt == ReactionType.SECOND_ORDER_A_B_TO_C)
            self._update_k_label(rt)
            self._update()
        else:
            self._update_k_label(rt)

        self._item.update()

    def _on_arrhenius_toggled(self, checked: bool):
        self._set_arrhenius_visible(checked)
        self._update()

    def _on_run(self):
        if self._item:
            self.run_requested.emit(self._item)

    def _on_species_changed(self, row: int, col: int):
        if self._loading:
            return
        self._read_species_table()

    def _on_role_changed(self):
        if self._loading:
            return
        self._read_species_table()

    def _update(self):
        if self._item is None or self._loading:
            return
        r = self._item.reaction
        if isinstance(r, CustomReaction):
            r.k = self._k_spin.value()
            r.use_arrhenius = self._arrh_check.isChecked()
            r.A_factor = self._A_spin.value()
            r.Ea = self._Ea_spin.value()
            r.T = self._T_spin.value()
            r.t_end = self._tend_spin.value()
            r.n_points = self._npts_spin.value()
        else:
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
        self._item.update()

    # ── species table helpers ─────────────────────────────────────────────

    def _load_custom(self, rxn: CustomReaction):
        self._species_table.blockSignals(True)
        self._species_table.setRowCount(0)
        for s in rxn.species:
            self._append_species_row(s.name, s.stoich, s.is_reactant, s.C0)
        self._species_table.blockSignals(False)
        self._update_custom_preview()

    def _append_species_row(self, name: str = "X", stoich: float = 1.0,
                             is_reactant: bool = True, C0: float = 0.0):
        row = self._species_table.rowCount()
        self._species_table.insertRow(row)
        self._species_table.setItem(row, 0, QTableWidgetItem(name))
        self._species_table.setItem(row, 1, QTableWidgetItem(str(stoich)))

        role_combo = QComboBox()
        role_combo.addItem("Reactant")
        role_combo.addItem("Product")
        role_combo.setCurrentIndex(0 if is_reactant else 1)
        role_combo.currentIndexChanged.connect(self._on_role_changed)
        self._species_table.setCellWidget(row, 2, role_combo)

        self._species_table.setItem(row, 3, QTableWidgetItem(str(C0)))

    def _add_species_row(self):
        self._species_table.blockSignals(True)
        self._append_species_row()
        self._species_table.blockSignals(False)
        self._read_species_table()

    def _remove_species_row(self):
        rows = self._species_table.selectionModel().selectedRows()
        if rows:
            for idx in sorted(rows, reverse=True):
                self._species_table.removeRow(idx.row())
        elif self._species_table.rowCount() > 0:
            self._species_table.removeRow(self._species_table.rowCount() - 1)
        self._read_species_table()

    def _read_species_table(self):
        if self._item is None or not isinstance(self._item.reaction, CustomReaction):
            return
        species = []
        for row in range(self._species_table.rowCount()):
            name_item = self._species_table.item(row, 0)
            stoich_item = self._species_table.item(row, 1)
            role_widget = self._species_table.cellWidget(row, 2)
            c0_item = self._species_table.item(row, 3)
            if name_item is None or stoich_item is None:
                continue
            name = name_item.text().strip()
            try:
                stoich = float(stoich_item.text())
            except ValueError:
                stoich = 1.0
            is_reactant = (role_widget.currentIndex() == 0) if role_widget else True
            try:
                c0 = float(c0_item.text()) if c0_item else 0.0
            except ValueError:
                c0 = 0.0
            species.append(SpeciesEntry(name=name, stoich=stoich,
                                        is_reactant=is_reactant, C0=c0))
        self._item.reaction.species = species
        self._update_custom_preview()
        self._item.update()

    def _update_custom_preview(self):
        if self._item and isinstance(self._item.reaction, CustomReaction):
            self._custom_preview.setText(self._item.reaction.reaction_label())

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
        if rt == ReactionType.CUSTOM:
            self._k_lbl.setText("k (mixed units):")
            self._A_lbl.setText("A (mixed units):")
            return
        is_second = rt in (ReactionType.SECOND_ORDER_A_B_TO_C,
                           ReactionType.SECOND_ORDER_2A_TO_B)
        unit = "L/(mol·s)" if is_second else "1/s"
        self._k_lbl.setText(f"k ({unit}):")
        self._A_lbl.setText(f"A ({unit}):")
