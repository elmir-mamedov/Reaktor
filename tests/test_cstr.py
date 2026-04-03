import math

import numpy as np
import pytest

from models.cstr import build_rhs, extract_outputs, simulate_cstr
from models.reaction import CustomReaction, SpeciesEntry, validate


# ── Helpers ───────────────────────────────────────────────────────────────────

def _ab_rxn(**kwargs):
    """A → B CSTR, 1st order. Override fields via kwargs."""
    params = dict(
        species=[
            SpeciesEntry("A", 1.0, True,  1.0, 1.0),
            SpeciesEntry("B", 1.0, False, 0.0, 0.0),
        ],
        k=0.05,
        reactor_type="cstr",
        Q=1.0,
        V=60.0,
        t_end=1000.0,
        n_points=500,
    )
    params.update(kwargs)
    return CustomReaction(**params)


# ── TestValidate ──────────────────────────────────────────────────────────────

class TestValidate:
    def _cstr(self, species):
        return CustomReaction(species=species, reactor_type="cstr")

    def test_valid_cstr(self):
        rxn = self._cstr([
            SpeciesEntry("A", 1.0, True,  1.0, 1.0),
            SpeciesEntry("B", 1.0, False, 0.0, 0.0),
        ])
        assert validate(rxn) is None

    def test_no_reactants(self):
        rxn = self._cstr([SpeciesEntry("B", 1.0, False, 0.0, 0.0)])
        assert validate(rxn) is not None

    def test_no_products(self):
        rxn = self._cstr([SpeciesEntry("A", 1.0, True, 1.0, 1.0)])
        assert validate(rxn) is not None

    def test_empty_name(self):
        rxn = self._cstr([
            SpeciesEntry("",  1.0, True,  1.0, 1.0),
            SpeciesEntry("B", 1.0, False, 0.0, 0.0),
        ])
        assert validate(rxn) is not None

    def test_duplicate_names(self):
        rxn = self._cstr([
            SpeciesEntry("A", 1.0, True,  1.0, 1.0),
            SpeciesEntry("A", 1.0, False, 0.0, 0.0),
        ])
        assert validate(rxn) is not None

    def test_negative_stoich(self):
        rxn = self._cstr([
            SpeciesEntry("A", -1.0, True,  1.0, 1.0),
            SpeciesEntry("B",  1.0, False, 0.0, 0.0),
        ])
        assert validate(rxn) is not None

    def test_negative_C0(self):
        rxn = self._cstr([
            SpeciesEntry("A", 1.0, True,  -0.5, 1.0),
            SpeciesEntry("B", 1.0, False,  0.0, 0.0),
        ])
        assert validate(rxn) is not None

    def test_negative_C_feed(self):
        rxn = self._cstr([
            SpeciesEntry("A", 1.0, True,  1.0, -1.0),
            SpeciesEntry("B", 1.0, False, 0.0,  0.0),
        ])
        assert validate(rxn) is not None

    def test_no_positive_C_feed(self):
        rxn = self._cstr([
            SpeciesEntry("A", 1.0, True,  1.0, 0.0),
            SpeciesEntry("B", 1.0, False, 0.0, 0.0),
        ])
        assert validate(rxn) is not None


# ── TestBuildRhs ──────────────────────────────────────────────────────────────

