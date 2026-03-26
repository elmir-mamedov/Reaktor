from dataclasses import dataclass, field
from enum import Enum


class ReactionType(Enum):
    FIRST_ORDER_A_TO_B = "A → B  (1st order,  −rA = k·CA)"
    SECOND_ORDER_A_B_TO_C = "A + B → C  (2nd order,  −rA = k·CA·CB)"
    SECOND_ORDER_2A_TO_B = "2A → B  (2nd order,  −rA = k·CA²)"


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
