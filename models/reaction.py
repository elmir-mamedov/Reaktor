from dataclasses import dataclass, field
from enum import Enum


class ReactionType(Enum):
    FIRST_ORDER_A_TO_B = "A → B  (1st order,  −rA = k·CA)"
    SECOND_ORDER_A_B_TO_C = "A + B → C  (2nd order,  −rA = k·CA·CB)"
    SECOND_ORDER_2A_TO_B = "2A → B  (2nd order,  −rA = k·CA²)"
    CUSTOM = "Custom stoichiometry"

@dataclass
class SpeciesEntry:
    name: str          # "A", "Ethanol", etc.
    stoich: float      # positive coefficient
    is_reactant: bool  # determines sign in ODE
    C0: float          # initial concentration

def _default_species():
    return [
        SpeciesEntry(name="A", stoich=1.0, is_reactant=True, C0=1.0),
        SpeciesEntry(name="B", stoich=1.0, is_reactant=False, C0=0.0),
    ]


@dataclass
class CustomReaction:
    species: list = field(default_factory=_default_species)
    k: float = 0.05
    use_arrhenius: bool = False
    A_factor: float = 1.0e8
    Ea: float = 50_000.0
    T: float = 298.15
    t_end: float = 100.0
    n_points: int = 500
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
    return None


@dataclass
class ElementaryReaction:
    reaction_type: ReactionType = ReactionType.FIRST_ORDER_A_TO_B

    # Direct rate constant (used when use_arrhenius is False)
    k: float = 0.05             # 1/s for 1st order; L/(mol·s) for 2nd order

    # Arrhenius parameters
    use_arrhenius: bool = False
    A_factor: float = 1.0e8     # pre-exponential factor (same units as k)
    Ea: float = 50_000.0        # activation energy, J/mol
    T: float = 298.15           # temperature, K

    # Feed conditions
    Ca0: float = 1.0            # initial conc. of A, mol/L
    Cb0: float = 1.0            # initial conc. of B (for A+B→C), mol/L

    # Simulation horizon
    t_end: float = 100.0        # s
    n_points: int = 500

    R: float = field(default=8.314, init=False, repr=False)

    def effective_k(self) -> float:
        """Return the rate constant, applying Arrhenius if requested."""
        if self.use_arrhenius:
            import math
            return self.A_factor * math.exp(-self.Ea / (self.R * self.T))
        return self.k
