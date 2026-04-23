"""
Waltz Filtering — Huffman-Clowes constraint propagation
for interpreting 2D line drawings of 3D scenes.

Algorithm:
    Each line in the drawing is assigned one of four labels:
        '+'  convex edge  (positive dihedral, ridge toward viewer)
        '-'  concave edge (negative dihedral, valley / crack)
        'R'  occluding boundary — solid is to the RIGHT when traversing
             the edge in the direction AWAY from this junction
        'L'  occluding boundary — solid is to the LEFT

    Arc-consistency (AC-3) propagation eliminates label combinations that
    cannot be consistent with any labeling at a neighboring junction.

Scene (image.png):
    Three objects: left rectangular box, center cylinder, right rectangular box.
    Major labeled junctions: A,B,C (left box left side),
    A',B',C' (left box / cylinder interface),
    H,I,J,K (cylinder silhouette), M (cylinder top), N,T (T-junctions),
    D',E',F' (cylinder / right box interface), D,E,F,G (right box).

Constraints (constraints.png):
    18 valid junction labelings across 4 types:
        Arrow (3), L (6), Y (5), T (4)
    See CATALOG below — updated to match the constraint table image.

References:
    Huffman (1971), Clowes (1971), Waltz (1975)
"""

from collections import deque
from copy import deepcopy


# ─────────────────────────────────────────────────────────────────────────────
# Label utilities
# ─────────────────────────────────────────────────────────────────────────────

def flip(label: str) -> str:
    """Return the label as seen from the OTHER endpoint of the same edge.

    R and L swap because the traversal direction reverses when we walk
    the edge from the opposite end.  '+' and '-' are orientation-independent.
    """
    return {'R': 'L', 'L': 'R'}.get(label, label)


LABEL_SYMBOLS = {'+': '+', '-': '-', 'R': '→', 'L': '←'}


# ─────────────────────────────────────────────────────────────────────────────
# Junction catalog  (Huffman-Clowes scheme for trihedral scenes)
#
# Each entry lists the valid label-tuples for a junction's arms in
# CLOCKWISE order.  Modify this table to match your constraints.png.
# ─────────────────────────────────────────────────────────────────────────────

CATALOG: dict[str, list[tuple[str, ...]]] = {

    # ── Arrow-junction (3 valid labelings from constraints.png) ──────────────
    #
    #   arm[0] ── ● ── arm[2]   (wings, silhouette boundary edges)
    #              |
    #           arm[1]           (shaft, interior or boundary edge going up)
    #
    # Physical reading: the shaft is the dominant occluding or interior arm;
    # the two wings are symmetric silhouette or interior arms.
    #
    'Arrow': [
        ('R', 'R', 'L'),   # shaft=boundary-R,  wings: R / L
        ('-', 'R', '-'),   # shaft=boundary-R,  wings both concave
        ('+', 'R', '+'),   # shaft=boundary-R,  wings both convex
    ],

    # ── L-junction (6 valid labelings from constraints.png) ──────────────────
    #
    #   arm[1]
    #     │
    #     ●── arm[0]
    #
    'L': [
        ('L', 'L'),   # both boundary-L  (e.g. occluding contour corner)
        ('L', 'R'),   # boundary-L / boundary-R
        ('-', 'L'),   # concave / boundary-L
        ('L', '-'),   # boundary-L / concave
        ('-', '+'),   # concave / convex   (crack meeting a ridge)
        ('+', 'R'),   # convex / boundary-R
    ],

    # ── Y-junction / Fork (5 valid labelings from constraints.png) ───────────
    #
    #   arm[1]  arm[2]
    #      \    /
    #       \  /
    #        ●
    #        │
    #      arm[0]
    #
    'Y': [
        ('+', '+', '+'),   # all convex  — near outer corner of a block
        ('-', '-', '-'),   # all concave — inner room corner
        ('L', 'L', '-'),   # two boundary-L arms, one concave
        ('L', '-', 'R'),   # mixed boundary / concave
        ('-', 'L', 'R'),   # concave / mixed boundary
    ],

    # ── T-junction (4 valid labelings from constraints.png) ──────────────────
    #
    #   arm[0] ── ● ── arm[2]   (crossbar: both boundary-L in all cases)
    #              │
    #           arm[1]           (stem: varies)
    #
    'T': [
        ('L', 'R', 'L'),   # stem = boundary-R (going away)
        ('L', 'L', 'L'),   # stem = boundary-L
        ('L', '+', 'L'),   # stem = convex
        ('L', '-', 'L'),   # stem = concave
    ],
}


# ─────────────────────────────────────────────────────────────────────────────
# Scene representation
# ─────────────────────────────────────────────────────────────────────────────

