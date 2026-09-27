from pathlib import Path

import numpy as np

from app.domain.entities.node import Node
from app.domain.exceptions import UnknownCityError
from app.infrastructure.geospatial.distance_matrix_builder import build_distance_time_matrix
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


class CachedGraphRepository:
    """GeospatialRepositoryPort implementation over the offline-cached
    OSMnx graphs (PRD Section 8: zero-network at runtime). Real Phase-7
    implementation of what was a stub since Phase 0/1's scaffolding."""

    def list_cities(self) -> list[dict]:
        return [{"id": city_id, "name": info["name"]} for city_id, info in CITY_CATALOG.items()]

    def build_matrices(self, city_id: str, nodes: list[Node]) -> tuple[np.ndarray, np.ndarray]:
        city = CITY_CATALOG.get(city_id)
        if city is None:
            raise UnknownCityError(city_id)
        graph = load_cached_graph(city["cache_path"])
        return build_distance_time_matrix(graph, nodes)
