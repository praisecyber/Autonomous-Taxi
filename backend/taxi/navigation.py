"""A small, explicit route graph; coordinates are SIMULATED metres."""

import heapq
import math

POINTS = {"A": (0.0, 0.0), "J": (5.0, 0.0), "B": (10.0, 0.0), "C": (5.0, 5.0)}
STOPS = {"A": "Engineering", "B": "Library", "C": "Student Centre"}
EDGES = {"A": ["J"], "J": ["A", "B", "C"], "B": ["J"], "C": ["J"]}


def route(origin: str, destination: str, stops=None, edges=None) -> list[str]:
    stops = STOPS if stops is None else stops
    edges = EDGES if edges is None else edges
    if origin not in stops or destination not in stops:
        raise ValueError("Choose a configured stop")
    if origin == destination:
        raise ValueError("Vehicle is already at that stop")
    pending = [(0.0, origin, [origin])]
    seen = set()
    while pending:
        cost, node, path = heapq.heappop(pending)
        if node == destination:
            return path
        if node in seen:
            continue
        seen.add(node)
        for nxt in edges[node]:
            heapq.heappush(
                pending, (cost + math.dist(POINTS[node], POINTS[nxt]), nxt, path + [nxt])
            )
    raise ValueError("No allowed route")
