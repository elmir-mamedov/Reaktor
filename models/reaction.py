from dataclasses import dataclass, field


@dataclass
class SpeciesEntry:
    name: str          # "A", "Ethanol", etc.
    stoich: float      # positive coefficient
    is_reactant: bool  # determines sign in ODE
    C0: float          # initial concentration
    C_feed: float = 0.0  # CSTR inlet/feed concentration (mol/L)


@dataclass
class CustomReaction:
    species: list = field(default_factory=list)
    k: float = 0.05
    use_arrhenius: bool = False
    A_factor: float = 1.0e8
    Ea: float = 50_000.0
    T: float = 298.15
    t_end: float = 100.0
    n_points: int = 500
    reactor_type: str = "batch"   # "batch" or "cstr"
    tau: float = 60.0             # CSTR residence time (s) — kept in sync with V/Q
    Q: float = 1.0                # Volumetric flow rate (L/s)
    V: float = 60.0               # Reactor volume (L)
    R: float = field(default=8.314, init=False, repr=False)

    def effective_k(self) -> float:
        if self.use_arrhenius:
            import math
            return self.A_factor * math.exp(-self.Ea / (self.R * self.T))
        return self.k

    def reaction_label(self) -> str:
        def fmt_side(entries):
            parts = []
            for s in entries:
                if s.stoich == int(s.stoich) and s.stoich != 1:
                    coef = str(int(s.stoich))
                elif s.stoich != 1.0:
                    coef = f"{s.stoich:.2g}"
                else:
                    coef = ""
                parts.append(f"{coef}{s.name}")
            return " + ".join(parts)

        reactants = [s for s in self.species if s.is_reactant]
        products = [s for s in self.species if not s.is_reactant]
        lhs = fmt_side(reactants) if reactants else "?"
        rhs = fmt_side(products) if products else "?"
        return f"{lhs} → {rhs}"


def validate(rxn: CustomReaction) -> "str | None":
    reactants = [s for s in rxn.species if s.is_reactant]
    products = [s for s in rxn.species if not s.is_reactant]
    if not reactants:
        return "At least one reactant is required."
    if not products:
        return "At least one product is required."
    names = [s.name.strip() for s in rxn.species]
    if any(not n for n in names):
        return "All species must have a name."
    if len(names) != len(set(names)):
        return "Species names must be unique."
    if any(s.stoich <= 0 for s in rxn.species):
        return "All stoichiometric coefficients must be positive."
    if any(s.C0 < 0 for s in rxn.species):
        return "Initial concentrations cannot be negative."
    if rxn.reactor_type == "cstr":
        if any(s.C_feed < 0 for s in rxn.species):
            return "Feed concentrations cannot be negative."
        if not any(s.is_reactant and s.C_feed > 0 for s in rxn.species):
            return "At least one reactant must have a positive feed concentration."
    return None


# ── Templates ──────────────────────────────────────────────────────────────

TEMPLATES = {
    "A → B  (1st order)": [
        SpeciesEntry("A", 1.0, True,  1.0),
        SpeciesEntry("B", 1.0, False, 0.0),
    ],
    "A + B → C  (2nd order)": [
        SpeciesEntry("A", 1.0, True,  1.0),
        SpeciesEntry("B", 1.0, True,  1.0),
        SpeciesEntry("C", 1.0, False, 0.0),
    ],
    "2A → B  (2nd order)": [
        SpeciesEntry("A", 2.0, True,  1.0),
        SpeciesEntry("B", 1.0, False, 0.0),
    ],
    "Custom": [],
}

# CSTR templates: C0=0 (empty start), C_feed set for reactants
CSTR_TEMPLATES = {
    "A → B  (1st order)": [
        SpeciesEntry("A", 1.0, True,  1.0, 1.0),
        SpeciesEntry("B", 1.0, False, 0.0, 0.0),
    ],
    "A + B → C  (2nd order)": [
        SpeciesEntry("A", 1.0, True,  1.0, 1.0),
        SpeciesEntry("B", 1.0, True,  1.0, 1.0),
        SpeciesEntry("C", 1.0, False, 0.0, 0.0),
    ],
    "2A → B  (2nd order)": [
        SpeciesEntry("A", 2.0, True,  1.0, 1.0),
        SpeciesEntry("B", 1.0, False, 0.0, 0.0),
    ],
    "Custom": [],
}


def default_reaction() -> CustomReaction:
    """Return a ready-to-use A → B batch reaction."""
    return CustomReaction(species=[
        SpeciesEntry("A", 1.0, True,  1.0),
        SpeciesEntry("B", 1.0, False, 0.0),
    ])


def default_cstr_reaction() -> CustomReaction:
    """Return a ready-to-use A → B CSTR reaction."""
    return CustomReaction(
        species=[
            SpeciesEntry("A", 1.0, True,  1.0, 1.0),
            SpeciesEntry("B", 1.0, False, 0.0, 0.0),
        ],
        reactor_type="cstr",
        tau=60.0,
        t_end=300.0,
    )
