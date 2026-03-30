import numpy as np
from scipy.integrate import solve_ivp
from typing import Dict

from models.reaction import CustomReaction


def simulate_cstr(reaction: CustomReaction) -> Dict:
    """
    Simulate transient approach to steady state in a CSTR.

    Material balance per species:
        dC_i/dt = (C_i_feed - C_i) / tau  +  r_i

    where tau = residence time (s) and r_i uses power-law kinetics.

    Returns a dict with keys:
        t              - time array (s)
        concentrations - dict mapping species label -> concentration array (mol/L)
        conversion     - fractional conversion of the first reactant (0..1)
        success        - bool
        message        - solver status message
    """
    k = reaction.effective_k()
    tau = reaction.tau
    t_span = (0.0, reaction.t_end)
    t_eval = np.linspace(0.0, reaction.t_end, reaction.n_points)

    reactants = [s for s in reaction.species if s.is_reactant]
    n = len(reaction.species)
    idx = {s.name: i for i, s in enumerate(reaction.species)}

    def rhs(t, y):
        r = k
        for s in reactants:
            r *= max(y[idx[s.name]], 0.0) ** s.stoich
        dydt = []
        for s in reaction.species:
            sign = -1.0 if s.is_reactant else 1.0
            flow_term = (s.C_feed - y[idx[s.name]]) / tau
            rxn_term = sign * s.stoich * r
            dydt.append(flow_term + rxn_term)
        return dydt

    y0 = [s.C0 for s in reaction.species]
    sol = solve_ivp(rhs, t_span, y0, t_eval=t_eval,
                    method="RK45", rtol=1e-8, atol=1e-11)

    ref = reactants[0]
    Ca_feed = ref.C_feed
    Ca_idx = idx[ref.name]
    if Ca_feed > 0:
        conversion = 1.0 - sol.y[Ca_idx] / Ca_feed
    else:
        conversion = np.zeros_like(sol.t)

    return {
        "t": sol.t,
        "concentrations": {s.name: sol.y[idx[s.name]] for s in reaction.species},
        "conversion": conversion,
        "success": sol.success,
        "message": sol.message,
    }
