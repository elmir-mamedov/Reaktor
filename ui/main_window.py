from PyQt6.QtWidgets import (QMainWindow, QDockWidget, QSplitter,
                              QStatusBar, QLabel, QMessageBox, QToolBar)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QAction

from ui.palette_panel import PalettePanel
from ui.flowsheet_canvas import (FlowsheetScene, FlowsheetView,
                                  BatchReactorItem, CSTRReactorItem,
                                  HeaterCoolerItem, FlashSeparatorItem)
from ui.properties_panel import PropertiesPanel
from ui.results_panel import ResultsPanel
from models.batch_reactor import simulate
from models.cstr import simulate_cstr


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Reaktor — Unit Processing Simulator")
        self.resize(1400, 900)
        self.setMinimumSize(1000, 680)

        self._build_scene()
        self._build_toolbar()
        self._build_central()
        self._build_docks()
        self._build_statusbar()
        self._connect()

        self._statusbar.showMessage(
            "Drag a Batch Reactor or CSTR from the Equipment palette onto the flowsheet.", 6000)

    # ── construction ──────────────────────────────────────────────────────

    def _build_scene(self):
        self._scene = FlowsheetScene()
        self._canvas = FlowsheetView(self._scene)

    def _build_toolbar(self):
        tb = QToolBar("Main")
        tb.setMovable(False)
        tb.setIconSize(QSize(16, 16))
        self.addToolBar(tb)

        run_act = QAction("▶  Run  (F5)", self)
        run_act.setShortcut("F5")
        run_act.triggered.connect(self._run_selected)
        tb.addAction(run_act)

        tb.addSeparator()

        fit_act = QAction("⊞  Fit View  (F)", self)
        fit_act.triggered.connect(self._fit_view)
        tb.addAction(fit_act)

        clear_act = QAction("✕  Clear Canvas", self)
        clear_act.triggered.connect(self._clear_canvas)
        tb.addAction(clear_act)

        tb.addSeparator()

        self._tb_info = QLabel("  No reactor selected")
        self._tb_info.setStyleSheet("color: #636e72; font-size: 11px;")
        tb.addWidget(self._tb_info)

        self._build_menu()

    def _build_menu(self):
        mb = self.menuBar()

        file_m = mb.addMenu("File")
        new_a = QAction("New Simulation", self)
        new_a.setShortcut("Ctrl+N")
        new_a.triggered.connect(self._new_simulation)
        file_m.addAction(new_a)
        file_m.addSeparator()
        quit_a = QAction("Exit", self)
        quit_a.setShortcut("Ctrl+Q")
        quit_a.triggered.connect(self.close)
        file_m.addAction(quit_a)

        sim_m = mb.addMenu("Simulate")
        run_a2 = QAction("Run Active Reactor", self)
        run_a2.setShortcut("F5")
        run_a2.triggered.connect(self._run_selected)
        sim_m.addAction(run_a2)

        view_m = mb.addMenu("View")
        fit_a2 = QAction("Fit All", self)
        fit_a2.setShortcut("Ctrl+F")
        fit_a2.triggered.connect(self._fit_view)
        view_m.addAction(fit_a2)

        help_m = mb.addMenu("Help")
        about_a = QAction("About Reaktor", self)
        about_a.triggered.connect(self._show_about)
        help_m.addAction(about_a)

    def _build_central(self):
        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.addWidget(self._canvas)

        self._results = ResultsPanel()
        self._results.setMinimumHeight(180)
        splitter.addWidget(self._results)
        splitter.setSizes([620, 220])
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 0)

        self.setCentralWidget(splitter)

    def _build_docks(self):
        # Left: equipment palette
        palette_dock = QDockWidget("Equipment", self)
        palette_dock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea)
        palette_dock.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable |
            QDockWidget.DockWidgetFeature.DockWidgetFloatable)
        self._palette = PalettePanel()
        palette_dock.setWidget(self._palette)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, palette_dock)

        # Right: properties
        props_dock = QDockWidget("Properties", self)
        props_dock.setAllowedAreas(Qt.DockWidgetArea.RightDockWidgetArea)
        props_dock.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable |
            QDockWidget.DockWidgetFeature.DockWidgetFloatable)
        self._props = PropertiesPanel()
        props_dock.setWidget(self._props)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, props_dock)

        # Enforce initial widths
        self.resizeDocks([palette_dock], [160], Qt.Orientation.Horizontal)
        self.resizeDocks([props_dock], [290], Qt.Orientation.Horizontal)

    def _build_statusbar(self):
        self._statusbar = QStatusBar()
        self.setStatusBar(self._statusbar)

    # ── signal connections ────────────────────────────────────────────────

    def _connect(self):
        self._scene.reactor_selected.connect(self._on_reactor_selected)
        self._scene.reactor_deselected.connect(self._on_reactor_deselected)
        self._props.run_requested.connect(self._run_reactor)

    # ── slots ─────────────────────────────────────────────────────────────

    def _on_reactor_selected(self, item: BatchReactorItem):
        upstream = self._scene.get_upstream_heater(item) if isinstance(item, CSTRReactorItem) else None
        self._props.load_reactor(item, upstream_heater=upstream)
        self._tb_info.setText(f"  Selected: {item.name}")
        if item._last_results is not None:
            kind, *data = item._last_results
            if kind == "reactor":
                self._results.display(data[0], item.name)
            elif kind == "heater":
                self._results.display_heater(data[0], item.name)
            elif kind == "coupled":
                self._results.display_coupled(data[0], data[1], item.name)
            elif kind == "flash":
                self._results.display_flash(data[0], item.name)

    def _on_reactor_deselected(self):
        self._props.clear()
        self._tb_info.setText("  No reactor selected")

    def _run_selected(self):
        self._run_all()

    def _run_all(self):
        """Run every block on the canvas. Heaters that feed a CSTR are skipped
        (they are re-run automatically as part of the coupled simulation)."""
        all_items = [i for i in self._scene.items()
                     if isinstance(i, (BatchReactorItem, CSTRReactorItem,
                                       HeaterCoolerItem, FlashSeparatorItem))]
        if not all_items:
            self._statusbar.showMessage("No blocks on the canvas to run.", 4000)
            return

        connected_heaters = {s.source for s in self._scene._streams
                             if isinstance(s.source, HeaterCoolerItem)}

        ordered = (
            [i for i in all_items if isinstance(i, HeaterCoolerItem) and i not in connected_heaters] +
            [i for i in all_items if isinstance(i, BatchReactorItem)] +
            [i for i in all_items if isinstance(i, CSTRReactorItem)] +
            [i for i in all_items if isinstance(i, FlashSeparatorItem)]
        )

        for item in ordered:
            self._run_reactor(item)

        self._statusbar.showMessage(
            f"All {len(ordered)} block(s) simulated.", 5000)

    def _run_reactor(self, item):
        # ── Flash Separator path ──────────────────────────────────────────
        if isinstance(item, FlashSeparatorItem):
            from models.flash import simulate_flash
            upstream_cstr = self._scene.get_upstream_cstr(item)
            if upstream_cstr is None:
                QMessageBox.warning(self, "No Feed",
                                    f"{item.name} has no upstream CSTR connected.")
                return
            self._statusbar.showMessage(f"Running {item.name}…")
            try:
                cstr_results = simulate_cstr(upstream_cstr.reaction)
                flash_results = simulate_flash(
                    item.config,
                    cstr_results["concentrations"],
                    cstr_results["t"],
                    feed_Q=upstream_cstr.reaction.Q,
                )
                if not flash_results["success"]:
                    self._statusbar.showMessage(
                        f"Flash warning for {item.name}: {flash_results['message']}", 6000)
                item._last_results = ("flash", flash_results)
                upstream_cstr._last_results = ("reactor", cstr_results)
                self._results.display_flash(flash_results, item.name)
                psi_final = float(flash_results["psi"][-1])
                self._statusbar.showMessage(
                    f"{item.name}  |  ψ_final = {psi_final:.4f}"
                    f"  |  T = {item.config.T:.1f} K  |  P = {item.config.P:.3f} bar")
                self._tb_info.setText(f"  {item.name}  •  ψ = {psi_final:.3f}")
            except Exception as exc:
                QMessageBox.critical(self, "Simulation Error",
                                     f"Simulation failed for {item.name}:\n\n{exc}")
                self._statusbar.showMessage(f"Error: {exc}", 6000)
            return

        # ── Heater/Cooler path ────────────────────────────────────────────
        if isinstance(item, HeaterCoolerItem):
            from models.heater import simulate_heater
            self._statusbar.showMessage(f"Running {item.name}…")
            try:
                results = simulate_heater(item.config)
                if not results["success"]:
                    self._statusbar.showMessage(
                        f"Solver warning for {item.name}: {results['message']}", 6000)
                item._last_results = ("heater", results)
                self._results.display_heater(results, item.name)
                T_final = float(results["temperature"][-1])
                msg = (f"{item.name}  |  T_final = {T_final:.2f} K"
                       f"  |  T_target = {item.config.T_target:.2f} K"
                       f"  |  Solver: {results['message']}")
                self._statusbar.showMessage(msg)
                self._tb_info.setText(f"  {item.name}  •  T = {T_final:.2f} K")
            except Exception as exc:
                QMessageBox.critical(self, "Simulation Error",
                                     f"Simulation failed for {item.name}:\n\n{exc}")
                self._statusbar.showMessage(f"Error: {exc}", 6000)
            return

        # ── Reactor path ──────────────────────────────────────────────────
        from models.reaction import validate
        err = validate(item.reaction)
        if err:
            QMessageBox.warning(self, "Invalid Reaction", err)
            return

        self._statusbar.showMessage(f"Running {item.name}…")
        try:
            if isinstance(item, CSTRReactorItem):
                upstream = self._scene.get_upstream_heater(item)
                if upstream is not None:
                    import numpy as np
                    from models.coupled import simulate_coupled
                    from models.heater import build_rhs as h_rhs, extract_outputs as h_out
                    from models.cstr import build_rhs as c_rhs, extract_outputs as c_out

                    h_fn, h_y0 = h_rhs(upstream.config)
                    c_fn, c_y0 = c_rhs(item.reaction)
                    units = [
                        (h_fn, h_y0, h_out),
                        (c_fn, c_y0, lambda y: c_out(y, item.reaction)),
                    ]
                    connections = [(0, "temperature", 1, "temperature")]
                    t_end = max(upstream.config.t_end, item.reaction.t_end)
                    n_pts = max(upstream.config.n_points, item.reaction.n_points)
                    t_eval = np.linspace(0.0, t_end, n_pts)
                    sol, offsets, sizes = simulate_coupled(
                        units, connections, (0.0, t_end), t_eval)

                    h_y = sol.y[offsets[0]:offsets[1]]
                    c_y = sol.y[offsets[1]:offsets[2]]
                    idx = {s.name: i for i, s in enumerate(item.reaction.species)}
                    reactants = [s for s in item.reaction.species if s.is_reactant]
                    ref = reactants[0]
                    Ca_feed = ref.C_feed
                    Ca_idx = idx[ref.name]
                    conversion = (1.0 - c_y[Ca_idx] / Ca_feed) if Ca_feed > 0 else np.zeros_like(sol.t)

                    heater_results = {
                        "t": sol.t,
                        "temperature": h_y[0],
                        "approach": (h_y[0] - upstream.config.T0) / (upstream.config.T_target - upstream.config.T0) * 100
                        if abs(upstream.config.T_target - upstream.config.T0) > 1e-9
                        else np.full_like(sol.t, 100.0),
                        "success": sol.success,
                        "message": sol.message,
                    }
                    cstr_concentrations = {s.name: c_y[idx[s.name]] for s in item.reaction.species}
                    from models.streams import build_single_pass_streams
                    cstr_results = {
                        "t": sol.t,
                        "concentrations": cstr_concentrations,
                        "conversion": conversion,
                        "streams": build_single_pass_streams(
                            item.reaction.species, item.reaction.Q, sol.t, cstr_concentrations
                        ),
                        "Q": item.reaction.Q,
                        "success": sol.success,
                        "message": sol.message,
                    }

                    if not sol.success:
                        self._statusbar.showMessage(
                            f"Solver warning for {item.name}: {sol.message}", 6000)

                    item._last_results = ("coupled", heater_results, cstr_results)
                    upstream._last_results = ("heater", heater_results)
                    self._results.display_coupled(heater_results, cstr_results, item.name)
                    X_final = float(conversion[-1]) * 100
                    ref_name = ref.name
                    msg = (f"{item.name} (coupled)  |  X{ref_name} = {X_final:.2f}%"
                           f"  |  T_final = {float(h_y[0, -1]):.2f} K"
                           f"  |  Solver: {sol.message}")
                    self._statusbar.showMessage(msg)
                    self._tb_info.setText(f"  {item.name}  •  X{ref_name} = {X_final:.2f}%")
                    return

                results = simulate_cstr(item.reaction)
                result_label = "Steady-state conversion"
            else:
                results = simulate(item.reaction)
                result_label = "Final conversion"

            if not results["success"]:
                self._statusbar.showMessage(
                    f"Solver warning for {item.name}: {results['message']}", 6000)

            item._last_results = ("reactor", results)
            self._results.display(results, item.name)

            reactants = [s for s in item.reaction.species if s.is_reactant]
            ref = reactants[0].name if reactants else "A"

            X_final = float(results["conversion"][-1]) * 100
            msg = (f"{item.name}  |  {result_label} X{ref} = {X_final:.2f}%  "
                   f"|  Solver: {results['message']}")
            self._statusbar.showMessage(msg)
            self._tb_info.setText(
                f"  {item.name}  •  X{ref} = {X_final:.2f}%")

        except Exception as exc:
            QMessageBox.critical(self, "Simulation Error",
                                 f"Simulation failed for {item.name}:\n\n{exc}")
            self._statusbar.showMessage(f"Error: {exc}", 6000)

    def _new_simulation(self):
        reply = QMessageBox.question(
            self, "New Simulation",
            "Clear the flowsheet and start a new simulation?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self._clear_canvas()

    def _clear_canvas(self):
        for item in list(self._scene.items()):
            self._scene.removeItem(item)
        self._scene._counter = 0
        self._props.clear()
        self._tb_info.setText("  No reactor selected")
        self._statusbar.showMessage("Flowsheet cleared.", 3000)

    def _fit_view(self):
        br = self._scene.itemsBoundingRect()
        if not br.isNull():
            self._canvas.fitInView(
                br.adjusted(-80, -80, 80, 80),
                Qt.AspectRatioMode.KeepAspectRatio)

    def _show_about(self):
        QMessageBox.about(
            self, "About Reaktor",
            "<h3>Reaktor v1.0</h3>"
            "<p>A desktop simulator for chemical unit operations.</p>"
            "<p>Define reactions with custom stoichiometry and Arrhenius kinetics. "
            "Connect units on a flowsheet for coupled dynamic simulation. "
            "ODEs are solved with SciPy's RK45.</p>"
            "<p><b>Built with:</b> Python · PyQt6 · NumPy · SciPy · Matplotlib</p>")
