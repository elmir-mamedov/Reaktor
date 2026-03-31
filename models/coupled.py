from itertools import accumulate
import numpy as np
from scipy.integrate import solve_ivp


def simulate_coupled(units, connections, t_span, t_eval):
    """
    Generic coupled ODE solver for connected unit operations.

    Parameters
    ----------
    units : list of (rhs_fn, y0, extract_outputs_fn)
        rhs_fn(t, y_local, context) -> list  — ODE right-hand side
        extract_outputs_fn(y_local) -> dict  — named outputs from this unit
    connections : list of (src_idx, out_key, dst_idx, in_key)
        Routes out_key from src unit's outputs into dst unit's context as in_key.
    t_span : (t0, t_end)
    t_eval : array of evaluation time points

    Returns
    -------
    sol     : scipy OdeResult  (sol.y contains the full combined state)
    offsets : list of start indices per unit in the combined state vector
    sizes   : list of state vector sizes per unit
    """
    sizes = [len(y0) for _, y0, _ in units]
    offsets = [0] + list(accumulate(sizes))
    y0_all = [v for _, y0, _ in units for v in y0]

    def combined_rhs(t, y_all):
        ys = [y_all[offsets[i]:offsets[i + 1]] for i in range(len(units))]
        contexts = [{} for _ in units]
        for src, out_key, dst, in_key in connections:
            _, _, extract = units[src]
            contexts[dst][in_key] = extract(ys[src])[out_key]
        dydt = []
        for i, (rhs, _, _) in enumerate(units):
            dydt.extend(rhs(t, ys[i], contexts[i]))
        return dydt

    sol = solve_ivp(
        combined_rhs, t_span, y0_all,
        t_eval=t_eval, method="RK45", rtol=1e-8, atol=1e-11,
    )
    return sol, offsets, sizes
