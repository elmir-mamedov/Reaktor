import numpy as np


def build_single_pass_streams(
    species,
    Q: float,
    t: np.ndarray,
    concentrations: dict,
    inlet_name: str = "Feed",
    outlet_name: str = "Product",
) -> list:
    """Build inlet + outlet stream dicts for a single-stream flow unit (CSTR, PFR, etc.).

    Inlet flows are constant (Q × C_feed); outlet flows are time-varying (Q × C(t)).
    For multi-stream units (mixer, separator), callers build streams manually using
    the same dict structure: {name, direction, Q, flows: {species: np.ndarray}}.
    """
    inlet = {
        "name": inlet_name,
        "direction": "in",
        "Q": Q,
        "flows": {s.name: np.full_like(t, Q * s.C_feed, dtype=float)
                  for s in species},
    }
    outlet = {
        "name": outlet_name,
        "direction": "out",
        "Q": Q,
        "flows": {sp: Q * concentrations[sp] for sp in concentrations},
    }
    return [inlet, outlet]