class TestBuildRhs:
    def test_y0_matches_species_C0(self):
        rxn = CustomReaction(
            species=[
                SpeciesEntry("A", 1.0, True,  0.8, 1.0),
                SpeciesEntry("B", 1.0, False, 0.2, 0.0),
            ],
            k=0.05, reactor_type="cstr", Q=1.0, V=60.0,
        )
        _, y0 = build_rhs(rxn)
        assert y0 == [0.8, 0.2]

    def test_rhs_at_steady_state_first_order(self):
        """At the analytical steady state Ca_ss = C_feed/(1+k*tau), dydt must be zero."""
        k, Q, V, C_feed = 0.05, 1.0, 60.0, 1.0
        tau = V / Q
        Ca_ss = C_feed / (1 + k * tau)
        Cb_ss = C_feed - Ca_ss

        rxn = CustomReaction(
            species=[
                SpeciesEntry("A", 1.0, True,  Ca_ss, C_feed),
                SpeciesEntry("B", 1.0, False, Cb_ss, 0.0),
            ],
            k=k, reactor_type="cstr", Q=Q, V=V,
        )
        rhs_fn, _ = build_rhs(rxn)
        dydt = rhs_fn(0.0, [Ca_ss, Cb_ss])
        assert abs(dydt[0]) < 1e-10
        assert abs(dydt[1]) < 1e-10

    def test_rhs_uses_context_temperature(self):
        """Higher temperature via context → faster rate → more negative dydt for reactant A."""
        rxn = CustomReaction(
            species=[
                SpeciesEntry("A", 1.0, True,  0.5, 1.0),
                SpeciesEntry("B", 1.0, False, 0.5, 0.0),
            ],
            use_arrhenius=False,
            A_factor=1.0e8,
            Ea=50_000.0,
            reactor_type="cstr",
            Q=1.0, V=60.0,
        )
        rhs_fn, _ = build_rhs(rxn)
        y = [0.5, 0.5]
        dydt_low  = rhs_fn(0.0, y, context={"temperature": 300.0})
        dydt_high = rhs_fn(0.0, y, context={"temperature": 400.0})
        assert dydt_high[0] < dydt_low[0]

    def test_rhs_clamps_negative_concentration(self):
        """Negative concentrations in y don't crash; the reaction rate is clamped to zero."""
        rxn = _ab_rxn()
        rhs_fn, _ = build_rhs(rxn)
        dydt = rhs_fn(0.0, [-0.1, 0.0])
        assert isinstance(dydt, list)
        assert len(dydt) == 2

    def test_rhs_second_order(self):
        """A + B → C: signs and magnitude of dydt match hand-calculated values."""
        k, Q, V = 0.01, 1.0, 10.0
        tau = V / Q
        rxn = CustomReaction(
            species=[
                SpeciesEntry("A", 1.0, True,  0.5, 1.0),
                SpeciesEntry("B", 1.0, True,  0.5, 1.0),
                SpeciesEntry("C", 1.0, False, 0.0, 0.0),
            ],
            k=k, reactor_type="cstr", Q=Q, V=V,
        )
        rhs_fn, _ = build_rhs(rxn)
        Ca, Cb, Cc = 0.5, 0.5, 0.0
        r = k * Ca * Cb
        dydt = rhs_fn(0.0, [Ca, Cb, Cc])
        assert abs(dydt[0] - ((1.0 - Ca) / tau - r)) < 1e-12
        assert abs(dydt[1] - ((1.0 - Cb) / tau - r)) < 1e-12
        assert abs(dydt[2] - ((0.0 - Cc) / tau + r)) < 1e-12


# ── TestSimulateCstr ──────────────────────────────────────────────────────────

class TestSimulateCstr:
    @pytest.fixture
    def first_order(self):
        return _ab_rxn()

    def test_return_keys(self, first_order):
        result = simulate_cstr(first_order)
        assert {"t", "concentrations", "conversion", "streams", "Q", "success", "message"} <= result.keys()

    def test_solver_succeeds(self, first_order):
        result = simulate_cstr(first_order)
        assert result["success"] is True

    def test_convergence_to_steady_state(self, first_order):
        """After 1000 s A must be within 1% of the analytical CSTR steady state."""
        k, Q, V = 0.05, 1.0, 60.0
        Ca_ss = 1.0 / (1 + k * (V / Q))
        result = simulate_cstr(first_order)
        Ca_final = result["concentrations"]["A"][-1]
        assert abs(Ca_final - Ca_ss) / Ca_ss < 0.01

    def test_conversion_range(self, first_order):
        result = simulate_cstr(first_order)
        conv = result["conversion"]
        assert np.all(conv >= 0.0)
        assert np.all(conv <= 1.0)

    def test_conversion_zero_feed(self):
        """When C_feed of first reactant is 0 the conversion array must be all zeros."""
        rxn = CustomReaction(
            species=[
                SpeciesEntry("A", 1.0, True,  0.0, 0.0),
                SpeciesEntry("B", 1.0, False, 0.0, 0.0),
            ],
            k=0.05, reactor_type="cstr",
            Q=1.0, V=60.0, t_end=100.0, n_points=100,
        )
        result = simulate_cstr(rxn)
        assert np.all(result["conversion"] == 0.0)

    def test_streams_structure(self, first_order):
        streams = simulate_cstr(first_order)["streams"]
        assert len(streams) == 2
        for stream in streams:
            assert "name" in stream
            assert "direction" in stream
            assert "Q" in stream
            assert "flows" in stream

    def test_mass_balance_no_reaction(self):
        """With k=0 (no reaction) the outlet concentration must equal the feed at steady state."""
        rxn = _ab_rxn(k=0.0)
        result = simulate_cstr(rxn)
        Ca_final = result["concentrations"]["A"][-1]
        assert abs(Ca_final - 1.0) < 0.01


# ── TestExtractOutputs ────────────────────────────────────────────────────────

class TestExtractOutputs:
    @pytest.fixture
    def rxn(self):
        return CustomReaction(
            species=[
                SpeciesEntry("A", 1.0, True,  0.6, 1.0),
                SpeciesEntry("B", 1.0, False, 0.4, 0.0),
            ],
            reactor_type="cstr",
        )

    def test_returns_concentrations_key(self, rxn):
        result = extract_outputs([0.6, 0.4], rxn)
        assert "concentrations" in result

    def test_maps_species_names(self, rxn):
        result = extract_outputs([0.6, 0.4], rxn)
        assert "A" in result["concentrations"]
        assert "B" in result["concentrations"]

    def test_values_match_y(self, rxn):
        result = extract_outputs([0.6, 0.4], rxn)
        assert result["concentrations"]["A"] == pytest.approx(0.6)
        assert result["concentrations"]["B"] == pytest.approx(0.4)
