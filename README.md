# Reaktor

A desktop GUI application for simulating chemical unit operations. Define custom reactions with arbitrary stoichiometry and kinetics, connect equipment on a flowsheet, and solve the resulting ODEs with full coupling between units.

---

## Features

- **Flowsheet editor** — drag-and-drop equipment onto a zoomable/pannable canvas
- **Port-based connections** — drag from an output port to an input port to create streams between units; upstream outputs are passed into downstream ODEs at every solver timestep
- **Three equipment types** — Batch Reactor, CSTR, and Heater/Cooler
- **Custom reactions** — define any number of species with arbitrary stoichiometry and roles (reactant/product)
- **Reaction kinetics** — simple rate constant or full Arrhenius equation (`k = A·exp(-Ea/RT)`)
- **Coupled simulation** — connecting a Heater to a CSTR runs a single combined ODE system; the heater's outlet temperature drives the CSTR's Arrhenius kinetics
- **ODE solver** — powered by SciPy's RK45 integrator with tight tolerances
- **Interactive results** — concentration profiles, conversion curves, temperature profiles, and a tabular data view

---

## Equipment Models

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

### Heater / Cooler

First-order approach to a target temperature with time constant `τ`:

```
dT/dt = (T_target - T) / τ
```

When a Heater is connected to a CSTR, the outlet temperature is passed into the CSTR's rate expression at every timestep, making `k` temperature-dependent via the Arrhenius equation.

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

1. **Add equipment** — drag a Batch Reactor, CSTR, or Heater/Cooler from the left palette onto the canvas.
2. **Select it** — click the item to open the properties panel on the right.
3. **Configure** — choose a template or build a custom reaction; set species, stoichiometry, concentrations, and kinetics.
4. **Connect units** — hover over a unit to reveal its port dots. Drag from an output port (right side) to an input port (left side) of another unit to create a stream.
5. **Run** — press **Run** (or `F5`) to solve the ODEs. A connected pair runs as a single coupled system.
6. **Inspect results** — view plots and data in the bottom panel.

---

## Project Structure

```
Reaktor/
├── main.py                   # Application entry point
├── models/
│   ├── reaction.py           # Reaction dataclasses and validation
│   ├── batch_reactor.py      # Batch reactor ODE solver
│   ├── cstr.py               # CSTR ODE solver
│   ├── heater.py             # Heater/Cooler ODE solver
│   └── coupled.py            # Generic coupled ODE solver
└── ui/
    ├── main_window.py        # Main window and layout
    ├── flowsheet_canvas.py   # Drag-drop canvas, reactor graphics, streams
    ├── palette_panel.py      # Equipment palette
    ├── properties_panel.py   # Equipment parameter editor
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