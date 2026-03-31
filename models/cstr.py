import math
import numpy as np
from scipy.integrate import solve_ivp
from typing import Dict

from models.reaction import CustomReaction


def build_rhs(reaction: CustomReaction):
    """Return (rhs_fn, y0) for standalone or coupled simulation.

    rhs_fn signature: rhs(t, y_local, context) -> list
    context keys consumed: "temperature" (K) — overrides reaction.T when provided
    """
    tau = reaction.tau
    reactants = [s for s in reaction.species if s.is_reactant]
    idx = {s.name: i for i, s in enumerate(reaction.species)}

    def rhs(t, y, context=None):
        ctx = context or {}
        T = ctx.get("temperature", reaction.T)
        if reaction.use_arrhenius or "temperature" in ctx:
            k = reaction.A_factor * math.exp(-reaction.Ea / (reaction.R * T))
        else:
            k = reaction.k
        r = k
        for s in reactants:
            r *= max(y[idx[s.name]], 0.0) ** s.stoich
        dydt = []
        for s in reaction.species:
            sign = -1.0 if s.is_reactant else 1.0
            dydt.append((s.C_feed - y[idx[s.name]]) / tau + sign * s.stoich * r)
        return dydt

    y0 = [s.C0 for s in reaction.species]
    return rhs, y0


def extract_outputs(y, reaction: CustomReaction) -> dict:
    """Named outputs from CSTR state vector."""
    idx = {s.name: i for i, s in enumerate(reaction.species)}
    return {"concentrations": {s.name: float(y[idx[s.name]]) for s in reaction.species}}


def simulate_cstr(reaction: CustomReaction) -> Dict:
    """
    Simulate transient approach to steady state in a CSTR.

    Material balance per species:
        dC_i/dt = (C_i_feed - C_i) / tau  +  r_i

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
    ref = reactants[0]
    Ca_feed = ref.C_feed
    Ca_idx = idx[ref.name]
    conversion = (1.0 - sol.y[Ca_idx] / Ca_feed) if Ca_feed > 0 else np.zeros_like(sol.t)

    return {
        "t": sol.t,
        "concentrations": {s.name: sol.y[idx[s.name]] for s in reaction.species},
        "conversion": conversion,
        "success": sol.success,
        "message": sol.message,
    }
