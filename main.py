from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from itertools import product


@dataclass(frozen=True, slots=True)
class Edge:
    edge_id: str
    a: str
    b: str


@dataclass(frozen=True, slots=True)
class Junction:
    junction_id: str
    kind: str
    incident_edges: tuple[str, ...]


LABELS: tuple[str, ...] = ("convex", "concave", "occluding_a_to_b", "occluding_b_to_a")
LABEL_SYMBOL = {
    "convex": "+",
    "concave": "-",
    "occluding_a_to_b": "a->b",
    "occluding_b_to_a": "b->a",
}

# Hardcoded compatibility catalog (patterns are exact mark counts).
CATALOG: dict[str, tuple[dict[str, int], ...]] = {
    "endpoint": ({"+": 1}, {"-": 1}, {"out": 1}),
    "line": ({"+": 2}, {"-": 2}, {"in": 1, "out": 1}),
    "elbow": ({"+": 2}, {"-": 2}, {"+": 1, "-": 1}, {"in": 1, "out": 1}),
    "tee": ({"+": 1, "-": 2}, {"in": 1, "out": 1, "-": 1}),
    "cross": ({"+": 2, "-": 2}, {"in": 2, "out": 2}),
}


# Hardcoded symbolic graph example.
# Junction "edges" must be in cyclic order and each junction must provide explicit kind.
EXAMPLE_EDGES: dict[str, tuple[str, str]] = {
    "E1": ("J1", "J2"),
    "E2": ("J1", "J3"),
    "E3": ("J1", "J4"),
    "E4": ("J2", "J5"),
}

EXAMPLE_JUNCTIONS: dict[str, dict[str, object]] = {
    "J1": {"kind": "tee", "edges": ["E1", "E2", "E3"]},
    "J2": {"kind": "line", "edges": ["E1", "E4"]},
    "J3": {"kind": "endpoint", "edges": ["E2"]},
    "J4": {"kind": "endpoint", "edges": ["E3"]},
    "J5": {"kind": "endpoint", "edges": ["E4"]},
}


def build_graph(
    edges_input: dict[str, tuple[str, str]],
    junctions_input: dict[str, dict[str, object]],
) -> tuple[dict[str, Edge], dict[str, Junction]]:
    edges = {
        edge_id: Edge(edge_id=edge_id, a=endpoints[0], b=endpoints[1])
        for edge_id, endpoints in edges_input.items()
    }
    junctions: dict[str, Junction] = {}

    for junction_id, payload in junctions_input.items():
        if "kind" not in payload:
            raise ValueError(f"Junction {junction_id} is missing required 'kind'.")
        if "edges" not in payload:
            raise ValueError(f"Junction {junction_id} is missing required 'edges'.")
        kind = payload["kind"]
        incident_edges = payload["edges"]
        if not isinstance(kind, str):
            raise ValueError(f"Junction {junction_id} kind must be a string.")
        if not isinstance(incident_edges, list) or not all(isinstance(e, str) for e in incident_edges):
            raise ValueError(f"Junction {junction_id} edges must be a list[str].")
        if not incident_edges:
            raise ValueError(f"Junction {junction_id} must reference at least one edge.")
        junctions[junction_id] = Junction(junction_id=junction_id, kind=kind, incident_edges=tuple(incident_edges))

    for edge_id, edge in edges.items():
        if edge.a not in junctions or edge.b not in junctions:
            raise ValueError(f"Edge {edge_id} references unknown junction(s): {edge.a}, {edge.b}.")
        if edge_id not in junctions[edge.a].incident_edges or edge_id not in junctions[edge.b].incident_edges:
            raise ValueError(
                f"Edge {edge_id} must be listed in both endpoint junctions ({edge.a}, {edge.b})."
            )

    for junction_id, junction in junctions.items():
        for edge_id in junction.incident_edges:
            if edge_id not in edges:
                raise ValueError(f"Junction {junction_id} references unknown edge {edge_id}.")
            edge = edges[edge_id]
            if junction_id != edge.a and junction_id != edge.b:
                raise ValueError(f"Junction {junction_id} lists edge {edge_id} but is not an endpoint of that edge.")

    return edges, junctions


def mark_at_junction(edge: Edge, label: str, junction_id: str) -> str:
    if label == "convex":
        return "+"
    if label == "concave":
        return "-"
    if label == "occluding_a_to_b":
        return "out" if junction_id == edge.a else "in"
    if label == "occluding_b_to_a":
        return "out" if junction_id == edge.b else "in"
    raise ValueError(f"Unknown label: {label}")


def marks_match_pattern(marks: tuple[str, ...], pattern: dict[str, int]) -> bool:
    counts = Counter(marks)
    for key, expected in pattern.items():
        if counts.get(key, 0) != expected:
            return False
    for observed_key, observed_count in counts.items():
        if observed_key not in pattern and observed_count > 0:
            return False
    return sum(pattern.values()) == len(marks)


def assignment_is_legal(kind: str, marks: tuple[str, ...]) -> bool:
    patterns = CATALOG.get(kind)
    if not patterns:
        return True
    return any(marks_match_pattern(marks, pattern) for pattern in patterns)


def value_has_support(
    edge_id: str,
    candidate_label: str,
    junction: Junction,
    edges: dict[str, Edge],
    domains: dict[str, set[str]],
) -> bool:
    positions = {eid: index for index, eid in enumerate(junction.incident_edges)}
    other_edges = [eid for eid in junction.incident_edges if eid != edge_id]
    other_domains = [sorted(domains[eid]) for eid in other_edges]

    for combination in product(*other_domains):
        labels_by_edge = {edge_id: candidate_label}
        labels_by_edge.update(dict(zip(other_edges, combination, strict=True)))
        marks = ["" for _ in junction.incident_edges]
        for eid, label in labels_by_edge.items():
            position = positions[eid]
            marks[position] = mark_at_junction(edges[eid], label, junction.junction_id)
        if assignment_is_legal(junction.kind, tuple(marks)):
            return True
    return False


def waltz_filter(edges: dict[str, Edge], junctions: dict[str, Junction]) -> tuple[dict[str, set[str]], bool]:
    domains: dict[str, set[str]] = {edge_id: set(LABELS) for edge_id in edges}
    changed = True

    while changed:
        changed = False
        for junction in sorted(junctions.values(), key=lambda j: j.junction_id):
            for edge_id in junction.incident_edges:
                current_domain = domains[edge_id]
                supported = {
                    label
                    for label in sorted(current_domain)
                    if value_has_support(edge_id, label, junction, edges, domains)
                }
                if supported != current_domain:
                    domains[edge_id] = supported
                    changed = True
                    if not supported:
                        return domains, False
    return domains, True


def print_result(edges: dict[str, Edge], domains: dict[str, set[str]], consistent: bool) -> None:
    print("Waltz Filtering Result")
    print("======================")
    print(f"Consistent labeling found: {consistent}")
    for edge_id in sorted(edges):
        edge = edges[edge_id]
        labels = [LABEL_SYMBOL[label] for label in LABELS if label in domains[edge_id]]
        print(f"{edge_id} {edge.a}->{edge.b}: {', '.join(labels)}")


def main() -> None:
    edges, junctions = build_graph(EXAMPLE_EDGES, EXAMPLE_JUNCTIONS)
    domains, consistent = waltz_filter(edges, junctions)
    print_result(edges, domains, consistent)


if __name__ == "__main__":
    main()
