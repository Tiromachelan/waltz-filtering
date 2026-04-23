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

EDGE_LABELS = ("+", "-", "→", "←")
_ARROW_REVERSE = {"→": "←", "←": "→"}


def local_symbol(edge_id: str, edge_label: str, junction_id: str) -> str:
    start, end = edges[edge_id]
    if junction_id != start and junction_id != end:
        raise ValueError(f"Junction {junction_id!r} is not incident to edge {edge_id!r}")
    if edge_label in {"+", "-"}:
        return edge_label
    if junction_id == start:
        return edge_label
    return _ARROW_REVERSE[edge_label]


def has_junction_support(
    edge_id: str,
    edge_label: str,
    junction_id: str,
    domains: dict[str, set[str]],
) -> bool:
    incident_edges = junctions[junction_id]["edges"]
    degree = len(incident_edges)
    allowed_local_tuples = junction_catalog.get(degree)
    if allowed_local_tuples is None:
        raise ValueError(
            f"No junction catalog entries for degree-{degree} junction {junction_id!r}"
        )

    target_index = incident_edges.index(edge_id)
    target_local_symbol = local_symbol(edge_id, edge_label, junction_id)

    for local_tuple in allowed_local_tuples:
        if local_tuple[target_index] != target_local_symbol:
            continue

        tuple_supported = True
        for idx, other_edge_id in enumerate(incident_edges):
            if other_edge_id == edge_id:
                continue

            required_symbol = local_tuple[idx]
            if not any(
                local_symbol(other_edge_id, candidate, junction_id) == required_symbol
                for candidate in domains[other_edge_id]
            ):
                tuple_supported = False
                break

        if tuple_supported:
            return True

    return False


def filter_edge_domains() -> dict[str, set[str]]:
    domains = {edge_id: set(EDGE_LABELS) for edge_id in edges}

    changed = True
    while changed:
        changed = False
        for edge_id, (junction_a, junction_b) in edges.items():
            current = domains[edge_id]
            removable: set[str] = set()

            for edge_label in current:
                if not has_junction_support(edge_id, edge_label, junction_a, domains):
                    removable.add(edge_label)
                    continue
                if not has_junction_support(edge_id, edge_label, junction_b, domains):
                    removable.add(edge_label)

            if removable:
                current.difference_update(removable)
                changed = True
                if not current:
                    raise ValueError(f"Inconsistent labeling: edge {edge_id!r} has no labels")

    return domains


def main() -> None:
    filtered_domains = filter_edge_domains()
    print("Surviving labels per edge:")
    for edge_id in edges:
        labels = ", ".join(label for label in EDGE_LABELS if label in filtered_domains[edge_id])
        print(f"{edge_id}: {labels}")


if __name__ == "__main__":
    main()
