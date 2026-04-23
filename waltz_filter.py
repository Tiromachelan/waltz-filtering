# Catalog of legal local edge-label patterns, grouped by junction degree and type.
junction_catalog = {
    2: {
        # L-JUNCTIONS
        # Reading clockwise across the interior angle (< 180 degrees)
        # Order: (Arm 1, Arm 2)
        "L": [
            ("→", "←"),  # Outer boundary corner
            ("←", "→"),  # Inner hole boundary
            ("+", "→"),
            ("←", "+"),
            ("-", "←"),
            ("→", "-"),
        ],
    },
    3: {
        # ARROW JUNCTIONS
        # The angle > 180 degrees is at the top.
        # Reading clockwise: Right Wing, Stem, Left Wing
        "ARROW": [
            ("→", "+", "←"),  # Outer boundary (e.g., corner of a wedge)
            ("+", "-", "+"),  # Inner corner (e.g., inside corner of a room)
            ("-", "+", "-"),  # Exterior fold (e.g., looking at the spine of an open book)
        ],
        # Y-JUNCTIONS
        # Three angles < 180 degrees.
        # Reading clockwise starting from ~2 o'clock: Top-Right Arm, Bottom Arm, Top-Left Arm
        "Y": [
            ("+", "+", "+"),  # Outer corner of a cube
            ("-", "-", "-"),  # Inner corner of a box
            ("→", "-", "←"),  # Boundary with one concave edge
            ("-", "←", "→"),  # (Cyclic permutation of above)
            ("←", "→", "-"),  # (Cyclic permutation of above)
        ],
        # T-JUNCTIONS
        # Two collinear edges forming the top of the 'T', stem pointing down.
        # Reading clockwise: Left Collinear, Right Collinear, Stem
        # (Note: In Waltz filtering, collinear edges of a T-junction are always
        # boundaries going left-to-right, so they are always "→" then "←")
        "T": [
            ("→", "←", "+"),
            ("→", "←", "-"),
            ("→", "←", "→"),
            ("→", "←", "←"),
        ],
    },
}

# Hardcoded scene graph edges: edge_id -> (junction_a, junction_b).
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

# Hardcoded junction metadata:
# - "edges" are listed in clockwise cyclic order around the junction
# - "type" selects which subset of catalog tuples can appear at this junction
junctions = {
    "A": {
        "edges": ["AA'", "AB"],
        "type": "L",
    },
    "B": {
        "edges": ["AB", "BC", "BB'"],
        "type": "ARROW",
    },
    "C": {
        "edges": ["CC'", "BC"],
        "type": "L",
    },
    "A'": {
        "edges": ["A'J", "B'A'", "AA'"],
        "type": "Y",
    },
    "B'": {
        "edges": ["B'A'", "C'B'", "BB'"],
        "type": "Y",
    },
    "C'": {
        "edges": ["HC'", "CC'", "C'B'"],
        "type": "Y",
    },
    "H": {
        "edges": ["HI_M", "HI_N", "HC'"],
        "type": "Y",
    },
    "I": {
        "edges": ["HI_N", "HI_M", "IF'"],
        "type": "Y",
    },
    "J": {
        "edges": ["JK_T", "A'J"],
        "type": "L",
    },
    "K": {
        "edges": ["D'K", "JK_T"],
        "type": "L",
    },
    "F'": {
        "edges": ["IF'", "F'G'", "F'F"],
        "type": "ARROW",
    },
    "G'": {
        "edges": ["F'G'", "G'D'", "G'G"],
        "type": "ARROW",
    },
    "D'": {
        "edges": ["D'K", "D'D", "G'D'"],
        "type": "ARROW",
    },
    "F": {
        "edges": ["F'F", "FE", "GF"],
        "type": "T",
    },
    "G": {
        "edges": ["G'G", "GF", "GD"],
        "type": "ARROW",
    },
    "D": {
        "edges": ["D'D", "GD", "DE"],
        "type": "Y",
    },
    "E": {
        "edges": ["DE", "FE"],
        "type": "L",
    }
}

# Global edge label alphabet:
# "+" convex, "-" concave, arrows are occluding boundaries with direction.
EDGE_LABELS = ("+", "-", "→", "←")
_ARROW_REVERSE = {"→": "←", "←": "→"}


def local_symbol(edge_id: str, edge_label: str, junction_id: str) -> str:
    """Convert an edge label into the symbol seen from one junction endpoint."""
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
    """Return True when edge_label can participate in at least one legal local tuple."""
    junction = junctions[junction_id]
    incident_edges = junction["edges"]
    degree = len(incident_edges)
    junction_type = junction.get("type")
    if junction_type is None:
        raise ValueError(f"Junction {junction_id!r} is missing required type")

    allowed_by_type = junction_catalog.get(degree)
    if allowed_by_type is None:
        raise ValueError(
            f"No junction catalog entries for degree-{degree} junction {junction_id!r}"
        )
    allowed_local_tuples = allowed_by_type.get(junction_type)
    if allowed_local_tuples is None:
        raise ValueError(
            f"No {junction_type!r} catalog entries for degree-{degree} junction {junction_id!r}"
        )

    target_index = incident_edges.index(edge_id)
    target_local_symbol = local_symbol(edge_id, edge_label, junction_id)

    # Try each legal tuple for this junction type and see whether neighbors can match it.
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
    """Run iterative Waltz constraint propagation until no domains change."""
    domains = {edge_id: set(EDGE_LABELS) for edge_id in edges}

    changed = True
    while changed:
        changed = False
        for edge_id, (junction_a, junction_b) in edges.items():
            current = domains[edge_id]
            removable: set[str] = set()

            # A label survives only if both endpoint junctions can support it.
            for edge_label in current:
                if not has_junction_support(edge_id, edge_label, junction_a, domains):
                    removable.add(edge_label)
                    continue
                if not has_junction_support(edge_id, edge_label, junction_b, domains):
                    removable.add(edge_label)

            if removable:
                current.difference_update(removable)
                changed = True
                # Empty domain means no globally consistent interpretation remains.
                if not current:
                    raise ValueError(f"Inconsistent labeling: edge {edge_id!r} has no labels")

    return domains


def main() -> None:
    """Execute filtering on the hardcoded graph and print the final domains."""
    filtered_domains = filter_edge_domains()
    print("Surviving labels per edge:")
    for edge_id in edges:
        labels = ", ".join(label for label in EDGE_LABELS if label in filtered_domains[edge_id])
        print(f"{edge_id}: {labels}")


if __name__ == "__main__":
    main()
