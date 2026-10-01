from collections.abc import Sequence
from pathlib import Path

import numpy as np

from app.domain.entities.node import Node
from app.domain.exceptions import UnknownCityError
from app.infrastructure.geospatial.distance_matrix_builder import (
    build_accident_impacts,
    build_distance_time_matrix,
    build_route_leg_geometries,
)
from app.infrastructure.geospatial.osmnx_client import load_cached_graph

# Data-driven so a second cache_path entry is the only change needed to add
# a city, never a UI/router hardcode (PRD Section 16's pre-seeded-scenario
# requirement, Phase 6's own convention -- only one city is actually cached
# today).
CACHE_DIR = Path(__file__).resolve().parents[4] / "cache"
CITY_CATALOG = {
    "indiranagar_bengaluru": {
        "name": "Indiranagar, Bengaluru",
        "cache_path": CACHE_DIR / "indiranagar_bengaluru.graphml",
    },
}


ACCIDENT_DELAY_MULTIPLIER = 5.0
"""Design Brief Flow C's own "x5 delay" chip -- an accident multiplies the
affected road segment's travel time fivefold, applied to every parallel/
both-direction edge between the same two graph nodes (an accident blocks
the road, not one direction's lane markings)."""


class CachedGraphRepository:
    """GeospatialRepositoryPort implementation over the offline-cached
    OSMnx graphs (PRD Section 8: zero-network at runtime). Real Phase-7
    implementation of what was a stub since Phase 0/1's scaffolding."""

    def list_cities(self) -> list[dict]:
        return [{"id": city_id, "name": info["name"]} for city_id, info in CITY_CATALOG.items()]

    def _load(self, city_id: str):
        city = CITY_CATALOG.get(city_id)
        if city is None:
            raise UnknownCityError(city_id)
        return load_cached_graph(city["cache_path"])

    def list_edges(self, city_id: str) -> list[dict]:
        """One entry per undirected road segment (a MultiDiGraph has a
        separate edge per direction, and sometimes parallel ways between
        the same two nodes -- deduped here since they render as the same
        visual line and Flow C selects a *segment*, not a direction)."""
        graph = self._load(city_id)
        seen: set[frozenset] = set()
        edges = []
        for u, v in graph.edges():
            pair = frozenset((u, v))
            if pair in seen:
                continue
            seen.add(pair)
            edges.append({
                "edge_id": f"{min(u, v)}_{max(u, v)}",
                "from_node_id": u,
                "to_node_id": v,
                "from_lat": graph.nodes[u]["y"],
                "from_lon": graph.nodes[u]["x"],
                "to_lat": graph.nodes[v]["y"],
                "to_lon": graph.nodes[v]["x"],
            })
        return edges

    def _load_with_accidents(self, city_id: str, accident_edges: Sequence[tuple[int, int]]):
        graph = self._load(city_id)
        pairs = {frozenset(e) for e in accident_edges}  # a repeated segment is delayed once, not x5 per repeat
        if pairs:
            graph = graph.copy()
            for u, v, data in graph.edges(data=True):
                if frozenset((u, v)) in pairs:
                    data["travel_time"] *= ACCIDENT_DELAY_MULTIPLIER
        return graph

    def build_matrices(
        self, city_id: str, nodes: list[Node], accident_edges: Sequence[tuple[int, int]] = ()
    ) -> tuple[np.ndarray, np.ndarray]:
        return build_distance_time_matrix(self._load_with_accidents(city_id, accident_edges), nodes)

    def accident_impacts(
        self,
        city_id: str,
        nodes: list[Node],
        sequences: list[list[str]],
        accident_edges: Sequence[tuple[int, int]],
    ) -> list[dict]:
        return build_accident_impacts(
            self._load(city_id), nodes, sequences, list(accident_edges), ACCIDENT_DELAY_MULTIPLIER
        )

    def route_leg_geometries(
        self,
        city_id: str,
        nodes: list[Node],
        sequences: list[list[str]],
        accident_edges: Sequence[tuple[int, int]] = (),
    ) -> list[list[list[list[float]]]]:
        return build_route_leg_geometries(
            self._load_with_accidents(city_id, accident_edges), nodes, sequences
        )
