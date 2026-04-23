junction_catalog = {
    2: [
        # L-junctions (Left arm, Right arm)
        ("←", "→"),
        ("→", "←"),
        ("-", "→"),
        ("←", "-"),
        ("→", "+"),
        ("+", "←"),
    ],
    
    3: [
        # Arrow junctions (Left wing, Right wing, Stem)
        ("→", "←", "+"),
        ("-", "-", "+"),
        ("+", "+", "-"),
        
        # Y-junctions (Left arm, Right arm, Bottom arm)
        ("+", "+", "+"),
        ("-", "-", "-"),
        ("→", "←", "-"),
        ("←", "-", "→"),
        ("-", "→", "←"),
        
        # T-junctions (Left collinear, Right collinear, Stem)
        ("←", "→", "←"),
        ("→", "←", "→"),
        ("←", "→", "+"),
        ("→", "←", "-"),
    ],
}

edges = {
    "AB": ("A", "B"),
    "AA'": ("A", "A'"),
    "BC": ("B", "C"),
    "BB'": ("B", "B'"),
    "CC'": ("C", "C'"),
    "C'B'": ("C'", "B'"),
    "B'A'": ("B'", "A'"),
    "HC'": ("H", "C'"),
    "A'J": ("A'", "J"),
    "HI_M": ("H", "I"),  # Top back arc of the cylinder
    "HI_N": ("H", "I"),  # Top front arc of the cylinder
    "IF'": ("I", "F'"),
    "F'G'": ("F'", "G'"),
    "G'D'": ("G'", "D'"),
    "D'K": ("D'", "K"),
    "JK_T": ("J", "K"),  # Bottom front arc of the cylinder
    "D'D": ("D'", "D"),
    "G'G": ("G'", "G"),
    "F'F": ("F'", "F"),
    "GD": ("G", "D"),
    "GF": ("G", "F"),
    "DE": ("D", "E"),
    "FE": ("F", "E"),
}

junctions = {
    "A": {
        "edges": ["AB", "AA'"]
    },
    "B": {
        "edges": ["BC", "BB'", "AB"]  # CW order
    },
    "C": {
        "edges": ["CC'", "BC"]
    },
    "A'": {
        "edges": ["B'A'", "A'J", "AA'"]
    },
    "B'": {
        "edges": ["C'B'", "B'A'", "BB'"]
    },
    "C'": {
        "edges": ["HC'", "C'B'", "CC'"]
    },
    "H": {
        "edges": ["HI_M", "HI_N", "HC'"]
    },
    "I": {
        "edges": ["IF'", "HI_N", "HI_M"]
    },
    "J": {
        "edges": ["A'J", "JK_T"]
    },
    "K": {
        "edges": ["D'K", "JK_T"]
    },
    "F'": {
        "edges": ["IF'", "F'F", "F'G'"]
    },
    "G'": {
        "edges": ["F'G'", "G'G", "G'D'"]
    },
    "D'": {
        "edges": ["G'D'", "D'D", "D'K"]
    },
    "F": {
        "edges": ["FE", "GF", "F'F"]
    },
    "G": {
        "edges": ["GF", "GD", "G'G"]
    },
    "D": {
        "edges": ["GD", "DE", "D'D"]
    },
    "E": {
        "edges": ["FE", "DE"]
    }
}

