from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
from scipy.optimize import brentq


@dataclass
class FlashSpeciesData:
    name: str
    A: float = 4.0    # Antoine A  (log10, bar, K)
    B: float = 1500.0 # Antoine B
    C: float = -50.0  # Antoine C (K offset)


@dataclass
class FlashConfig:
    T: float = 350.0            # Flash temperature (K) — user controlled
    P: float = 1.013            # Flash pressure (bar)
    species: list = field(default_factory=list)  # list[FlashSpeciesData]


def _psat(T: float, A: float, B: float, C: float) -> float:
    """Antoine equation: log10(P_sat/bar) = A - B/(T[K] + C)."""
    return 10.0 ** (A - B / (T + C))


def _rachford_rice(psi: float, z: np.ndarray, K: np.ndarray) -> float:
    return float(np.sum(z * (K - 1.0) / (1.0 + psi * (K - 1.0))))


def simulate_flash(
    config: FlashConfig,
    feed_concentrations: dict,
    t: np.ndarray,
    feed_Q: float = 1.0,
) -> dict:
    """
    Apply isothermal flash at each time point using Rachford-Rice.

    feed_concentrations: {species_name: np.ndarray} from upstream CSTR output.
    K_i = P_sat_i(T) / P is constant (T, P fixed); only z_i(t) changes.

    Returns dict with keys:
        t          - time array
        vapor      - {species: mole fraction y_i(t)}
        liquid     - {species: mole fraction x_i(t)}
        psi        - vapor fraction array (0..1)
        streams    - list of stream dicts (Feed in, Vapor out, Liquid out)
        success    - bool
        message    - status string
    """
    species = config.species
    names = [s.name for s in species]
    n = len(names)

    if n == 0 or not all(nm in feed_concentrations for nm in names):
        return {
            "t": t, "vapor": {}, "liquid": {}, "psi": np.zeros_like(t),
            "streams": [], "success": False,
            "message": "Flash species do not match feed concentrations.",
        }

    # K-values (time-invariant)
    K = np.array([_psat(config.T, s.A, s.B, s.C) / config.P for s in species])

    # Stacked concentration matrix: shape (n_species, n_time)
    C_mat = np.vstack([feed_concentrations[nm] for nm in names])  # (n, nt)

    nt = len(t)
    psi_arr = np.empty(nt)
    x_mat = np.empty((n, nt))
    y_mat = np.empty((n, nt))

    all_ok = True
    msg = "OK"

    for ti in range(nt):
        C_t = C_mat[:, ti]
        C_total = C_t.sum()
        if C_total <= 0.0:
            psi_arr[ti] = 0.0
            x_mat[:, ti] = 0.0
            y_mat[:, ti] = 0.0
            continue

        z = C_t / C_total

        # Standard Rachford-Rice trivial-check using g(0+) and g(1-)
        eps = 1e-8
        g0 = _rachford_rice(eps, z, K)
        g1 = _rachford_rice(1.0 - eps, z, K)
        if g0 <= 0.0:
            psi = 0.0   # sub-cooled liquid
        elif g1 >= 0.0:
            psi = 1.0   # super-heated vapor
        else:
            try:
                psi = brentq(_rachford_rice, eps, 1.0 - eps,
                             args=(z, K), xtol=1e-10, maxiter=200)
            except Exception as e:
                psi = 0.5
                all_ok = False
                msg = f"Rachford-Rice did not converge at t={t[ti]:.2f}: {e}"

        psi = float(np.clip(psi, 0.0, 1.0))
        x = z / (1.0 + psi * (K - 1.0))
        y = K * x
        # When one phase is absent, zero out its composition (no physical meaning)
        if psi <= 0.0:
            y = np.zeros_like(z)
        elif psi >= 1.0:
            x = np.zeros_like(z)
        psi_arr[ti] = psi
        x_mat[:, ti] = x
        y_mat[:, ti] = y

    vapor  = {names[i]: y_mat[i] for i in range(n)}
    liquid = {names[i]: x_mat[i] for i in range(n)}

    # Molar flow streams: F_i(t) = feed_Q * C_i(t)  [mol/s]
    C_total_t = C_mat.sum(axis=0)  # total concentration at each t (mol/L)
    Q = feed_Q
    F_t = C_total_t * Q  # total molar flow (mol/s)
    streams = [
        {
            "name": "Feed",
            "direction": "in",
            "Q": Q,
            "flows": {nm: feed_concentrations[nm] * Q for nm in names},
        },
        {
            "name": "Vapor",
            "direction": "out",
            "Q": Q,
            "flows": {names[i]: psi_arr * F_t * y_mat[i] for i in range(n)},
        },
        {
            "name": "Liquid",
            "direction": "out",
            "Q": Q,
            "flows": {names[i]: (1.0 - psi_arr) * F_t * x_mat[i] for i in range(n)},
        },
    ]

    return {
        "t": t,
        "vapor": vapor,
        "liquid": liquid,
        "psi": psi_arr,
        "streams": streams,
        "success": all_ok,
        "message": msg,
    }
