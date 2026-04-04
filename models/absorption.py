from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
from scipy.optimize import brentq

# ---------------------------------------------------------------------------
# Packing database — Billet & Schultes (1999) constants
# Keys: a_p (m²/m³), epsilon (void fraction), Ch, Cs, CL, CV, Cp
# ---------------------------------------------------------------------------
PACKING_DATABASE: dict[str, dict] = {
    "Ralu Ring 25mm": {
        "a_p": 215.0, "epsilon": 0.94,
        "Ch": 0.533, "Cs": 2.464, "CL": 1.334, "CV": 0.382, "Cp": 0.784,
    },
    "Pall Ring 25mm (plastic)": {
        "a_p": 205.0, "epsilon": 0.90,
        "Ch": 0.604, "Cs": 2.528, "CL": 1.239, "CV": 0.356, "Cp": 0.763,
    },
    "Raschig Ring 25mm (ceramic)": {
        "a_p": 190.0, "epsilon": 0.73,
        "Ch": 0.530, "Cs": 2.300, "CL": 1.045, "CV": 0.270, "Cp": 1.000,
    },
    "IMTP 25 (metal)": {
        "a_p": 225.0, "epsilon": 0.96,
        "Ch": 0.719, "Cs": 2.971, "CL": 1.577, "CV": 0.415, "Cp": 0.557,
    },
}

_G = 9.81          # gravitational acceleration (m/s²)
_M_WATER = 0.018   # molar mass of water (kg/mol)
_M_AIR   = 0.029   # molar mass of air (kg/mol)


@dataclass
class AbsorptionConfig:
    # --- Gas inlet / outlet compositions ---
    y_in:  float = 0.13     # CO₂ mole fraction at gas inlet (bottom)
    y_out: float = 0.0005   # CO₂ mole fraction at gas outlet (top)
    x_in:  float = 0.0      # CO₂ mole fraction in entering solvent (top), 0 = pure

    # --- Operating conditions ---
    u_G:   float = 1.1      # Superficial gas velocity (m/s)
    T:     float = 298.15   # Temperature (K)
    P:     float = 101325.0 # Pressure (Pa)

    # --- Liquid rate specification ---
    # L is set as L_factor × L_min (the thermodynamic minimum liquid rate).
    # L_factor > 1 is required for feasible absorption; typically 1.2–2.0.
    # The loading-point calculation then checks whether this L can be
    # hydraulically supported (i.e. the column won't flood).
    L_factor: float = 1.5   # L / L_min operating multiplier

    # --- Column geometry ---
    D_col: float = 1.4      # Column inner diameter (m)

    # --- Packing ---
    packing: str = "Ralu Ring 25mm"

    # --- Physical properties (CO₂-water defaults at 25 °C, 1 atm) ---
    rho_L:   float = 997.0      # Liquid density (kg/m³)
    mu_L:    float = 8.9e-4     # Liquid dynamic viscosity (Pa·s)
    sigma_L: float = 0.072      # Liquid surface tension (N/m)
    D_L:     float = 1.92e-9    # CO₂ diffusivity in liquid (m²/s)
    D_G:     float = 1.60e-5    # CO₂ diffusivity in gas phase (m²/s)
    rho_G:   float = 1.185      # Gas density (kg/m³)
    mu_G:    float = 1.84e-5    # Gas dynamic viscosity (Pa·s)
    H_px:    float = 3.4e7      # Henry's constant (Pa), y* = (H_px/P)·x

    # --- Discretisation ---
    n_points: int = 100


