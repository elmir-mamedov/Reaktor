from __future__ import annotations

import numpy as np
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QTabWidget,
                              QTableWidget, QTableWidgetItem, QHeaderView,
                              QLabel, QFrame)
from PyQt6.QtCore import Qt

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure

_COLORS = ["#2980b9", "#e74c3c", "#27ae60", "#f39c12", "#8e44ad"]


class _Canvas(FigureCanvasQTAgg):
    """Thin wrapper around a matplotlib Figure embedded in Qt."""

    def __init__(self, parent=None):
        fig = Figure(figsize=(5, 3), dpi=100, facecolor="white")
        fig.subplots_adjust(left=0.12, right=0.97, top=0.90, bottom=0.16)
        super().__init__(fig)
        self.setParent(parent)
        self.fig = fig
        self._ax = None
        self._show_placeholder()

    def _show_placeholder(self):
        self.fig.clear()
        ax = self.fig.add_subplot(111)
        ax.text(0.5, 0.5, "Run a simulation to see results",
                ha="center", va="center", transform=ax.transAxes,
                color="#95a5a6", fontsize=11)
        ax.axis("off")
        self.draw_idle()

    def plot_concentrations(self, results: dict):
        self.fig.clear()
        ax = self.fig.add_subplot(111)
        t = results["t"]
        for i, (sp, conc) in enumerate(results["concentrations"].items()):
            ax.plot(t, conc, color=_COLORS[i % len(_COLORS)],
                    linewidth=2, label=f"$C_{{{sp}}}$")
        ax.set_xlabel("Time (s)", fontsize=10)
        ax.set_ylabel("Concentration (mol/L)", fontsize=10)
        ax.set_title("Concentration vs. Time", fontsize=11, fontweight="bold")
        ax.legend(fontsize=9, framealpha=0.9)
        ax.set_xlim(0, t[-1])
        ax.set_ylim(bottom=0)
        ax.grid(True, alpha=0.3)
        ax.set_facecolor("#fafafa")
        self.fig.tight_layout()
        self.draw_idle()

    def plot_conversion(self, results: dict):
        self.fig.clear()
        ax = self.fig.add_subplot(111)
        t = results["t"]
        X = results["conversion"] * 100
        ax.plot(t, X, color="#27ae60", linewidth=2)
        ax.fill_between(t, X, alpha=0.12, color="#27ae60")
        ax.set_xlabel("Time (s)", fontsize=10)
        ax.set_ylabel("Conversion $X_A$ (%)", fontsize=10)
        ax.set_title("Conversion vs. Time", fontsize=11, fontweight="bold")
        ax.set_xlim(0, t[-1])
        ax.set_ylim(0, 105)
        ax.grid(True, alpha=0.3)
        ax.set_facecolor("#fafafa")
        self.fig.tight_layout()
        self.draw_idle()

    def plot_temperature(self, results: dict):
        self.fig.clear()
        ax = self.fig.add_subplot(111)
        t = results["t"]
        T = results["temperature"]
        ax.plot(t, T, color="#e67e22", linewidth=2)
        ax.set_xlabel("Time (s)", fontsize=10)
        ax.set_ylabel("Temperature (K)", fontsize=10)
        ax.set_title("Temperature vs. Time", fontsize=11, fontweight="bold")
        ax.set_xlim(0, t[-1])
        ax.grid(True, alpha=0.3)
        ax.set_facecolor("#fafafa")
        self.fig.tight_layout()
        self.draw_idle()

    def plot_approach(self, results: dict):
        self.fig.clear()
        ax = self.fig.add_subplot(111)
        t = results["t"]
        A = results["approach"]
        ax.plot(t, A, color="#d35400", linewidth=2)
        ax.fill_between(t, A, alpha=0.12, color="#d35400")
        ax.set_xlabel("Time (s)", fontsize=10)
        ax.set_ylabel("Approach to T_target (%)", fontsize=10)
        ax.set_title("Approach to Steady State", fontsize=11, fontweight="bold")
        ax.set_xlim(0, t[-1])
        ax.set_ylim(0, 105)
        ax.grid(True, alpha=0.3)
        ax.set_facecolor("#fafafa")
        self.fig.tight_layout()
        self.draw_idle()


class ResultsPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Header bar
        header = QLabel("  Simulation Results")
        header.setFixedHeight(28)
        header.setStyleSheet(
            "background-color: #1a5276; color: white;"
            "font-size: 11px; font-weight: bold;")
        layout.addWidget(header)

        self._tabs = QTabWidget()
        layout.addWidget(self._tabs)

        self._conc_canvas = _Canvas()
        self._conv_canvas = _Canvas()
        self._table = QTableWidget()
        self._table.setAlternatingRowColors(True)
        self._table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        self._tabs.addTab(self._conc_canvas, "Concentrations")
        self._tabs.addTab(self._conv_canvas, "Conversion")
        self._tabs.addTab(self._table, "Data Table")

    def display(self, results: dict, reactor_name: str = ""):
        self._conc_canvas.plot_concentrations(results)
        self._conv_canvas.plot_conversion(results)
        self._populate_table(results)
        suffix = f" — {reactor_name}" if reactor_name else ""
        self._tabs.setTabText(0, f"Concentrations{suffix}")
        self._tabs.setTabText(1, f"Conversion{suffix}")
        self._tabs.setTabText(2, "Data Table")

    def display_heater(self, results: dict, reactor_name: str = ""):
        self._conc_canvas.plot_temperature(results)
        self._conv_canvas.plot_approach(results)
        self._populate_heater_table(results)
        suffix = f" — {reactor_name}" if reactor_name else ""
        self._tabs.setTabText(0, f"Temperature{suffix}")
        self._tabs.setTabText(1, f"Approach{suffix}")
        self._tabs.setTabText(2, "Data Table")

    def _populate_table(self, results: dict):
        t = results["t"]
        concs = results["concentrations"]
        X = results["conversion"]
        species = list(concs.keys())

        headers = ["Time (s)"] + [f"C{s} (mol/L)" for s in species] + ["XA (−)"]

        # Subsample for readability (max ~100 rows)
        step = max(1, len(t) // 100)
        idxs = list(range(0, len(t), step))
        if idxs[-1] != len(t) - 1:
            idxs.append(len(t) - 1)

        self._table.setColumnCount(len(headers))
        self._table.setRowCount(len(idxs))
        self._table.setHorizontalHeaderLabels(headers)

        for row, idx in enumerate(idxs):
            self._table.setItem(row, 0, QTableWidgetItem(f"{t[idx]:.4f}"))
            for col, sp in enumerate(species, 1):
                self._table.setItem(
                    row, col, QTableWidgetItem(f"{concs[sp][idx]:.6f}"))
            self._table.setItem(
                row, len(species) + 1, QTableWidgetItem(f"{X[idx]:.6f}"))

    def _populate_heater_table(self, results: dict):
        t = results["t"]
        T = results["temperature"]
        A = results["approach"]

        step = max(1, len(t) // 100)
        idxs = list(range(0, len(t), step))
        if idxs[-1] != len(t) - 1:
            idxs.append(len(t) - 1)

        self._table.setColumnCount(3)
        self._table.setRowCount(len(idxs))
        self._table.setHorizontalHeaderLabels(
            ["Time (s)", "Temperature (K)", "Approach (%)"])

        for row, idx in enumerate(idxs):
            self._table.setItem(row, 0, QTableWidgetItem(f"{t[idx]:.4f}"))
            self._table.setItem(row, 1, QTableWidgetItem(f"{T[idx]:.4f}"))
            self._table.setItem(row, 2, QTableWidgetItem(f"{A[idx]:.2f}"))

    def display_coupled(self, heater_results: dict, cstr_results: dict, name: str = ""):
        self._conc_canvas.plot_temperature(heater_results)
        self._conv_canvas.plot_concentrations(cstr_results)
        self._populate_coupled_table(heater_results, cstr_results)
        suffix = f" — {name}" if name else ""
        self._tabs.setTabText(0, f"Temperature{suffix}")
        self._tabs.setTabText(1, f"Concentrations{suffix}")
        self._tabs.setTabText(2, "Data Table")

    def _populate_coupled_table(self, heater_results: dict, cstr_results: dict):
        t = cstr_results["t"]
        T = heater_results["temperature"]
        concs = cstr_results["concentrations"]
        X = cstr_results["conversion"]
        species = list(concs.keys())

        headers = ["Time (s)", "T (K)"] + [f"C{s} (mol/L)" for s in species] + ["XA (−)"]

        step = max(1, len(t) // 100)
        idxs = list(range(0, len(t), step))
        if idxs[-1] != len(t) - 1:
            idxs.append(len(t) - 1)

        self._table.setColumnCount(len(headers))
        self._table.setRowCount(len(idxs))
        self._table.setHorizontalHeaderLabels(headers)

        for row, idx in enumerate(idxs):
            self._table.setItem(row, 0, QTableWidgetItem(f"{t[idx]:.4f}"))
            self._table.setItem(row, 1, QTableWidgetItem(f"{T[idx]:.4f}"))
            for col, sp in enumerate(species, 2):
                self._table.setItem(
                    row, col, QTableWidgetItem(f"{concs[sp][idx]:.6f}"))
            self._table.setItem(
                row, len(species) + 2, QTableWidgetItem(f"{X[idx]:.6f}"))
