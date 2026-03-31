from dataclasses import dataclass
import numpy as np
from scipy.integrate import solve_ivp


@dataclass
class HeaterConfig:
    T0: float = 298.15        # Initial temperature (K)
    T_target: float = 350.0   # Target steady-state temperature (K)
    tau: float = 60.0         # Thermal residence time (s)
    t_end: float = 300.0      # Simulation duration (s)
    n_points: int = 500


def build_rhs(config: HeaterConfig):
    """Return (rhs_fn, y0) for standalone or coupled simulation.

    rhs_fn signature: rhs(t, y_local, context) -> list
    """
    def rhs(t, y, context=None):
        return [(config.T_target - y[0]) / config.tau]
    return rhs, [config.T0]


def extract_outputs(y) -> dict:
    """Named outputs from heater state vector."""
    return {"temperature": float(y[0])}


def simulate_heater(config: HeaterConfig) -> dict:
    """
    Simulate a heater/cooler using a first-order dynamic model.

    dT/dt = (T_target - T) / tau

    Returns a dict with keys:
        t           - time array (s)
        temperature - temperature array (K)
        approach    - % approach to T_target (0..100)
        success     - bool
        message     - solver status message
    """
    rhs_fn, y0 = build_rhs(config)
    t_eval = np.linspace(0.0, config.t_end, config.n_points)

    sol = solve_ivp(
        lambda t, y: rhs_fn(t, y),
        (0.0, config.t_end), y0,
        t_eval=t_eval, method="RK45", rtol=1e-8, atol=1e-11,
    )

    dT = config.T_target - config.T0
    approach = (
        (sol.y[0] - config.T0) / dT * 100.0
        if abs(dT) > 1e-9
        else np.full_like(sol.t, 100.0)
    )

    return {
        "t": sol.t,
        "temperature": sol.y[0],
        "approach": approach,
        "success": sol.success,
        "message": sol.message,
    }
