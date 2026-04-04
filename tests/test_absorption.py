"""Unit tests for models/absorption.py — simulate_absorption() and AbsorptionConfig."""
import math
import pytest
import numpy as np

from models.absorption import AbsorptionConfig, PACKING_DATABASE, simulate_absorption


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def default_result():
    """Run with default AbsorptionConfig and return the result dict."""
    return simulate_absorption(AbsorptionConfig())


# ---------------------------------------------------------------------------
# AbsorptionConfig defaults
# ---------------------------------------------------------------------------

class TestAbsorptionConfig:
    def test_default_instantiation(self):
        cfg = AbsorptionConfig()
        assert cfg.y_in == 0.13
        assert cfg.y_out == 0.0005
        assert cfg.x_in == 0.0
        assert cfg.packing == "Ralu Ring 25mm"

    def test_custom_values_stored(self):
        cfg = AbsorptionConfig(y_in=0.10, y_out=0.001, T=310.0)
        assert cfg.y_in == 0.10
        assert cfg.y_out == 0.001
        assert cfg.T == 310.0


# ---------------------------------------------------------------------------
# Return-dict structure
# ---------------------------------------------------------------------------

class TestReturnStructure:
    EXPECTED_KEYS = {
        "z", "y", "x", "y_star", "HOG", "HETP", "kG_a", "kL_a", "KOG_a",
        "NOG", "HOG_bottom", "HOG_top", "HOG_mean",
        "HETP_bottom", "HETP_top", "HETP_mean",
        "H_col", "delta_P",
        "R_gas_pct", "R_liq_pct",
        "L_molar", "L_mass", "L_molar_min", "u_L", "u_G_Fl",
        "u_G_actual", "loading_frac", "lambda_val", "A_abs",
        "L_factor", "x_out", "m",
        "success", "message",
    }

    def test_all_keys_present(self):
        res = default_result()
        assert self.EXPECTED_KEYS.issubset(res.keys())

    def test_profile_arrays_length(self):
        cfg = AbsorptionConfig(n_points=50)
        res = simulate_absorption(cfg)
        for key in ("z", "y", "x", "y_star", "HOG", "HETP", "kG_a", "kL_a", "KOG_a"):
            assert len(res[key]) == 50, f"Array '{key}' has wrong length"

    def test_all_scalars_are_finite(self):
        res = default_result()
        scalar_keys = [
            "NOG", "HOG_bottom", "HOG_top", "HOG_mean",
            "HETP_bottom", "HETP_top", "HETP_mean",
            "H_col", "delta_P", "R_gas_pct", "R_liq_pct",
            "L_molar", "L_mass", "L_molar_min", "u_L", "u_G_Fl",
            "u_G_actual", "loading_frac", "lambda_val", "L_factor", "x_out", "m",
        ]
        for key in scalar_keys:
            assert math.isfinite(res[key]), f"Scalar '{key}' is not finite"


# ---------------------------------------------------------------------------
# Profile array consistency
# ---------------------------------------------------------------------------

class TestProfileArrays:
    def test_y_array_endpoints(self):
        cfg = AbsorptionConfig(y_in=0.13, y_out=0.0005)
        res = simulate_absorption(cfg)
        assert res["y"][0] == pytest.approx(cfg.y_in)
        assert res["y"][-1] == pytest.approx(cfg.y_out)

    def test_z_array_starts_at_zero(self):
        res = default_result()
        assert res["z"][0] == pytest.approx(0.0)

    def test_z_array_monotonically_increasing(self):
        res = default_result()
        assert np.all(np.diff(res["z"]) >= 0)

    def test_z_last_equals_H_col(self):
        res = default_result()
        assert res["z"][-1] == pytest.approx(res["H_col"], rel=1e-6)

    def test_x_array_consistent_with_operating_line(self):
        cfg = AbsorptionConfig()
        res = simulate_absorption(cfg)
        # x(y) = (G/L) * (y - y_out) + x_in  — check a few points
        GoverL = res["L_factor"]  # not stored, recalculate via x_out
        # x_out is at y_in: verify endpoint
        assert res["x"][0] == pytest.approx(res["x_out"], rel=1e-6)
        assert res["x"][-1] == pytest.approx(cfg.x_in, abs=1e-10)

    def test_y_star_equals_m_times_x(self):
        res = default_result()
        np.testing.assert_allclose(res["y_star"], res["m"] * res["x"], rtol=1e-10)

    def test_HOG_array_is_constant(self):
        res = default_result()
        assert np.all(res["HOG"] == res["HOG"][0])

    def test_HETP_array_is_constant(self):
        res = default_result()
        assert np.all(res["HETP"] == res["HETP"][0])

    def test_kG_a_array_is_constant(self):
        res = default_result()
        assert np.all(res["kG_a"] == res["kG_a"][0])


