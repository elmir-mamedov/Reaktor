import numpy as np
from scipy.integrate import solve_ivp
from typing import Dict

from models.reaction import ElementaryReaction, ReactionType


def simulate(reaction: ElementaryReaction) -> Dict:
    """
    Simulate a batch reactor for the given elementary reaction.

    Returns a dict with keys:
        t              - time array (s)
        concentrations - dict mapping species label -> concentration array (mol/L)
        conversion     - fractional conversion of A (0..1)
        success        - bool
        message        - solver status message
    """
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

    raise ValueError(f"Unsupported reaction type: {reaction.reaction_type}")