class Junction:
    """A vertex in the 2D line drawing."""

    def __init__(self, name: str, jtype: str, arms: list[str]) -> None:
        """
        Parameters
        ----------
        name  : identifier, e.g. 'A'
        jtype : one of 'L', 'Y', 'T', 'Arrow'
        arms  : edge names listed in CLOCKWISE order around this junction
        """
        self.name = name
        self.jtype = jtype
        self.arms = arms
        # Initialize with the full catalog; propagation will prune this.
        self.labelings: list[tuple[str, ...]] = list(CATALOG[jtype])

    def arm_index(self, edge_name: str) -> int:
        return self.arms.index(edge_name)

    def label_for(self, edge_name: str, labeling: tuple[str, ...]) -> str:
        """Return the label this junction assigns to edge_name in the given labeling."""
        return labeling[self.arm_index(edge_name)]

    def __repr__(self) -> str:
        return (f"Junction({self.name!r}, {self.jtype!r}, "
                f"{len(self.labelings)} labelings)")


class Edge:
    """A line segment connecting two junctions."""

    def __init__(self, name: str, j1: str, j2: str) -> None:
        """
        j1 → j2 defines the positive traversal direction for R/L semantics.
        The label from j1's perspective is stored directly; from j2's
        perspective the same physical label is flip(label).
        """
        self.name = name
        self.endpoints: tuple[str, str] = (j1, j2)

    def other(self, junction_name: str) -> str:
        a, b = self.endpoints
        return b if junction_name == a else a

    def __repr__(self) -> str:
        return f"Edge({self.name!r}: {self.endpoints[0]}↔{self.endpoints[1]})"


# ─────────────────────────────────────────────────────────────────────────────
# Waltz filtering — arc-consistency (AC-3)
# ─────────────────────────────────────────────────────────────────────────────

def _filter_arc(jA: Junction, jB: Junction, edge_name: str) -> bool:
    """Remove from jA.labelings any entry whose label on `edge_name` is
    incompatible with every labeling in jB.

    Two labels on the same edge are compatible iff:
        flip(label_from_jA) == label_from_jB

    Returns True if jA.labelings was reduced (a change occurred).
    """
    supported_by_jB = {jB.label_for(edge_name, lb) for lb in jB.labelings}

    pruned = [
        lb for lb in jA.labelings
        if flip(jA.label_for(edge_name, lb)) in supported_by_jB
    ]

    changed = len(pruned) != len(jA.labelings)
    jA.labelings = pruned
    return changed


def waltz_filter(
    junctions: dict[str, Junction],
    edges: dict[str, Edge],
) -> dict[str, Junction]:
    """Run Waltz (Huffman-Clowes) constraint propagation.

    Parameters
    ----------
    junctions : mapping from name to Junction (will be deep-copied)
    edges     : mapping from name to Edge

    Returns
    -------
    A new dict of Junctions with pruned labelings.

    Raises
    ------
    ValueError if the scene is over-constrained (any junction empties out).
    """
    junctions = deepcopy(junctions)

    # Seed the queue with every directed arc (jA → jB) for each shared edge.
    queue: deque[tuple[str, str, str]] = deque()
    for edge in edges.values():
        j1, j2 = edge.endpoints
        queue.append((j1, j2, edge.name))
        queue.append((j2, j1, edge.name))

    while queue:
        jA_name, jB_name, edge_name = queue.popleft()
        jA = junctions[jA_name]
        jB = junctions[jB_name]

        if _filter_arc(jA, jB, edge_name):
            if not jA.labelings:
                raise ValueError(
                    f"Contradiction: junction '{jA_name}' has no valid labelings."
                )
            # jA changed — re-enqueue all neighbors of jA (except jB on this edge).
            for other_edge_name in jA.arms:
                if other_edge_name == edge_name:
                    continue
                neighbor = edges[other_edge_name].other(jA_name)
                queue.append((neighbor, jA_name, other_edge_name))

    return junctions


# ─────────────────────────────────────────────────────────────────────────────
# Scene: left rectangular box from image.png
#
#   C ───── C'          ← C (L), C' (Arrow): top edge
#   |       |
#   B ───── B'          ← B (Y), B' (Arrow): middle horizontal
#   |       |
#   A ───── A'          ← A (L), A' (Arrow): bottom edge
#
#  Left face:  A-B (lower), B-C (upper) — visible vertical silhouette
#  Bottom face: A-A' (horizontal)
#  Middle face: B-B' (horizontal)
#  Top face:   C-C' (horizontal)
#  Right side: A'-B' (lower), B'-C' (upper) — where box meets cylinder
#
#  Junction types
#  ──────────────
#   A  (L):     two edges meet at bottom-left silhouette corner
#   B  (Y):     three faces meet at mid-left; three edges AB, BB', BC
#   C  (L):     two edges meet at top-left silhouette corner
#   A' (Arrow): bottom-right where silhouette meets interior edges
#   B' (Arrow): mid-right where three edges meet (BB', A'B', B'C')
#   C' (Arrow): top-right where silhouette meets interior edges
#
# Update build_scene() to add the cylinder and right box when desired.
# ─────────────────────────────────────────────────────────────────────────────

