from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from itertools import product
from math import atan2

Point = tuple[int, int]


@dataclass(frozen=True, slots=True)
class Edge:
    edge_id: str
    a: Point
    b: Point
    path: tuple[Point, ...]


@dataclass(frozen=True, slots=True)
class Junction:
    point: Point
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


# Hardcoded example "image" (1 = edge pixel, 0 = background)
EXAMPLE_GRID: tuple[tuple[int, ...], ...] = (
    (0, 0, 0, 0, 0, 0, 0),
    (0, 0, 1, 0, 0, 0, 0),
    (0, 0, 1, 0, 0, 0, 0),
    (0, 1, 1, 1, 1, 1, 0),
    (0, 0, 1, 0, 0, 0, 0),
    (0, 0, 1, 0, 0, 0, 0),
    (0, 0, 0, 0, 0, 0, 0),
)


def neighbors4(point: Point, pixels: set[Point]) -> tuple[Point, ...]:
    r, c = point
    result: list[Point] = []
    for dr, dc in ((-1, 0), (0, -1), (0, 1), (1, 0)):
        candidate = (r + dr, c + dc)
        if candidate in pixels:
            result.append(candidate)
    return tuple(sorted(result))


def is_vertex(point: Point, neighbors: tuple[Point, ...]) -> bool:
    if len(neighbors) != 2:
        return True
    (r1, c1), (r2, c2) = neighbors
    r0, c0 = point
    d1 = (r1 - r0, c1 - c0)
    d2 = (r2 - r0, c2 - c0)
    return not (d1[0] == -d2[0] and d1[1] == -d2[1])


def classify_junction(point: Point, edge_dirs: tuple[tuple[int, int], ...]) -> str:
    degree = len(edge_dirs)
    if degree == 1:
        return "endpoint"
    if degree == 2:
        (dr1, dc1), (dr2, dc2) = edge_dirs
        if dr1 == -dr2 and dc1 == -dc2:
            return "line"
        return "elbow"
    if degree == 3:
        return "tee"
    if degree == 4:
        return "cross"
    return f"star_{degree}"


def build_graph(grid: tuple[tuple[int, ...], ...]) -> tuple[dict[str, Edge], dict[Point, Junction]]:
    pixels = {(r, c) for r, row in enumerate(grid) for c, value in enumerate(row) if value}
    if not pixels:
        return {}, {}

    neighbor_map = {p: neighbors4(p, pixels) for p in pixels}
    vertices = {p for p in pixels if is_vertex(p, neighbor_map[p])}

    visited_steps: set[tuple[Point, Point]] = set()
    edges: dict[str, Edge] = {}
    edge_index = 1

    for vertex in sorted(vertices):
        for neighbor in neighbor_map[vertex]:
            if (vertex, neighbor) in visited_steps:
                continue

            path = [vertex]
            prev = vertex
            current = neighbor
            visited_steps.add((vertex, neighbor))
            visited_steps.add((neighbor, vertex))

            while current not in vertices:
                path.append(current)
                next_candidates = [n for n in neighbor_map[current] if n != prev]
                if not next_candidates:
                    break
                nxt = next_candidates[0]
                visited_steps.add((current, nxt))
                visited_steps.add((nxt, current))
                prev, current = current, nxt

            if current not in vertices:
                continue

            path.append(current)
            edge_id = f"E{edge_index:02d}"
            edge_index += 1
            edges[edge_id] = Edge(edge_id=edge_id, a=path[0], b=path[-1], path=tuple(path))

    vertex_to_edges: dict[Point, list[str]] = {v: [] for v in vertices}
    for edge in edges.values():
        vertex_to_edges[edge.a].append(edge.edge_id)
        vertex_to_edges[edge.b].append(edge.edge_id)

    junctions: dict[Point, Junction] = {}
    for vertex in sorted(vertices):
        edge_and_angles: list[tuple[str, float, tuple[int, int]]] = []
        for edge_id in vertex_to_edges[vertex]:
            edge = edges[edge_id]
            next_point = edge.path[1] if vertex == edge.a else edge.path[-2]
            dr = next_point[0] - vertex[0]
            dc = next_point[1] - vertex[1]
            angle = atan2(dr, dc)
            edge_and_angles.append((edge_id, angle, (dr, dc)))
        edge_and_angles.sort(key=lambda item: item[1])
        incident_edges = tuple(item[0] for item in edge_and_angles)
        edge_dirs = tuple(item[2] for item in edge_and_angles)
        junctions[vertex] = Junction(point=vertex, kind=classify_junction(vertex, edge_dirs), incident_edges=incident_edges)

    return edges, junctions


def mark_at_junction(edge: Edge, label: str, junction_point: Point) -> str:
    if label == "convex":
        return "+"
    if label == "concave":
        return "-"
    if label == "occluding_a_to_b":
        return "out" if junction_point == edge.a else "in"
    if label == "occluding_b_to_a":
        return "out" if junction_point == edge.b else "in"
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
            marks[position] = mark_at_junction(edges[eid], label, junction.point)
        if assignment_is_legal(junction.kind, tuple(marks)):
            return True
    return False


def waltz_filter(edges: dict[str, Edge], junctions: dict[Point, Junction]) -> tuple[dict[str, set[str]], bool]:
    domains: dict[str, set[str]] = {edge_id: set(LABELS) for edge_id in edges}
    changed = True

    while changed:
        changed = False
        for junction in sorted(junctions.values(), key=lambda j: j.point):
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
    edges, junctions = build_graph(EXAMPLE_GRID)
    domains, consistent = waltz_filter(edges, junctions)
    print_result(edges, domains, consistent)


if __name__ == "__main__":
    main()
