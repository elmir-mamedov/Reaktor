from PyQt6.QtWidgets import (QMainWindow, QDockWidget, QSplitter,
                              QStatusBar, QLabel, QMessageBox, QToolBar)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QAction

from ui.palette_panel import PalettePanel
from ui.flowsheet_canvas import FlowsheetScene, FlowsheetView, BatchReactorItem
from ui.properties_panel import PropertiesPanel
from ui.results_panel import ResultsPanel
from models.batch_reactor import simulate


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
            "Drag a Batch Reactor from the Equipment palette onto the flowsheet.", 6000)

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
        self._props.load_reactor(item)
        self._tb_info.setText(f"  Selected: {item.name}")

    def _on_reactor_deselected(self):
        self._props.clear()
        self._tb_info.setText("  No reactor selected")

    def _run_selected(self):
        items = [i for i in self._scene.selectedItems()
                 if isinstance(i, BatchReactorItem)]
        if not items:
            self._statusbar.showMessage(
                "Select a reactor on the flowsheet first, then press Run.", 4000)
            return
        self._run_reactor(items[0])

    def _run_reactor(self, item: BatchReactorItem):
        from models.reaction import validate
        err = validate(item.reaction)
        if err:
            QMessageBox.warning(self, "Invalid Reaction", err)
            return

        self._statusbar.showMessage(f"Running {item.name}…")
        try:
            results = simulate(item.reaction)
            if not results["success"]:
                self._statusbar.showMessage(
                    f"Solver warning for {item.name}: {results['message']}", 6000)

            self._results.display(results, item.name)

            reactants = [s for s in item.reaction.species if s.is_reactant]
            ref = reactants[0].name if reactants else "A"

            X_final = float(results["conversion"][-1]) * 100
            msg = (f"{item.name}  |  Final conversion X{ref} = {X_final:.2f}%  "
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
            "<p>A batch reactor process simulator inspired by Aspen PLUS.</p>"
            "<p>Define any reaction with custom stoichiometry and optional "
            "Arrhenius kinetics. ODEs are solved with SciPy's RK45.</p>"
            "<p><b>Built with:</b> Python · PyQt6 · NumPy · SciPy · Matplotlib</p>")
