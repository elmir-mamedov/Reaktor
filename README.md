# Reaktor

A desktop GUI application for simulating chemical reactors. Define custom reactions with arbitrary stoichiometry and kinetics, then solve the resulting ODEs and visualize the results.

Inspired by Aspen PLUS.

---

## Features

- **Flowsheet editor** — drag-and-drop reactors onto a zoomable/pannable canvas
- **Two reactor types** — Batch Reactor and CSTR (Continuous Stirred Tank Reactor)
- **Custom reactions** — define any number of species with arbitrary stoichiometry and roles (reactant/product)
- **Reaction kinetics** — simple rate constant or full Arrhenius equation (`k = A·exp(-Ea/RT)`)
- **ODE solver** — powered by SciPy's RK45 integrator with tight tolerances
- **Interactive results** — concentration profiles, conversion curves, and a tabular data view

---

## Reactor Models

### Batch Reactor

Closed system — all reactants are loaded at once. The solver integrates the material balance over time:

```
dC_i/dt = ν_i · r
r = k · ∏ C_j^ν_j   (product over all reactants j)
```

### CSTR

Continuous flow with a residence time `τ`. The solver finds the transient approach to steady state:

```
dC_i/dt = (C_i,feed - C_i) / τ + ν_i · r
```

---

## Getting Started

### Prerequisites

- Python 3.14+
- [`uv`](https://github.com/astral-sh/uv) (recommended) or `pip`

### Installation

```bash
git clone https://github.com/your-username/Reaktor.git
cd Reaktor

# with uv (recommended)
uv sync

# or with pip
pip install -e .
```

### Run

```bash
python main.py
```

---

## Usage

1. **Add a reactor** — drag a Batch Reactor or CSTR from the left palette onto the canvas.
2. **Select it** — click the reactor to open the properties panel on the right.
3. **Configure the reaction** — choose a template or build a custom reaction: add species, set stoichiometry, roles, and initial/feed concentrations.
4. **Set kinetics** — enter a rate constant `k`, or enable Arrhenius kinetics and provide `A`, `Ea`, and `T`.
5. **Run** — press **Run** (or `F5`) to solve the ODEs.
6. **Inspect results** — view concentration and conversion plots in the bottom panel, or switch to the data table.

---

## Project Structure

```
Reaktor/
├── main.py                   # Application entry point
├── models/
│   ├── reaction.py           # Reaction dataclasses and validation
│   ├── batch_reactor.py      # Batch reactor ODE solver
│   └── cstr.py               # CSTR ODE solver
└── ui/
    ├── main_window.py        # Main window and layout
    ├── flowsheet_canvas.py   # Drag-drop canvas and reactor graphics
    ├── palette_panel.py      # Equipment palette
    ├── properties_panel.py   # Reactor parameter editor
    ├── results_panel.py      # Plots and data table
    └── styles.py             # Global stylesheet
```

---

## Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| PyQt6 | ≥6.7 | GUI framework |
| NumPy | ≥2.1 | Numerical arrays |
| SciPy | ≥1.14 | ODE solver |
| Matplotlib | ≥3.9 | Embedded plots |
