# Built-in Antoine constants: log10(P_sat / bar) = A - B / (T[K] + C)
# Source: NIST-derived values, valid roughly 250-500 K.
# Replace this module with a NIST database lookup when available.

BUILTIN_ANTOINE = {
    "Water":      {"A": 5.40221, "B": 1838.675, "C": -31.737},
    "Benzene":    {"A": 4.72583, "B": 1660.652, "C":  -1.461},
    "Toluene":    {"A": 4.54436, "B": 1738.123, "C": -42.232},
    "Ethanol":    {"A": 5.37229, "B": 1670.409, "C": -40.191},
    "Methanol":   {"A": 5.31301, "B": 1676.569, "C": -21.728},
    "n-Hexane":   {"A": 4.02267, "B": 1316.554, "C": -35.930},
    "Acetone":    {"A": 4.42448, "B": 1312.253, "C": -32.445},
    "Chloroform": {"A": 4.20772, "B": 1233.129, "C": -40.953},
}