def simulate_absorption(config: AbsorptionConfig) -> dict:
    """
    Steady-state design of a packed absorption column using the
    Billet-Schultes (1999) mass-transfer and hydraulic model.

    Profile axis: column height z [m], z=0 at bottom (gas inlet),
    z=H at top (gas outlet / liquid inlet).

    Liquid rate is L = L_factor × L_min (specified via config.L_factor).
    The loading-point velocity is then checked to confirm the column
    can hydraulically support this liquid rate.

    Returns a dict with profile arrays (length n_points) and key scalars.
    """
    cfg = config
    pk  = PACKING_DATABASE[cfg.packing]
    a_p     = pk["a_p"]
    epsilon = pk["epsilon"]
    Ch      = pk["Ch"]
    Cs      = pk["Cs"]
    CL      = pk["CL"]
    CV      = pk["CV"]
    Cp      = pk["Cp"]

    # -----------------------------------------------------------------------
    # 1. Column geometry and gas flow
    # -----------------------------------------------------------------------
    A_col   = math.pi * cfg.D_col**2 / 4.0          # m²
    M_G     = cfg.y_in * 0.044 + (1.0 - cfg.y_in) * _M_AIR   # kg/mol
    G_mass  = cfg.u_G * A_col * cfg.rho_G            # kg/s
    G_molar = G_mass / M_G                            # mol/s

    # Equilibrium slope  y* = m·x
    m = cfg.H_px / cfg.P

    # -----------------------------------------------------------------------
    # 2. Thermodynamic minimum liquid rate (pinch analysis)
    #    x_out_max = y_in / m  (liquid in equilibrium with inlet gas)
    #    L_min: minimum L for the required separation
    # -----------------------------------------------------------------------
    x_out_max  = cfg.y_in / m
    L_molar_min = (G_molar * (cfg.y_in - cfg.y_out)
                   / max(x_out_max - cfg.x_in, 1e-15))

    # Operating liquid rate
    L_molar = cfg.L_factor * L_molar_min
    L_mass  = L_molar * _M_WATER
    u_L     = L_mass / (cfg.rho_L * A_col)   # m/s

    # -----------------------------------------------------------------------
    # 3. Hydraulic check — Billet-Schultes loading / flooding point
    #    u_G,Fl = Ch · √[(ρ_L−ρ_G)/ρ_G · ε^1.5 · √(g/a_p) · exp(−1.463·F_Lv^0.842)]
    # -----------------------------------------------------------------------
    F_Lv_op = (L_mass / G_mass) * math.sqrt(cfg.rho_G / cfg.rho_L)

    u_G_Fl = (Ch * math.sqrt(
        (cfg.rho_L - cfg.rho_G) / cfg.rho_G
        * epsilon**1.5
        * math.sqrt(_G / a_p)
        * math.exp(-1.463 * F_Lv_op**0.842)
    ))

    loading_frac_actual = cfg.u_G / u_G_Fl   # what fraction of flooding we're at

    if loading_frac_actual >= 1.0:
        hydraulic_ok = False
        hyd_msg = (f"Flooding: u_G ({cfg.u_G:.2f} m/s) ≥ u_G,Fl ({u_G_Fl:.2f} m/s). "
                   f"Reduce u_G or increase column diameter.")
    else:
        hydraulic_ok = True
        hyd_msg = ""

    # -----------------------------------------------------------------------
    # 4. Material balance — operating line
    #    x(y) = (G_molar/L_molar)·(y − y_out) + x_in
    # -----------------------------------------------------------------------
    GoverL = G_molar / L_molar
    x_out  = GoverL * (cfg.y_in - cfg.y_out) + cfg.x_in

    # -----------------------------------------------------------------------
    # 5. Billet-Schultes mass-transfer coefficients (constant along column
    #    for dilute / straight-line approximation)
    # -----------------------------------------------------------------------
    d_h  = 4.0 * epsilon / a_p          # hydraulic diameter (m)
    nu_L = cfg.mu_L / cfg.rho_L         # liquid kinematic viscosity (m²/s)
    nu_G = cfg.mu_G / cfg.rho_G         # gas kinematic viscosity (m²/s)

    # k_L  (m/s) — Billet & Schultes (1999), Eq. 4:
    #   k_L = C_L · sqrt(D_L · u_L / (ε · d_h)) · (g / ν_L)^(1/6)
    k_L = (CL
           * math.sqrt(cfg.D_L * u_L / (epsilon * d_h))
           * (_G / nu_L)**(1.0/6.0))

    # k_G  (m/s) — Billet & Schultes (1999), Eq. 6:
    #   k_G = C_V · D_G^(2/3) · u_G^(1/3) / (ν_G^(1/6) · d_h^(1/2))
    k_G = (CV
           * cfg.D_G**(2.0/3.0)
           * cfg.u_G**(1.0/3.0)
           / (nu_G**(1.0/6.0) * d_h**0.5))

    kL_a   = k_L * a_p   # s⁻¹
    kG_a   = k_G * a_p   # s⁻¹

    # Overall coefficient and HOG
    KOG_a  = 1.0 / (1.0 / kG_a + m / kL_a)    # s⁻¹
    G_flux = G_molar / A_col                     # mol/(m²·s)
    HOG    = G_flux / KOG_a                      # m

    # -----------------------------------------------------------------------
    # 6. Profile arrays along y-axis (bottom → top: y_in → y_out)
    # -----------------------------------------------------------------------
    y_arr      = np.linspace(cfg.y_in, cfg.y_out, cfg.n_points)
    x_arr      = GoverL * (y_arr - cfg.y_out) + cfg.x_in
    y_star_arr = m * x_arr
    driving    = y_arr - y_star_arr
    driving    = np.where(driving > 1e-15, driving, 1e-15)

    ntu_integrand = 1.0 / driving
    NOG = float(np.trapezoid(ntu_integrand[::-1], y_arr[::-1]))

    # z(y): cumulative integral from y_in (bottom) toward y_out (top)
    cumulative = np.concatenate([[0.0],
        np.cumsum(0.5 * (HOG / driving[:-1] + HOG / driving[1:])
                  * np.abs(np.diff(y_arr)))])
    z_arr = cumulative
    H_col = float(z_arr[-1])

    # HOG and HETP arrays (constant for dilute / straight equilibrium)
    HOG_arr  = np.full(cfg.n_points, HOG)
    lambda_val = m * G_molar / L_molar    # stripping factor

    if abs(lambda_val - 1.0) < 1e-6:
        HETP = HOG
    else:
        HETP = HOG * math.log(lambda_val) / (lambda_val - 1.0)

    HETP_arr    = np.full(cfg.n_points, HETP)
    HETP_mean   = HETP
    HOG_mean    = HOG

    # -----------------------------------------------------------------------
    # 7. Pressure drop — Billet-Schultes wet correlation
    # -----------------------------------------------------------------------
    dP_dry  = Cs * (a_p / epsilon**3) * cfg.rho_G * cfg.u_G**2 / 2.0
    dP_wet  = dP_dry * math.exp(
        1.463 * Cp * F_Lv_op**0.842
        * math.sqrt(cfg.rho_L / cfg.rho_G)
        / epsilon**1.5
    )
    delta_P = dP_wet * H_col   # Pa

    # -----------------------------------------------------------------------
    # 8. Mass-transfer resistance split
    # -----------------------------------------------------------------------
    R_total   = 1.0 / KOG_a
    R_gas_pct = (1.0 / kG_a) / R_total * 100.0
    R_liq_pct = (m / kL_a)   / R_total * 100.0

    # -----------------------------------------------------------------------
    # 9. Status message
    # -----------------------------------------------------------------------
    msgs = []
    if hyd_msg:
        msgs.append(hyd_msg)
    if not msgs:
        msgs.append("OK")
    success_flag = hydraulic_ok

    return {
        # Profile arrays (index 0 = bottom, index -1 = top)
        "z":        z_arr,
        "y":        y_arr,
        "x":        x_arr,
        "y_star":   y_star_arr,
        "HOG":      HOG_arr,
        "HETP":     HETP_arr,
        "kG_a":     np.full(cfg.n_points, kG_a),
        "kL_a":     np.full(cfg.n_points, kL_a),
        "KOG_a":    np.full(cfg.n_points, KOG_a),
        # Transfer-unit scalars
        "NOG":          NOG,
        "HOG_bottom":   HOG,
        "HOG_top":      HOG,
        "HOG_mean":     HOG_mean,
        "HETP_bottom":  HETP,
        "HETP_top":     HETP,
        "HETP_mean":    HETP_mean,
        # Column sizing
        "H_col":    H_col,
        "delta_P":  delta_P,
        # Resistance split
        "R_gas_pct": R_gas_pct,
        "R_liq_pct": R_liq_pct,
        # Flow conditions
        "L_molar":          L_molar,
        "L_mass":           L_mass,
        "L_molar_min":      L_molar_min,
        "u_L":              u_L,
        "u_G_Fl":           u_G_Fl,
        "u_G_actual":       cfg.u_G,
        "loading_frac":     loading_frac_actual,
        "lambda_val":       lambda_val,
        "A_abs":            1.0 / lambda_val if lambda_val != 0 else float("inf"),
        "L_factor":         cfg.L_factor,
        "x_out":            x_out,
        "m":                m,
        # Status
        "success": success_flag,
        "message": "  |  ".join(msgs),
    }
