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
    t_eval = np.linspace(0.0, config.t_end, config.n_points)

    def rhs(t, y):
        return [(config.T_target - y[0]) / config.tau]

    sol = solve_ivp(
        rhs, (0.0, config.t_end), [config.T0],
        t_eval=t_eval, method="RK45", rtol=1e-8, atol=1e-11,
    )

    dT = config.T_target - config.T0
    if abs(dT) > 1e-9:
        approach = (sol.y[0] - config.T0) / dT * 100.0
    else:
        approach = np.full_like(sol.t, 100.0)

    return {
        "t": sol.t,
        "temperature": sol.y[0],
        "approach": approach,
        "success": sol.success,
        "message": sol.message,
    }
