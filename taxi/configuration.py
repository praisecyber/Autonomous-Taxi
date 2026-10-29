"""Conservative simulation-only route configuration; fixed map coordinates/IDs."""

import json
from copy import deepcopy

from pydantic import BaseModel, ConfigDict, Field, field_validator
from .navigation import STOPS, POINTS, EDGES


class RouteConfiguration(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: int = Field(ge=0)
    stops: dict[str, str]
    edges: dict[str, list[str]]

    @field_validator("stops")
    @classmethod
    def labels(cls, value):
        if set(value) != set(STOPS):
            raise ValueError("Keep the existing stop IDs; map geometry is fixed")
        if any(not label.strip() or len(label) > 80 for label in value.values()):
            raise ValueError("Stop names must contain 1–80 characters")
        return {key: label.strip() for key, label in value.items()}

    @field_validator("edges")
    @classmethod
    def graph(cls, edges):
        if set(edges) != set(POINTS):
            raise ValueError("Keep the existing map node IDs")
        for node, neighbors in edges.items():
            if len(neighbors) != len(set(neighbors)):
                raise ValueError("Duplicate edges are not allowed")
            for neighbor in neighbors:
                if neighbor not in POINTS or neighbor == node:
                    raise ValueError("Invalid route node")
                if neighbor not in EDGES[node]:
                    raise ValueError("Only existing mapped road segments may be enabled")
                if node not in edges[neighbor]:
                    raise ValueError("Road segments must be bidirectional")
        visited, pending = set(), ["A"]
        while pending:
            node = pending.pop()
            if node not in visited:
                visited.add(node)
                pending.extend(edges[node])
        if visited != set(POINTS):
            raise ValueError("Every stop and junction must remain reachable")
        return edges


def load_configuration(store):
    row = store.db.execute("SELECT * FROM configuration WHERE id=1").fetchone()
    if row:
        config = RouteConfiguration(version=row["version"], **json.loads(row["payload"]))
        return config.model_dump()
    return {"version": 0, "stops": deepcopy(STOPS), "edges": deepcopy(EDGES)}
