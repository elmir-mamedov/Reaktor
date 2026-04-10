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
        self._dark = False
        self._show_placeholder()

    def set_dark_mode(self, enabled: bool) -> None:
        self._dark = enabled
        fig_bg = "#000000" if enabled else "white"
        self.fig.set_facecolor(fig_bg)
        for ax in self.fig.get_axes():
            self._apply_ax_style(ax)
        self.draw_idle()

    def _fig_bg(self) -> str:
        return "#0f0f0f" if self._dark else "white"

    def _ax_bg(self) -> str:
        return "#111111" if self._dark else "#fafafa"

    def _text_color(self) -> str:
        return "#e8e8e8" if self._dark else "black"

    def _apply_ax_style(self, ax) -> None:
        tc = self._text_color()
        ax.set_facecolor(self._ax_bg())
        ax.tick_params(colors=tc, labelcolor=tc)
        ax.xaxis.label.set_color(tc)
        ax.yaxis.label.set_color(tc)
        ax.title.set_color(tc)
        for spine in ax.spines.values():
            spine.set_edgecolor("#3d4450" if self._dark else "#cccccc")
        legend = ax.get_legend()
        if legend:
            legend.get_frame().set_facecolor("#1a1a1a" if self._dark else "white")
            legend.get_frame().set_edgecolor("#2a2a2a" if self._dark else "#cccccc")
            for text in legend.get_texts():
                text.set_color(tc)

    def _show_placeholder(self):
        self.fig.clear()
        self.fig.set_facecolor(self._fig_bg())
        ax = self.fig.add_subplot(111)
        ax.text(0.5, 0.5, "Run a simulation to see results",
                ha="center", va="center", transform=ax.transAxes,
                color="#95a5a6", fontsize=11)
        ax.axis("off")
        ax.set_facecolor(self._ax_bg())
        self.draw_idle()

    def plot_concentrations(self, results: dict):
        self.fig.clear()
        self.fig.set_facecolor(self._fig_bg())
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
        self._apply_ax_style(ax)
        self.fig.tight_layout()
        self.draw_idle()

    def plot_conversion(self, results: dict):
        self.fig.clear()
        self.fig.set_facecolor(self._fig_bg())
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
        self._apply_ax_style(ax)
        self.fig.tight_layout()
        self.draw_idle()

    def plot_temperature(self, results: dict):
        self.fig.clear()
        self.fig.set_facecolor(self._fig_bg())
        ax = self.fig.add_subplot(111)
        t = results["t"]
        T = results["temperature"]
        ax.plot(t, T, color="#e67e22", linewidth=2)
        ax.set_xlabel("Time (s)", fontsize=10)
        ax.set_ylabel("Temperature (K)", fontsize=10)
        ax.set_title("Temperature vs. Time", fontsize=11, fontweight="bold")
        ax.set_xlim(0, t[-1])
        ax.grid(True, alpha=0.3)
        self._apply_ax_style(ax)
        self.fig.tight_layout()
        self.draw_idle()

    def plot_approach(self, results: dict):
        self.fig.clear()
        self.fig.set_facecolor(self._fig_bg())
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
        self._apply_ax_style(ax)
        self.fig.tight_layout()
        self.draw_idle()

    def plot_flash_phase(self, results: dict, phase: str):
        """Plot mole fraction vs time for vapor (y_i) or liquid (x_i)."""
        self.fig.clear()
        self.fig.set_facecolor(self._fig_bg())
        ax = self.fig.add_subplot(111)
        t = results["t"]
        data = results[phase]  # "vapor" or "liquid"
        label_char = "y" if phase == "vapor" else "x"
        for i, (sp, arr) in enumerate(data.items()):
            ax.plot(t, arr, color=_COLORS[i % len(_COLORS)],
                    linewidth=2, label=f"${label_char}_{{{sp}}}$")
        phase_name = "Vapor" if phase == "vapor" else "Liquid"
        ax.set_xlabel("Time (s)", fontsize=10)
        ax.set_ylabel(f"{phase_name} mole fraction (−)", fontsize=10)
        ax.set_title(f"{phase_name} Phase Composition", fontsize=11, fontweight="bold")
        ax.legend(fontsize=9, framealpha=0.9)
        ax.set_xlim(0, t[-1])
        ax.set_ylim(0, 1.05)
        ax.grid(True, alpha=0.3)
        self._apply_ax_style(ax)
        self.fig.tight_layout()
        self.draw_idle()

    def plot_flash_psi(self, results: dict):
        """Plot vapor fraction ψ(t)."""
        self.fig.clear()
        self.fig.set_facecolor(self._fig_bg())
        ax = self.fig.add_subplot(111)
        t = results["t"]
        psi = results["psi"]
        ax.plot(t, psi, color="#8e44ad", linewidth=2)
        ax.fill_between(t, psi, alpha=0.12, color="#8e44ad")
        ax.set_xlabel("Time (s)", fontsize=10)
        ax.set_ylabel("Vapor fraction ψ (−)", fontsize=10)
        ax.set_title("Vapor Fraction vs. Time", fontsize=11, fontweight="bold")
        ax.set_xlim(0, t[-1])
        ax.set_ylim(0, 1.05)
        ax.grid(True, alpha=0.3)
        self._apply_ax_style(ax)
        self.fig.tight_layout()
        self.draw_idle()

    def plot_absorption_profiles(self, results: dict):
        """Tab 0: y(z), y*(z) on left axis; x(z) on right axis."""
        self.fig.clear()
        self.fig.set_facecolor(self._fig_bg())
        ax = self.fig.add_subplot(111)
        z = results["z"]
        ax.plot(z, results["y"],      color="#2980b9", linewidth=2, label="y (gas)")
        ax.plot(z, results["y_star"], color="#2980b9", linewidth=1.5,
                linestyle="--", label="y* (equilibrium)")
        ax.set_xlabel("Column height z (m)", fontsize=10)
        ax.set_ylabel("Gas mole fraction y (−)", fontsize=10, color="#2980b9")
        ax.tick_params(axis="y", labelcolor="#2980b9")
        ax2 = ax.twinx()
        ax2.plot(z, results["x"], color="#e74c3c", linewidth=2, label="x (liquid)")
        ax2.set_ylabel("Liquid mole fraction x (−)", fontsize=10, color="#e74c3c")
        ax2.tick_params(axis="y", labelcolor="#e74c3c")
        ax.set_xlim(0, z[-1])
        tc = self._text_color()
        ax.set_title("Composition Profiles along Column Height",
                     fontsize=11, fontweight="bold", color=tc)
        ax.grid(True, alpha=0.3)
        self._apply_ax_style(ax)
        self._apply_ax_style(ax2)
        # Restore per-axis y-label colors (overridden by _apply_ax_style)
        ax.yaxis.label.set_color("#2980b9")
        ax2.yaxis.label.set_color("#e74c3c")
        # Combined legend
        lines1, labels1 = ax.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax.legend(lines1 + lines2, labels1 + labels2, fontsize=9, framealpha=0.9)
        self._apply_ax_style(ax)  # re-apply to update legend after it's created
        self.fig.tight_layout()
        self.draw_idle()

    def plot_hetp_profile(self, results: dict):
        """Tab 1: HOG(z) and HETP(z) with mean reference lines."""
        self.fig.clear()
        self.fig.set_facecolor(self._fig_bg())
        ax = self.fig.add_subplot(111)
        z = results["z"]
        ax.plot(z, results["HOG"],  color="#1abc9c", linewidth=2, label="HOG")
        ax.plot(z, results["HETP"], color="#f39c12", linewidth=2, label="HETP")
        ax.axhline(results["HOG_mean"],  color="#1abc9c", linewidth=1,
                   linestyle=":", label=f"HOG mean = {results['HOG_mean']:.3f} m")
        ax.axhline(results["HETP_mean"], color="#f39c12", linewidth=1,
                   linestyle=":", label=f"HETP mean = {results['HETP_mean']:.3f} m")
        ax.set_xlabel("Column height z (m)", fontsize=10)
        ax.set_ylabel("Transfer unit height (m)", fontsize=10)
        ax.set_title("HOG and HETP along Column Height", fontsize=11, fontweight="bold")
        ax.legend(fontsize=9, framealpha=0.9)
        ax.set_xlim(0, z[-1])
        ax.set_ylim(bottom=0)
        ax.grid(True, alpha=0.3)
        self._apply_ax_style(ax)
        self.fig.tight_layout()
        self.draw_idle()

    def plot_transfer_coefficients(self, results: dict):
        """Tab 2: k_G·a, k_L·a, K_OG·a along z."""
        self.fig.clear()
        self.fig.set_facecolor(self._fig_bg())
        ax = self.fig.add_subplot(111)
        z = results["z"]
        ax.plot(z, results["kG_a"],  color="#2980b9", linewidth=2, label="$k_G a$")
        ax.plot(z, results["kL_a"],  color="#e74c3c", linewidth=2, label="$k_L a$")
        ax.plot(z, results["KOG_a"], color="#27ae60", linewidth=2,
                linestyle="--", label="$K_{OG} a$")
        ax.set_xlabel("Column height z (m)", fontsize=10)
        ax.set_ylabel("Volumetric coeff. (s⁻¹)", fontsize=10)
        ax.set_title("Mass Transfer Coefficients", fontsize=11, fontweight="bold")
        ax.legend(fontsize=9, framealpha=0.9)
        ax.set_xlim(0, z[-1])
        ax.set_ylim(bottom=0)
        ax.grid(True, alpha=0.3)
        self._apply_ax_style(ax)
        self.fig.tight_layout()
        self.draw_idle()

    def plot_mass_balance(self, results: dict):
        self.fig.clear()
        self.fig.set_facecolor(self._fig_bg())
        ax = self.fig.add_subplot(111)
        t = results["t"]
        streams = results["streams"]
        if not streams:
            ax.text(0.5, 0.5, "No stream data available",
                    ha="center", va="center", transform=ax.transAxes, fontsize=11)
            self._apply_ax_style(ax)
            self.draw_idle()
            return
        species_list = list(streams[0]["flows"].keys())
        for i, sp in enumerate(species_list):
            color = _COLORS[i % len(_COLORS)]
            for stream in streams:
                if sp not in stream["flows"]:
                    continue
                is_in = stream["direction"] == "in"
                ax.plot(t, stream["flows"][sp],
                        color=color,
                        lw=1.5 if is_in else 2.0,
                        ls="--" if is_in else "-",
                        label=f"{stream['name']} – {sp}")
        ax.set_xlabel("Time (s)", fontsize=10)
        ax.set_ylabel("Molar flow (mol/s)", fontsize=10)
        ax.set_title("Mass Balance — Molar Flows", fontsize=11, fontweight="bold")
        ax.legend(fontsize=9, framealpha=0.9)
        ax.set_xlim(0, t[-1])
        ax.set_ylim(bottom=0)
        ax.grid(True, alpha=0.3)
        self._apply_ax_style(ax)
        self.fig.tight_layout()
        self.draw_idle()


class ResultsPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Header bar
        self._header = QLabel("  Simulation Results")
        self._header.setFixedHeight(28)
        self._header.setStyleSheet(
            "background-color: #1a5276; color: white;"
            "font-size: 11px; font-weight: bold;")
        layout.addWidget(self._header)

        self._tabs = QTabWidget()
        layout.addWidget(self._tabs)

        self._conc_canvas = _Canvas()
        self._conv_canvas = _Canvas()
        self._extra_canvas = _Canvas()
        self._table = QTableWidget()
        self._table.setAlternatingRowColors(True)
        self._table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        self._mb_canvas = _Canvas()

        self._tabs.addTab(self._conc_canvas, "Concentrations")
        self._tabs.addTab(self._conv_canvas, "Conversion")
        self._tabs.addTab(self._extra_canvas, "")
        self._tabs.addTab(self._table, "Data Table")
        self._tabs.addTab(self._mb_canvas, "Mass Balance")
        self._tabs.setTabVisible(2, False)
        self._tabs.setTabVisible(4, False)

    def set_dark_mode(self, enabled: bool) -> None:
        for canvas in (self._conc_canvas, self._conv_canvas,
                       self._extra_canvas, self._mb_canvas):
            canvas.set_dark_mode(enabled)
        if enabled:
            self._header.setStyleSheet(
                "background-color: #111111; color: #e8e8e8;"
                "font-size: 11px; font-weight: bold;")
        else:
            self._header.setStyleSheet(
                "background-color: #1a5276; color: white;"
                "font-size: 11px; font-weight: bold;")

    def display(self, results: dict, reactor_name: str = ""):
        self._tabs.setTabVisible(2, False)
        suffix = f" — {reactor_name}" if reactor_name else ""
        has_mb = "streams" in results
        self._tabs.setTabVisible(4, has_mb)
        self._conc_canvas.plot_concentrations(results)
        self._conv_canvas.plot_conversion(results)
        if has_mb:
            self._mb_canvas.plot_mass_balance(results)
        self._populate_table(results)
        self._tabs.setTabText(0, f"Concentrations{suffix}")
        self._tabs.setTabText(1, f"Conversion{suffix}")
        self._tabs.setTabText(3, "Data Table")
        if has_mb:
            self._tabs.setTabText(4, f"Mass Balance{suffix}")

    def display_heater(self, results: dict, reactor_name: str = ""):
        self._tabs.setTabVisible(2, False)
        self._tabs.setTabVisible(4, False)
        self._conc_canvas.plot_temperature(results)
        self._conv_canvas.plot_approach(results)
        self._populate_heater_table(results)
        suffix = f" — {reactor_name}" if reactor_name else ""
        self._tabs.setTabText(0, f"Temperature{suffix}")
        self._tabs.setTabText(1, f"Approach{suffix}")
        self._tabs.setTabText(3, "Data Table")

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
        self._tabs.setTabVisible(2, True)
        suffix = f" — {name}" if name else ""
        has_mb = "streams" in cstr_results
        self._tabs.setTabVisible(4, has_mb)
        self._conc_canvas.plot_temperature(heater_results)
        self._conv_canvas.plot_concentrations(cstr_results)
        self._extra_canvas.plot_conversion(cstr_results)
        if has_mb:
            self._mb_canvas.plot_mass_balance(cstr_results)
        self._populate_coupled_table(heater_results, cstr_results)
        self._tabs.setTabText(0, f"Temperature{suffix}")
        self._tabs.setTabText(1, f"Concentrations{suffix}")
        self._tabs.setTabText(2, f"Conversion{suffix}")
        self._tabs.setTabText(3, "Data Table")
        if has_mb:
            self._tabs.setTabText(4, f"Mass Balance{suffix}")

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

    def display_flash(self, results: dict, name: str = ""):
        suffix = f" — {name}" if name else ""
        self._tabs.setTabVisible(2, True)
        self._tabs.setTabVisible(4, True)
        self._conc_canvas.plot_flash_phase(results, "vapor")
        self._conv_canvas.plot_flash_phase(results, "liquid")
        self._extra_canvas.plot_flash_psi(results)
        self._mb_canvas.plot_mass_balance(results)
        self._populate_flash_table(results)
        self._tabs.setTabText(0, f"Vapor (y_i){suffix}")
        self._tabs.setTabText(1, f"Liquid (x_i){suffix}")
        self._tabs.setTabText(2, f"Vapor Fraction ψ{suffix}")
        self._tabs.setTabText(3, "Data Table")
        self._tabs.setTabText(4, f"Mass Balance{suffix}")

    def display_absorption(self, results: dict, name: str = ""):
        """Show steady-state absorption column results."""
        suffix = f" — {name}" if name else ""
        self._tabs.setTabVisible(2, True)
        self._tabs.setTabVisible(4, False)
        self._conc_canvas.plot_absorption_profiles(results)
        self._conv_canvas.plot_hetp_profile(results)
        self._extra_canvas.plot_transfer_coefficients(results)
        self._populate_absorption_table(results)
        self._tabs.setTabText(0, f"Profiles{suffix}")
        self._tabs.setTabText(1, f"HETP / HOG{suffix}")
        self._tabs.setTabText(2, f"Mass Transfer{suffix}")
        self._tabs.setTabText(3, "Data Table")

    def _populate_absorption_table(self, results: dict):
        """2-column scalar summary table for absorption column results."""
        rows = [
            ("NOG (−)",                          f"{results['NOG']:.4f}"),
            ("HOG mean (m)",                     f"{results['HOG_mean']:.4f}"),
            ("HETP mean (m)",                    f"{results['HETP_mean']:.4f}"),
            ("HETP bottom (m)",                  f"{results['HETP_bottom']:.4f}"),
            ("HETP top (m)",                     f"{results['HETP_top']:.4f}"),
            ("Packed bed height H (m)",          f"{results['H_col']:.4f}"),
            ("Pressure drop ΔP (Pa)",            f"{results['delta_P']:.2f}"),
            ("Liquid flow L (mol/s)",            f"{results['L_molar']:.4f}"),
            ("Liquid flow L (kg/s)",             f"{results['L_mass']:.4f}"),
            ("Superficial liquid vel. u_L (m/s)",f"{results['u_L']:.5f}"),
            ("Flooding velocity u_G,Fl (m/s)",   f"{results['u_G_Fl']:.4f}"),
            ("Operating u_G (m/s)",              f"{results['u_G_actual']:.4f}"),
            ("u_G / u_G,Fl (%)",                 f"{results['loading_frac']*100:.1f}"),
            ("L_min (mol/s)",                    f"{results['L_molar_min']:.2f}"),
            ("L operating (mol/s)",              f"{results['L_molar']:.2f}"),
            ("L / L_min factor",                 f"{results['L_factor']:.3f}"),
            ("Stripping factor λ (−)",           f"{results['lambda_val']:.4f}"),
            ("Absorption factor A (−)",          f"{results['A_abs']:.6f}"),
            ("Equilibrium slope m (−)",          f"{results['m']:.2f}"),
            ("Liquid exit x_out (−)",            f"{results['x_out']:.6f}"),
            ("Gas-side resistance (%)",          f"{results['R_gas_pct']:.2f}"),
            ("Liquid-side resistance (%)",       f"{results['R_liq_pct']:.2f}"),
        ]
        self._table.setColumnCount(2)
        self._table.setRowCount(len(rows))
        self._table.setHorizontalHeaderLabels(["Parameter", "Value"])
        for i, (param, val) in enumerate(rows):
            self._table.setItem(i, 0, QTableWidgetItem(param))
            self._table.setItem(i, 1, QTableWidgetItem(val))

    def _populate_flash_table(self, results: dict):
        t = results["t"]
        vapor = results["vapor"]
        liquid = results["liquid"]
        psi = results["psi"]
        species = list(vapor.keys())

        headers = (["Time (s)", "ψ (−)"]
                   + [f"y_{s}" for s in species]
                   + [f"x_{s}" for s in species])

        step = max(1, len(t) // 100)
        idxs = list(range(0, len(t), step))
        if idxs[-1] != len(t) - 1:
            idxs.append(len(t) - 1)

        self._table.setColumnCount(len(headers))
        self._table.setRowCount(len(idxs))
        self._table.setHorizontalHeaderLabels(headers)

        for row, idx in enumerate(idxs):
            self._table.setItem(row, 0, QTableWidgetItem(f"{t[idx]:.4f}"))
            self._table.setItem(row, 1, QTableWidgetItem(f"{psi[idx]:.4f}"))
            for col, sp in enumerate(species, 2):
                self._table.setItem(row, col, QTableWidgetItem(f"{vapor[sp][idx]:.6f}"))
            offset = 2 + len(species)
            for col, sp in enumerate(species, offset):
                self._table.setItem(row, col, QTableWidgetItem(f"{liquid[sp][idx]:.6f}"))
