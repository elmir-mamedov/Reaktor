import numpy as np
from scipy.integrate import solve_ivp
from typing import Dict

from models.reaction import ElementaryReaction, ReactionType, CustomReaction


def simulate(reaction) -> Dict:
    """
    Simulate a batch reactor for the given elementary reaction.

    Returns a dict with keys:
        t              - time array (s)
        concentrations - dict mapping species label -> concentration array (mol/L)
        conversion     - fractional conversion of A (0..1)
        success        - bool
        message        - solver status message
    """
    if isinstance(reaction, CustomReaction):
        k = reaction.effective_k()
        t_span = (0.0, reaction.t_end)
        t_eval = np.linspace(0.0, reaction.t_end, reaction.n_points)

        reactants = [s for s in reaction.species if s.is_reactant]
        products = [s for s in reaction.species if not s.is_reactant]
        n = len(reaction.species)
        idx = {s.name: i for i, s in enumerate(reaction.species)}

        def rhs(t, y):
            r = k
            for s in reactants:
                r *= max(y[idx[s.name]], 0.0) ** s.stoich
            dydt = [0.0] * n
            for s in reactants:
                dydt[idx[s.name]] -= s.stoich * r
            for s in products:
                dydt[idx[s.name]] += s.stoich * r
            return dydt

        y0 = [s.C0 for s in reaction.species]
        sol = solve_ivp(rhs, t_span, y0, t_eval=t_eval,
                        method="RK45", rtol=1e-8, atol=1e-11)

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

    k = reaction.effective_k()
    t_span = (0.0, reaction.t_end)
    t_eval = np.linspace(0.0, reaction.t_end, reaction.n_points)

    if reaction.reaction_type == ReactionType.FIRST_ORDER_A_TO_B:
        # A → B,  −rA = k·CA
        def rhs(t, y):
            Ca, Cb = y
            r = k * max(Ca, 0.0)
            return [-r, r]

        y0 = [reaction.Ca0, 0.0]
        sol = solve_ivp(rhs, t_span, y0, t_eval=t_eval,
                        method="RK45", rtol=1e-8, atol=1e-11)
        Ca0 = reaction.Ca0
        return {
            "t": sol.t,
            "concentrations": {"A": sol.y[0], "B": sol.y[1]},
            "conversion": 1.0 - sol.y[0] / Ca0,
            "success": sol.success,
            "message": sol.message,
        }

    elif reaction.reaction_type == ReactionType.SECOND_ORDER_A_B_TO_C:
        # A + B → C,  −rA = k·CA·CB
        def rhs(t, y):
            Ca, Cb, Cc = y
            r = k * max(Ca, 0.0) * max(Cb, 0.0)
            return [-r, -r, r]

        y0 = [reaction.Ca0, reaction.Cb0, 0.0]
        sol = solve_ivp(rhs, t_span, y0, t_eval=t_eval,
                        method="RK45", rtol=1e-8, atol=1e-11)
        Ca0 = reaction.Ca0
        return {
            "t": sol.t,
            "concentrations": {"A": sol.y[0], "B": sol.y[1], "C": sol.y[2]},
            "conversion": 1.0 - sol.y[0] / Ca0,
            "success": sol.success,
            "message": sol.message,
        }

    elif reaction.reaction_type == ReactionType.SECOND_ORDER_2A_TO_B:
        # 2A → B,  −rA = k·CA²
        def rhs(t, y):
            Ca, Cb = y
            r = k * max(Ca, 0.0) ** 2
            return [-2 * r, r]

        y0 = [reaction.Ca0, 0.0]
        sol = solve_ivp(rhs, t_span, y0, t_eval=t_eval,
                        method="RK45", rtol=1e-8, atol=1e-11)
        Ca0 = reaction.Ca0
        return {
            "t": sol.t,
            "concentrations": {"A": sol.y[0], "B": sol.y[1]},
            "conversion": 1.0 - sol.y[0] / Ca0,
            "success": sol.success,
            "message": sol.message,
        }

    raise ValueError(f"Unsupported reaction: {reaction}")