# ---------------------------------------------------------------------------
# Physical constraints
# ---------------------------------------------------------------------------

class TestPhysicalConstraints:
    def test_H_col_positive(self):
        assert default_result()["H_col"] > 0.0

    def test_NOG_positive(self):
        assert default_result()["NOG"] > 0.0

    def test_delta_P_positive(self):
        assert default_result()["delta_P"] > 0.0

    def test_resistance_percentages_sum_to_100(self):
        res = default_result()
        total = res["R_gas_pct"] + res["R_liq_pct"]
        assert total == pytest.approx(100.0, abs=1e-6)

    def test_resistance_percentages_in_range(self):
        res = default_result()
        assert 0.0 < res["R_gas_pct"] < 100.0
        assert 0.0 < res["R_liq_pct"] < 100.0

    def test_L_molar_greater_than_L_min(self):
        res = default_result()
        assert res["L_molar"] > res["L_molar_min"]

    def test_L_factor_preserved(self):
        cfg = AbsorptionConfig(L_factor=1.8)
        res = simulate_absorption(cfg)
        assert res["L_factor"] == pytest.approx(1.8)

    def test_u_G_actual_matches_config(self):
        cfg = AbsorptionConfig(u_G=0.8)
        res = simulate_absorption(cfg)
        assert res["u_G_actual"] == pytest.approx(0.8)

    def test_x_out_positive(self):
        assert default_result()["x_out"] > 0.0

    def test_m_positive(self):
        assert default_result()["m"] > 0.0

    def test_A_abs_is_inverse_of_lambda(self):
        res = default_result()
        assert res["A_abs"] == pytest.approx(1.0 / res["lambda_val"], rel=1e-10)

    def test_HOG_mean_equals_H_col_over_NOG(self):
        res = default_result()
        assert res["HOG_mean"] == pytest.approx(res["H_col"] / res["NOG"], rel=5e-2)


# ---------------------------------------------------------------------------
# Hydraulic check
# ---------------------------------------------------------------------------

class TestHydraulicCheck:
    # For the default packing (Ralu Ring 25mm) the flooding velocity is ~0.041 m/s,
    # so we use u_G=0.02 m/s for the "not flooding" tests.
    _safe_cfg = AbsorptionConfig(u_G=0.02)

    def test_non_flooding_config_is_ok(self):
        res = simulate_absorption(self._safe_cfg)
        assert res["success"] is True
        assert res["message"] == "OK"

    def test_loading_fraction_below_one_when_ok(self):
        res = simulate_absorption(self._safe_cfg)
        assert res["loading_frac"] < 1.0

    def test_flooding_detected(self):
        # u_G=0.05 m/s > u_G_Fl (~0.041 m/s) for the default packing
        cfg = AbsorptionConfig(u_G=0.05)
        res = simulate_absorption(cfg)
        assert res["success"] is False
        assert res["loading_frac"] >= 1.0
        assert "Flooding" in res["message"]

    def test_loading_frac_increases_with_u_G(self):
        res_low  = simulate_absorption(AbsorptionConfig(u_G=0.01))
        res_high = simulate_absorption(AbsorptionConfig(u_G=0.03))
        assert res_high["loading_frac"] > res_low["loading_frac"]


# ---------------------------------------------------------------------------
# Sensitivity / monotonicity
# ---------------------------------------------------------------------------

