import numpy as np
from scipy.integrate import solve_ivp
from typing import Dict

from models.reaction import CustomReaction


def build_rhs(reaction: CustomReaction):
    """Return (rhs_fn, y0) for standalone or coupled simulation.

    rhs_fn signature: rhs(t, y_local, context) -> list
    context is accepted but unused (batch reactor has no flow inputs).
    """
    reactants = [s for s in reaction.species if s.is_reactant]
    n = len(reaction.species)
    idx = {s.name: i for i, s in enumerate(reaction.species)}

    def rhs(t, y, context=None):
        k = reaction.effective_k()
        r = k
        for s in reactants:
            r *= max(y[idx[s.name]], 0.0) ** s.stoich
        dydt = [0.0] * n
        for s in reaction.species:
            sign = -1.0 if s.is_reactant else 1.0
            dydt[idx[s.name]] = sign * s.stoich * r
        return dydt

    y0 = [s.C0 for s in reaction.species]
    return rhs, y0


def extract_outputs(y, reaction: CustomReaction) -> dict:
    """Named outputs from batch reactor state vector."""
    idx = {s.name: i for i, s in enumerate(reaction.species)}
    return {"concentrations": {s.name: float(y[idx[s.name]]) for s in reaction.species}}


def simulate(reaction: CustomReaction) -> Dict:
    """
    Simulate a batch reactor for the given reaction.

    Returns a dict with keys:
        t              - time array (s)
        concentrations - dict mapping species label -> concentration array (mol/L)
        conversion     - fractional conversion of the first reactant (0..1)
        success        - bool
        message        - solver status message
    """
    rhs_fn, y0 = build_rhs(reaction)
    t_span = (0.0, reaction.t_end)
    t_eval = np.linspace(0.0, reaction.t_end, reaction.n_points)

    sol = solve_ivp(
        lambda t, y: rhs_fn(t, y),
        t_span, y0, t_eval=t_eval,
        method="RK45", rtol=1e-8, atol=1e-11,
    )

    reactants = [s for s in reaction.species if s.is_reactant]
    idx = {s.name: i for i, s in enumerate(reaction.species)}
    Ca0 = reactants[0].C0
    Ca_idx = idx[reactants[0].name]
    conversion = (1.0 - sol.y[Ca_idx] / Ca0) if Ca0 > 0 else np.zeros_like(sol.t)

    return {
        "t": sol.t,
        "concentrations": {s.name: sol.y[idx[s.name]] for s in reaction.species},
        "conversion": conversion,
        "success": sol.success,
        "message": sol.message,
    }
