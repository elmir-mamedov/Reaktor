from __future__ import annotations

import copy

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QFormLayout, QLabel,
                              QDoubleSpinBox, QSpinBox, QLineEdit, QComboBox,
                              QGroupBox, QCheckBox, QPushButton,
                              QScrollArea, QFrame, QSizePolicy,
                              QTableWidget, QTableWidgetItem, QHBoxLayout,
                              QHeaderView)
from PyQt6.QtCore import Qt, pyqtSignal

from models.reaction import CustomReaction, SpeciesEntry, TEMPLATES, CSTR_TEMPLATES


class PropertiesPanel(QWidget):
    """Right-hand panel: shows and edits the selected reactor's parameters."""

    run_requested = pyqtSignal(object)   # emits the BatchReactorItem

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(260)
        self.setMaximumWidth(320)
        self._item = None               # current flowsheet item
        self._upstream_heater = None    # HeaterCoolerItem connected upstream (CSTR only)
        self._loading = False           # suppress callbacks while populating

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
            "Select a reactor\non the flowsheet to\nview its properties.")
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
        self._reactor_type_lbl = QLabel("Batch Reactor")
        self._reactor_type_lbl.setStyleSheet(
            "color: #5d6d7e; font-size: 10px; font-style: italic;")
        gen_form.addRow("Type:", self._reactor_type_lbl)
        layout.addWidget(gen_grp)

        # — Reaction template —
        self._rxn_grp = QGroupBox("Reaction")
        rxn_form = QFormLayout(self._rxn_grp)
        rxn_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        self._template_combo = QComboBox()
        for name in TEMPLATES:
            self._template_combo.addItem(name)
        self._template_combo.currentTextChanged.connect(self._on_template_changed)
        rxn_form.addRow("Template:", self._template_combo)
        layout.addWidget(self._rxn_grp)

        # — Kinetics —
        self._kin_grp = QGroupBox("Kinetics")
        kin_form = QFormLayout(self._kin_grp)
        kin_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self._arrh_check = QCheckBox("Use Arrhenius equation")
        self._arrh_check.toggled.connect(self._on_arrhenius_toggled)
        kin_form.addRow("", self._arrh_check)

        self._k_lbl = QLabel("k:")
        self._k_spin = self._dspin(1e-9, 1e6, 0.05, 6)
        self._k_spin.setStepType(QDoubleSpinBox.StepType.AdaptiveDecimalStepType)
        kin_form.addRow(self._k_lbl, self._k_spin)
        self._k_spin.valueChanged.connect(self._update)

        self._A_lbl = QLabel("A:")
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

        layout.addWidget(self._kin_grp)

        # — Species table —
        self._species_grp = QGroupBox("Species")
        cust_layout = QVBoxLayout(self._species_grp)
        cust_layout.setContentsMargins(6, 6, 6, 6)
        cust_layout.setSpacing(6)

        self._reaction_preview = QLabel("A → B")
        self._reaction_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._reaction_preview.setStyleSheet(
            "font-size: 11px; font-weight: bold; color: #1a3a5c;"
            "background: #eaf4fb; border-radius: 4px; padding: 4px;")
        cust_layout.addWidget(self._reaction_preview)

        self._add_btn = QPushButton("+ Add Species")
        self._add_btn.setFixedHeight(30)
        self._add_btn.clicked.connect(self._add_species_row)
        self._rem_btn = QPushButton("- Remove Species")
        self._rem_btn.setFixedHeight(30)
        self._rem_btn.clicked.connect(self._remove_species_row)
        cust_layout.addWidget(self._add_btn)
        cust_layout.addWidget(self._rem_btn)

        self._species_table = QTableWidget(0, 5)
        self._species_table.setHorizontalHeaderLabels(
            ["Species", "Stoich", "Role", "C₀", "C_feed"])
        self._species_table.setColumnHidden(4, True)  # shown only for CSTR
        self._species_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch)
        self._species_table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows)
        self._species_table.setMinimumHeight(80)
        self._species_table.setMaximumHeight(200)
        self._species_table.setStyleSheet("QTableWidget::item { color: black; }")
        self._species_table.cellChanged.connect(self._on_species_changed)
        cust_layout.addWidget(self._species_table)

        layout.addWidget(self._species_grp)

        # — CSTR Settings (hidden for batch) —
        self._cstr_grp = QGroupBox("CSTR Settings")
        cstr_form = QFormLayout(self._cstr_grp)
        cstr_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        self._Q_spin = self._dspin(1e-6, 1e6, 1.0, 4)
        self._Q_spin.setStepType(QDoubleSpinBox.StepType.AdaptiveDecimalStepType)
        cstr_form.addRow("Flow rate Q (L/s):", self._Q_spin)
        self._Q_spin.valueChanged.connect(self._update)

        self._V_spin = self._dspin(1e-3, 1e8, 60.0, 2)
        self._V_spin.setStepType(QDoubleSpinBox.StepType.AdaptiveDecimalStepType)
        cstr_form.addRow("Volume V (L):", self._V_spin)
        self._V_spin.valueChanged.connect(self._update)

        self._tau_display = QLabel("60.00 s")
        self._tau_display.setStyleSheet("color: #5d6d7e; font-size: 10px;")
        cstr_form.addRow("τ = V/Q (s):", self._tau_display)
        self._cstr_grp.setVisible(False)
        layout.addWidget(self._cstr_grp)

        # — Simulation settings —
        self._sim_grp = QGroupBox("Simulation Settings")
        sim_form = QFormLayout(self._sim_grp)
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

        layout.addWidget(self._sim_grp)

        # — Heater / Cooler Settings —
        self._heater_grp = QGroupBox("Heater / Cooler")
        h_form = QFormLayout(self._heater_grp)
        h_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self._h_T0_spin = self._dspin(1.0, 5000.0, 298.15, 2)
        h_form.addRow("T\u2080 (K):", self._h_T0_spin)
        self._h_T0_spin.valueChanged.connect(self._update_heater)

        self._h_Ttarget_spin = self._dspin(1.0, 5000.0, 350.0, 2)
        h_form.addRow("T_target (K):", self._h_Ttarget_spin)
        self._h_Ttarget_spin.valueChanged.connect(self._update_heater)

        self._h_tau_spin = self._dspin(0.1, 1e6, 60.0, 1)
        self._h_tau_spin.setStepType(QDoubleSpinBox.StepType.AdaptiveDecimalStepType)
        h_form.addRow("\u03c4 (s):", self._h_tau_spin)
        self._h_tau_spin.valueChanged.connect(self._update_heater)

        self._h_tend_spin = self._dspin(0.1, 1e6, 300.0, 1)
        self._h_tend_spin.setStepType(QDoubleSpinBox.StepType.AdaptiveDecimalStepType)
        h_form.addRow("End time (s):", self._h_tend_spin)
        self._h_tend_spin.valueChanged.connect(self._update_heater)

        self._heater_grp.setVisible(False)
        layout.addWidget(self._heater_grp)

        # — Flash Separator Settings —
        self._flash_grp = QGroupBox("Flash Separator")
        flash_form = QFormLayout(self._flash_grp)
        flash_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self._flash_T_spin = self._dspin(100.0, 1000.0, 350.0, 2)
        flash_form.addRow("T (K):", self._flash_T_spin)
        self._flash_T_spin.valueChanged.connect(self._update_flash)

        self._flash_P_spin = self._dspin(0.001, 100.0, 1.013, 3)
        flash_form.addRow("P (bar):", self._flash_P_spin)
        self._flash_P_spin.valueChanged.connect(self._update_flash)

        flash_form.addRow(QLabel("Species → Antoine constants (log₁₀, bar, K):"))

        self._flash_species_table = QTableWidget(0, 4)
        self._flash_species_table.setHorizontalHeaderLabels(["Species", "A", "B", "C"])
        self._flash_species_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch)
        self._flash_species_table.setMinimumHeight(80)
        self._flash_species_table.setMaximumHeight(160)
        self._flash_species_table.setStyleSheet("QTableWidget::item { color: black; }")
        self._flash_species_table.cellChanged.connect(self._on_flash_species_changed)
        flash_form.addRow(self._flash_species_table)

        # Preset selector
        from models.antoine_data import BUILTIN_ANTOINE
        self._flash_preset_combo = QComboBox()
        self._flash_preset_combo.addItem("— Select preset —")
        for name in BUILTIN_ANTOINE:
            self._flash_preset_combo.addItem(name)
        self._flash_preset_row_spin = QSpinBox()
        self._flash_preset_row_spin.setRange(0, 99)
        self._flash_preset_row_spin.setPrefix("row ")
        preset_row = QHBoxLayout()
        preset_row.addWidget(QLabel("Fill row:"))
        preset_row.addWidget(self._flash_preset_row_spin)
        preset_row.addWidget(self._flash_preset_combo)
        flash_form.addRow(preset_row)
        self._flash_preset_combo.currentTextChanged.connect(self._on_flash_preset_selected)

        self._flash_grp.setVisible(False)
        layout.addWidget(self._flash_grp)

        # — Absorption Column Settings —
        from models.absorption import PACKING_DATABASE
        self._abs_grp = QGroupBox("Absorption Column")
        abs_main = QVBoxLayout(self._abs_grp)
        abs_main.setContentsMargins(6, 6, 6, 6)
        abs_main.setSpacing(6)

        abs_form = QFormLayout()
        abs_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self._abs_yin_spin = self._dspin(0.001, 0.999, 0.13, 4)
        abs_form.addRow("y_in (gas inlet):", self._abs_yin_spin)
        self._abs_yin_spin.valueChanged.connect(self._update_absorption)

        self._abs_yout_spin = self._dspin(1e-6, 0.5, 0.0005, 5)
        abs_form.addRow("y_out (gas outlet):", self._abs_yout_spin)
        self._abs_yout_spin.valueChanged.connect(self._update_absorption)

        self._abs_uG_spin = self._dspin(0.01, 10.0, 1.1, 3)
        abs_form.addRow("u_G (m/s):", self._abs_uG_spin)
        self._abs_uG_spin.valueChanged.connect(self._update_absorption)

        self._abs_T_spin = self._dspin(273.0, 400.0, 298.15, 2)
        abs_form.addRow("T (K):", self._abs_T_spin)
        self._abs_T_spin.valueChanged.connect(self._update_absorption)

        self._abs_P_spin = self._dspin(10000.0, 20000000.0, 101325.0, 0)
        self._abs_P_spin.setStepType(QDoubleSpinBox.StepType.AdaptiveDecimalStepType)
        abs_form.addRow("P (Pa):", self._abs_P_spin)
        self._abs_P_spin.valueChanged.connect(self._update_absorption)

        self._abs_lf_spin = self._dspin(1.01, 10.0, 1.5, 2)
        abs_form.addRow("L / L_min factor:", self._abs_lf_spin)
        self._abs_lf_spin.valueChanged.connect(self._update_absorption)

        self._abs_D_spin = self._dspin(0.05, 20.0, 1.4, 3)
        abs_form.addRow("Diameter D (m):", self._abs_D_spin)
        self._abs_D_spin.valueChanged.connect(self._update_absorption)

        self._abs_packing_combo = QComboBox()
        for pk_name in PACKING_DATABASE:
            self._abs_packing_combo.addItem(pk_name)
        abs_form.addRow("Packing:", self._abs_packing_combo)
        self._abs_packing_combo.currentTextChanged.connect(self._update_absorption)

        self._abs_npts_spin = QSpinBox()
        self._abs_npts_spin.setRange(10, 500)
        self._abs_npts_spin.setValue(100)
        self._abs_npts_spin.setSingleStep(10)
        abs_form.addRow("Grid points:", self._abs_npts_spin)
        self._abs_npts_spin.valueChanged.connect(self._update_absorption)

        abs_main.addLayout(abs_form)

        # Collapsible "Advanced / Physical Properties" sub-group
        self._abs_adv_btn = QPushButton("▶  Advanced / Physical Properties")
        self._abs_adv_btn.setCheckable(True)
        self._abs_adv_btn.setChecked(False)
        self._abs_adv_btn.setStyleSheet(
            "QPushButton { text-align: left; font-size: 10px; "
            "color: #5d6d7e; border: none; padding: 2px 0; background: transparent; }"
            "QPushButton:checked { color: #0e6655; }")
        abs_main.addWidget(self._abs_adv_btn)

        self._abs_adv_widget = QWidget()
        self._abs_adv_widget.setVisible(False)
        adv_form = QFormLayout(self._abs_adv_widget)
        adv_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self._abs_rhoL_spin = self._dspin(100.0, 3000.0, 997.0, 2)
        adv_form.addRow("ρ_L (kg/m³):", self._abs_rhoL_spin)
        self._abs_rhoL_spin.valueChanged.connect(self._update_absorption)

        self._abs_muL_spin = self._dspin(1e-6, 1.0, 8.9e-4, 6)
        adv_form.addRow("μ_L (Pa·s):", self._abs_muL_spin)
        self._abs_muL_spin.valueChanged.connect(self._update_absorption)

        self._abs_sigL_spin = self._dspin(0.001, 0.1, 0.072, 4)
        adv_form.addRow("σ_L (N/m):", self._abs_sigL_spin)
        self._abs_sigL_spin.valueChanged.connect(self._update_absorption)

        self._abs_DL_spin = self._dspin(1e-12, 1e-6, 1.92e-9, 12)
        self._abs_DL_spin.setStepType(QDoubleSpinBox.StepType.AdaptiveDecimalStepType)
        adv_form.addRow("D_L (m²/s):", self._abs_DL_spin)
        self._abs_DL_spin.valueChanged.connect(self._update_absorption)

        self._abs_DG_spin = self._dspin(1e-7, 1e-3, 1.6e-5, 9)
        self._abs_DG_spin.setStepType(QDoubleSpinBox.StepType.AdaptiveDecimalStepType)
        adv_form.addRow("D_G (m²/s):", self._abs_DG_spin)
        self._abs_DG_spin.valueChanged.connect(self._update_absorption)

        self._abs_rhoG_spin = self._dspin(0.01, 100.0, 1.185, 4)
        adv_form.addRow("ρ_G (kg/m³):", self._abs_rhoG_spin)
        self._abs_rhoG_spin.valueChanged.connect(self._update_absorption)

        self._abs_muG_spin = self._dspin(1e-6, 1e-3, 1.84e-5, 8)
        self._abs_muG_spin.setStepType(QDoubleSpinBox.StepType.AdaptiveDecimalStepType)
        adv_form.addRow("μ_G (Pa·s):", self._abs_muG_spin)
        self._abs_muG_spin.valueChanged.connect(self._update_absorption)

        self._abs_Hpx_spin = self._dspin(1e4, 1e9, 3.4e7, 0)
        self._abs_Hpx_spin.setStepType(QDoubleSpinBox.StepType.AdaptiveDecimalStepType)
        adv_form.addRow("H_px (Pa):", self._abs_Hpx_spin)
        self._abs_Hpx_spin.valueChanged.connect(self._update_absorption)

        abs_main.addWidget(self._abs_adv_widget)
        self._abs_adv_btn.toggled.connect(
            lambda checked: (
                self._abs_adv_widget.setVisible(checked),
                self._abs_adv_btn.setText(
                    ("▼  Advanced / Physical Properties"
                     if checked else "▶  Advanced / Physical Properties"))
            )
        )

        self._abs_grp.setVisible(False)
        layout.addWidget(self._abs_grp)

        # Run button
        self._run_btn = QPushButton("▶  Run Simulation")
        self._run_btn.setObjectName("run_btn")
        self._run_btn.setFixedHeight(36)
        self._run_btn.clicked.connect(self._on_run)
        layout.addWidget(self._run_btn)

        layout.addStretch()

        self._set_arrhenius_visible(False)

    # ── public slots ──────────────────────────────────────────────────────

    def load_reactor(self, item, upstream_heater=None):
        """Populate the panel from any flowsheet item (reactor or heater)."""
        from ui.flowsheet_canvas import (HeaterCoolerItem, FlashSeparatorItem,
                                         AbsorptionColumnItem)
        self._loading = True
        self._item = item
        self._upstream_heater = upstream_heater

        self._placeholder.setVisible(False)
        self._form_widget.setVisible(True)
        self._name_edit.setText(item.name)

        is_heater = isinstance(item, HeaterCoolerItem)
        is_flash = isinstance(item, FlashSeparatorItem)
        is_absorption = isinstance(item, AbsorptionColumnItem)
        is_reactor = not is_heater and not is_flash and not is_absorption

        # Show/hide groups based on item type
        self._rxn_grp.setVisible(is_reactor)
        self._kin_grp.setVisible(is_reactor)
        self._species_grp.setVisible(is_reactor)
        self._sim_grp.setVisible(is_reactor)
        self._heater_grp.setVisible(is_heater)
        self._flash_grp.setVisible(is_flash)
        self._abs_grp.setVisible(is_absorption)
        self._cstr_grp.setVisible(False)

        if is_absorption:
            self._reactor_type_lbl.setText("Absorption Column")
            cfg = item.config
            self._abs_yin_spin.setValue(cfg.y_in)
            self._abs_yout_spin.setValue(cfg.y_out)
            self._abs_uG_spin.setValue(cfg.u_G)
            self._abs_T_spin.setValue(cfg.T)
            self._abs_P_spin.setValue(cfg.P)
            self._abs_lf_spin.setValue(cfg.L_factor)
            self._abs_D_spin.setValue(cfg.D_col)
            idx = self._abs_packing_combo.findText(cfg.packing)
            if idx >= 0:
                self._abs_packing_combo.setCurrentIndex(idx)
            self._abs_npts_spin.setValue(cfg.n_points)
            self._abs_rhoL_spin.setValue(cfg.rho_L)
            self._abs_muL_spin.setValue(cfg.mu_L)
            self._abs_sigL_spin.setValue(cfg.sigma_L)
            self._abs_DL_spin.setValue(cfg.D_L)
            self._abs_DG_spin.setValue(cfg.D_G)
            self._abs_rhoG_spin.setValue(cfg.rho_G)
            self._abs_muG_spin.setValue(cfg.mu_G)
            self._abs_Hpx_spin.setValue(cfg.H_px)
        elif is_heater:
            self._reactor_type_lbl.setText("Heater / Cooler")
            cfg = item.config
            self._h_T0_spin.setValue(cfg.T0)
            self._h_Ttarget_spin.setValue(cfg.T_target)
            self._h_tau_spin.setValue(cfg.tau)
            self._h_tend_spin.setValue(cfg.t_end)
        elif is_flash:
            self._reactor_type_lbl.setText("Flash Separator")
            cfg = item.config
            self._flash_T_spin.setValue(cfg.T)
            self._flash_P_spin.setValue(cfg.P)
            # Auto-populate species from upstream CSTR if flash has none yet
            if not cfg.species and upstream_heater is not None:
                pass  # upstream_heater here is actually upstream_cstr for flash
            from models.flash import FlashSpeciesData
            if not cfg.species:
                # Check if scene has an upstream CSTR to pull species names from
                if hasattr(item, '_scene_ref') and item._scene_ref is not None:
                    upstream_cstr = item._scene_ref.get_upstream_cstr(item)
                    if upstream_cstr is not None:
                        cfg.species = [
                            FlashSpeciesData(name=s.name)
                            for s in upstream_cstr.reaction.species
                        ]
            self._load_flash_species(cfg)
        else:
            r: CustomReaction = item.reaction
            is_cstr = r.reactor_type == "cstr"
            self._reactor_type_lbl.setText("CSTR" if is_cstr else "Batch Reactor")
            self._arrh_check.setChecked(r.use_arrhenius)
            self._k_spin.setValue(r.k)
            self._A_spin.setValue(r.A_factor)
            self._Ea_spin.setValue(r.Ea)
            self._T_spin.setValue(r.T)
            self._tend_spin.setValue(r.t_end)
            self._npts_spin.setValue(r.n_points)
            self._set_arrhenius_visible(r.use_arrhenius)
            self._cstr_grp.setVisible(is_cstr)
            self._species_table.setColumnHidden(4, not is_cstr)
            if is_cstr:
                self._Q_spin.setValue(r.Q)
                self._V_spin.setValue(r.V)
                self._tau_display.setText(f"{r.V / r.Q:.2f} s")
            self._load_species(r)
            self._apply_heater_lock()

        self._loading = False

    def clear(self):
        self._item = None
        self._upstream_heater = None
        self._form_widget.setVisible(False)
        self._placeholder.setVisible(True)

    # ── callbacks ─────────────────────────────────────────────────────────

    def _on_name_changed(self, text: str):
        if self._item and not self._loading:
            self._item.name = text
            self._item.update()

    def _on_template_changed(self, name: str):
        if self._loading or self._item is None:
            return
        is_cstr = self._item.reaction.reactor_type == "cstr"
        tmpl = CSTR_TEMPLATES if is_cstr else TEMPLATES
        species = [copy.copy(s) for s in tmpl.get(name, [])]
        self._item.reaction.species = species
        self._loading = True
        self._load_species(self._item.reaction)
        self._loading = False
        self._item.update()

    def _on_arrhenius_toggled(self, checked: bool):
        self._set_arrhenius_visible(checked or self._upstream_heater is not None)
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

    def _update_absorption(self):
        if self._item is None or self._loading:
            return
        from ui.flowsheet_canvas import AbsorptionColumnItem
        if not isinstance(self._item, AbsorptionColumnItem):
            return
        cfg = self._item.config
        cfg.y_in            = self._abs_yin_spin.value()
        cfg.y_out           = self._abs_yout_spin.value()
        cfg.u_G             = self._abs_uG_spin.value()
        cfg.T               = self._abs_T_spin.value()
        cfg.P               = self._abs_P_spin.value()
        cfg.L_factor         = self._abs_lf_spin.value()
        cfg.D_col           = self._abs_D_spin.value()
        cfg.packing         = self._abs_packing_combo.currentText()
        cfg.n_points        = self._abs_npts_spin.value()
        cfg.rho_L           = self._abs_rhoL_spin.value()
        cfg.mu_L            = self._abs_muL_spin.value()
        cfg.sigma_L         = self._abs_sigL_spin.value()
        cfg.D_L             = self._abs_DL_spin.value()
        cfg.D_G             = self._abs_DG_spin.value()
        cfg.rho_G           = self._abs_rhoG_spin.value()
        cfg.mu_G            = self._abs_muG_spin.value()
        cfg.H_px            = self._abs_Hpx_spin.value()
        self._item.update()

    def _update_heater(self):
        if self._item is None or self._loading:
            return
        from ui.flowsheet_canvas import HeaterCoolerItem
        if not isinstance(self._item, HeaterCoolerItem):
            return
        cfg = self._item.config
        cfg.T0 = self._h_T0_spin.value()
        cfg.T_target = self._h_Ttarget_spin.value()
        cfg.tau = self._h_tau_spin.value()
        cfg.t_end = self._h_tend_spin.value()
        self._item.update()

    def _update_flash(self):
        if self._item is None or self._loading:
            return
        from ui.flowsheet_canvas import FlashSeparatorItem
        if not isinstance(self._item, FlashSeparatorItem):
            return
        cfg = self._item.config
        cfg.T = self._flash_T_spin.value()
        cfg.P = self._flash_P_spin.value()
        self._item.update()

    def _on_flash_species_changed(self, row: int, col: int):
        if self._loading:
            return
        from ui.flowsheet_canvas import FlashSeparatorItem
        if not isinstance(self._item, FlashSeparatorItem):
            return
        self._read_flash_species_table()

    def _on_flash_preset_selected(self, text: str):
        if self._loading or not text or text.startswith("—"):
            return
        from models.antoine_data import BUILTIN_ANTOINE
        if text not in BUILTIN_ANTOINE:
            return
        row = self._flash_preset_row_spin.value()
        if row >= self._flash_species_table.rowCount():
            return
        data = BUILTIN_ANTOINE[text]
        self._loading = True
        self._flash_species_table.setItem(row, 1, QTableWidgetItem(str(data["A"])))
        self._flash_species_table.setItem(row, 2, QTableWidgetItem(str(data["B"])))
        self._flash_species_table.setItem(row, 3, QTableWidgetItem(str(data["C"])))
        self._loading = False
        self._flash_preset_combo.setCurrentIndex(0)
        self._read_flash_species_table()

    def _load_flash_species(self, cfg):
        self._flash_species_table.blockSignals(True)
        self._flash_species_table.setRowCount(len(cfg.species))
        for i, s in enumerate(cfg.species):
            self._flash_species_table.setItem(i, 0, QTableWidgetItem(s.name))
            self._flash_species_table.setItem(i, 1, QTableWidgetItem(f"{s.A:.5f}"))
            self._flash_species_table.setItem(i, 2, QTableWidgetItem(f"{s.B:.3f}"))
            self._flash_species_table.setItem(i, 3, QTableWidgetItem(f"{s.C:.3f}"))
        self._flash_species_table.blockSignals(False)

    def _read_flash_species_table(self):
        from ui.flowsheet_canvas import FlashSeparatorItem
        from models.flash import FlashSpeciesData
        if not isinstance(self._item, FlashSeparatorItem):
            return
        species = []
        for row in range(self._flash_species_table.rowCount()):
            def _cell(r, c):
                item = self._flash_species_table.item(r, c)
                return item.text().strip() if item else ""
            name = _cell(row, 0)
            try:
                A = float(_cell(row, 1))
                B = float(_cell(row, 2))
                C = float(_cell(row, 3))
            except ValueError:
                continue
            if name:
                species.append(FlashSpeciesData(name=name, A=A, B=B, C=C))
        self._item.config.species = species

    def _update(self):
        if self._item is None or self._loading:
            return
        r = self._item.reaction
        r.k = self._k_spin.value()
        r.use_arrhenius = self._arrh_check.isChecked()
        r.A_factor = self._A_spin.value()
        r.Ea = self._Ea_spin.value()
        r.T = self._T_spin.value()
        r.t_end = self._tend_spin.value()
        r.n_points = self._npts_spin.value()
        if r.reactor_type == "cstr":
            r.Q = self._Q_spin.value()
            r.V = self._V_spin.value()
            if r.Q > 0:
                r.tau = r.V / r.Q
                self._tau_display.setText(f"{r.tau:.2f} s")
        self._item.update()

    # ── species table helpers ─────────────────────────────────────────────

    def _load_species(self, rxn: CustomReaction):
        self._species_table.setRowCount(0)
        for s in rxn.species:
            self._append_species_row(s.name, s.stoich, s.is_reactant, s.C0, s.C_feed)
        self._update_reaction_preview()

    def _append_species_row(self, name: str = "X", stoich: float = 1.0,
                             is_reactant: bool = True, C0: float = 0.0,
                             C_feed: float = 0.0):
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
        self._species_table.setItem(row, 4, QTableWidgetItem(str(C_feed)))

    def _switch_to_custom(self):
        self._loading = True
        self._template_combo.setCurrentText("Custom")
        self._loading = False

    def _next_species_name(self) -> str:
        existing = {
            self._species_table.item(r, 0).text()
            for r in range(self._species_table.rowCount())
            if self._species_table.item(r, 0)
        }
        for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            if letter not in existing:
                return letter
        return "X"

    def _add_species_row(self):
        self._switch_to_custom()
        self._species_table.blockSignals(True)
        self._append_species_row(name=self._next_species_name(), is_reactant=False)
        self._species_table.blockSignals(False)
        self._read_species_table()

    def _remove_species_row(self):
        self._switch_to_custom()
        rows = self._species_table.selectionModel().selectedRows()
        if rows:
            for idx in sorted(rows, reverse=True):
                self._species_table.removeRow(idx.row())
        elif self._species_table.rowCount() > 0:
            self._species_table.removeRow(self._species_table.rowCount() - 1)
        self._read_species_table()

    def _read_species_table(self):
        if self._item is None:
            return
        species = []
        for row in range(self._species_table.rowCount()):
            name_item = self._species_table.item(row, 0)
            stoich_item = self._species_table.item(row, 1)
            role_widget = self._species_table.cellWidget(row, 2)
            c0_item = self._species_table.item(row, 3)
            c_feed_item = self._species_table.item(row, 4)
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
            try:
                c_feed = float(c_feed_item.text()) if c_feed_item else 0.0
            except ValueError:
                c_feed = 0.0
            species.append(SpeciesEntry(name=name, stoich=stoich,
                                        is_reactant=is_reactant, C0=c0,
                                        C_feed=c_feed))
        self._item.reaction.species = species
        self._update_reaction_preview()
        self._item.update()

    def _update_reaction_preview(self):
        from ui.flowsheet_canvas import HeaterCoolerItem
        if self._item and not isinstance(self._item, HeaterCoolerItem):
            self._reaction_preview.setText(self._item.reaction.reaction_label())

    # ── helpers ───────────────────────────────────────────────────────────

    @staticmethod
    def _dspin(lo: float, hi: float, val: float, dec: int) -> QDoubleSpinBox:
        w = QDoubleSpinBox()
        w.setRange(lo, hi)
        w.setValue(val)
        w.setDecimals(dec)
        return w

    def _apply_heater_lock(self):
        """Lock/unlock the T spin based on whether an upstream heater is connected."""
        heater = self._upstream_heater
        if heater is not None:
            self._set_arrhenius_visible(True)
            self._T_spin.setValue(heater.config.T_target)
            self._T_spin.setEnabled(False)
            self._T_lbl.setText("T (K):  \u2190 Heater")
            self._T_spin.setToolTip(
                f"Controlled by connected Heater / Cooler\n"
                f"T_target = {heater.config.T_target:.2f} K")
        else:
            self._T_spin.setEnabled(True)
            self._T_lbl.setText("T (K):")
            self._T_spin.setToolTip("")

    def _set_arrhenius_visible(self, show: bool):
        effective = show or self._upstream_heater is not None
        self._k_lbl.setVisible(not effective)
        self._k_spin.setVisible(not effective)
        self._A_lbl.setVisible(effective)
        self._A_spin.setVisible(effective)
        self._Ea_lbl.setVisible(effective)
        self._Ea_spin.setVisible(effective)
        self._T_lbl.setVisible(effective)
        self._T_spin.setVisible(effective)