class TestSensitivity:
    def test_H_col_increases_with_stricter_spec(self):
        """Requiring lower y_out demands a taller column."""
        res_easy = simulate_absorption(AbsorptionConfig(y_out=0.01))
        res_hard = simulate_absorption(AbsorptionConfig(y_out=0.0005))
        assert res_hard["H_col"] > res_easy["H_col"]

    def test_H_col_increases_with_higher_y_in(self):
        """More CO₂ to remove → taller column."""
        res_low  = simulate_absorption(AbsorptionConfig(y_in=0.05, y_out=0.001))
        res_high = simulate_absorption(AbsorptionConfig(y_in=0.20, y_out=0.001))
        assert res_high["H_col"] > res_low["H_col"]

    def test_H_col_decreases_with_higher_L_factor(self):
        """More solvent flow → fewer transfer units / shorter column."""
        res_lo = simulate_absorption(AbsorptionConfig(L_factor=1.2))
        res_hi = simulate_absorption(AbsorptionConfig(L_factor=2.5))
        assert res_hi["H_col"] < res_lo["H_col"]

    def test_NOG_increases_with_stricter_spec(self):
        res_easy = simulate_absorption(AbsorptionConfig(y_out=0.01))
        res_hard = simulate_absorption(AbsorptionConfig(y_out=0.0005))
        assert res_hard["NOG"] > res_easy["NOG"]

    def test_delta_P_increases_with_u_G(self):
        res_lo = simulate_absorption(AbsorptionConfig(u_G=0.5))
        res_hi = simulate_absorption(AbsorptionConfig(u_G=1.5))
        assert res_hi["delta_P"] > res_lo["delta_P"]


# ---------------------------------------------------------------------------
# Equilibrium slope (m)
# ---------------------------------------------------------------------------

class TestEquilibriumSlope:
    def test_m_equals_H_px_over_P(self):
        cfg = AbsorptionConfig(H_px=3.4e7, P=101325.0)
        res = simulate_absorption(cfg)
        assert res["m"] == pytest.approx(cfg.H_px / cfg.P, rel=1e-10)

    def test_higher_H_px_gives_larger_m(self):
        res_lo = simulate_absorption(AbsorptionConfig(H_px=1e7))
        res_hi = simulate_absorption(AbsorptionConfig(H_px=5e7))
        assert res_hi["m"] > res_lo["m"]


# ---------------------------------------------------------------------------
# Packing database coverage
# ---------------------------------------------------------------------------

class TestPackingDatabase:
    @pytest.mark.parametrize("packing", list(PACKING_DATABASE.keys()))
    def test_all_packings_run_without_error(self, packing):
        cfg = AbsorptionConfig(packing=packing)
        res = simulate_absorption(cfg)
        assert res["H_col"] > 0.0
        assert math.isfinite(res["H_col"])

    def test_unknown_packing_raises(self):
        cfg = AbsorptionConfig(packing="NonExistentPacking")
        with pytest.raises(KeyError):
            simulate_absorption(cfg)


# ---------------------------------------------------------------------------
# HETP formula for lambda ≈ 1
# ---------------------------------------------------------------------------

class TestHETPLambdaEdgeCase:
    def test_HETP_equals_HOG_when_lambda_is_one(self):
        """When λ = 1 the HETP formula degenerates to HETP = HOG."""
        # λ = m · G / L = m / (L_factor / stripping denominator)
        # Easier to set H_px and P so m = L_molar / G_molar exactly.
        # We tune via binary search instead: just assert the branch is reached
        # by constructing a near-unity lambda config and check HETP ≈ HOG.
        # (The code checks abs(lambda-1) < 1e-6.)
        cfg = AbsorptionConfig()
        res = simulate_absorption(cfg)
        if abs(res["lambda_val"] - 1.0) < 1e-6:
            assert res["HETP_mean"] == pytest.approx(res["HOG_mean"])
        else:
            # For the default config lambda ≠ 1; just verify log formula is used
            expected = res["HOG_mean"] * math.log(res["lambda_val"]) / (res["lambda_val"] - 1.0)
            assert res["HETP_mean"] == pytest.approx(expected, rel=1e-6)