def build_scene() -> tuple[dict[str, Junction], dict[str, Edge]]:
    """Build the line-drawing scene to be interpreted.

    Currently models the left rectangular box from image.png.
    Extend with the cylinder (junctions H,I,J,K,M,N,T) and right box
    (D',E',F',D,E,F,G) to cover the full scene.

    Arms must be listed in CLOCKWISE order around each junction.
    For Arrow junctions arm[1] is the shaft (the non-boundary edge).
    """
    edges = {
        # Left-face silhouette edges (vertical)
        'AB':  Edge('AB',  'A',  'B'),
        'BC':  Edge('BC',  'B',  'C'),
        # Horizontal interior edges
        'AAp': Edge('AAp', 'A',  'Ap'),
        'BBp': Edge('BBp', 'B',  'Bp'),
        'CCp': Edge('CCp', 'C',  'Cp'),
        # Right-side edges (where box meets cylinder)
        'ApBp': Edge('ApBp', 'Ap', 'Bp'),
        'BpCp': Edge('BpCp', 'Bp', 'Cp'),
    }

    # Arms listed clockwise around each junction.
    junctions = {
        # A — L-junction at bottom-left silhouette corner
        #   arm[0]: AB going up, arm[1]: AAp going right
        'A':  Junction('A',  'L',     ['AB',   'AAp'  ]),

        # B — Y-junction at mid-left where 3 faces meet
        #   clockwise: BBp (right), BC (up), AB (down)
        'B':  Junction('B',  'Y',     ['BBp',  'BC',   'AB'  ]),

        # C — L-junction at top-left silhouette corner
        #   arm[0]: BC going down, arm[1]: CCp going right
        'C':  Junction('C',  'L',     ['BC',   'CCp'  ]),

        # A' — Arrow-junction at bottom-right (silhouette + interior)
        #   wings: AAp (going left, boundary), ApBp (going up, boundary)
        #   shaft: (none in this simplified 2-arm model; treat as L for now)
        #   Note: A' connects only to A and B' in this sub-scene; add the
        #   cylinder edge when modelling the full scene.
        'Ap': Junction('Ap', 'L',     ['AAp',  'ApBp' ]),

        # B' — Arrow-junction at mid-right (shaft = BBp, wings = ApBp, BpCp)
        'Bp': Junction('Bp', 'Arrow', ['ApBp', 'BBp',  'BpCp']),

        # C' — Arrow-junction at top-right (shaft = CCp, wings)
        'Cp': Junction('Cp', 'L',     ['CCp',  'BpCp' ]),
    }

    return junctions, edges


# ─────────────────────────────────────────────────────────────────────────────
# Output
# ─────────────────────────────────────────────────────────────────────────────

def _labeling_str(junction: Junction, labeling: tuple[str, ...]) -> str:
    parts = [
        f"{arm}:{LABEL_SYMBOLS[lbl]}"
        for arm, lbl in zip(junction.arms, labeling)
    ]
    return "  ".join(parts)


def print_results(junctions: dict[str, Junction]) -> None:
    print("\n=== Waltz Filtering Results ===\n")

    for name, jct in sorted(junctions.items()):
        n = len(jct.labelings)
        status = "UNIQUE" if n == 1 else f"{n} possibilities"
        print(f"  Junction {name}  ({jct.jtype})  [{status}]")
        for lb in jct.labelings:
            print(f"    {_labeling_str(jct, lb)}")
        print()

    print("Legend:  + convex   - concave   → boundary/R   ← boundary/L")


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    print("Waltz Filtering — Huffman-Clowes Line-Drawing Interpretation")
    print("=" * 60)

    junctions, edges = build_scene()

    print("\nInitial labelings per junction (before propagation):")
    for name, jct in sorted(junctions.items()):
        print(f"  {name} ({jct.jtype}): {len(jct.labelings)}")

    try:
        result = waltz_filter(junctions, edges)
        print_results(result)
    except ValueError as err:
        print(f"\n✗ No consistent labeling found: {err}")


if __name__ == "__main__":
    main()
