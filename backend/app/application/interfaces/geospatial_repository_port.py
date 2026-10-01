from typing import Protocol

import numpy as np

from app.domain.entities.node import Node


class GeospatialRepositoryPort(Protocol):
    def list_cities(self) -> list[dict]:
        """Returns [{"id": ..., "name": ...}, ...] for every cached city."""
        ...

    def list_edges(self, city_id: str) -> list[dict]:
        """Returns one entry per undirected road segment: {"edge_id",
        "from_node_id", "to_node_id", "from_lat", "from_lon", "to_lat",
        "to_lon"} -- the Setup screen's Flow C accident-injection map
        renders and picks from these. Raises UnknownCityError for an
        unrecognized city_id."""
        ...

    def build_matrices(
        self, city_id: str, nodes: list[Node], accident_edge: tuple[int, int] | None = None
    ) -> tuple[np.ndarray, np.ndarray]:
        """Returns (distance_matrix, base_time_matrix) for the given nodes
        against city_id's cached road graph. When accident_edge (a pair of
        graph node ids from list_edges, order-independent) is given, that
        road segment's travel time is multiplied fivefold before the
        matrices are computed -- Flow C's accident injection. Raises
        UnknownCityError (app.domain.exceptions) for an unrecognized
        city_id -- never a bare KeyError, so the presentation layer can
        translate it to a clean 404/422 without knowing this port's
        internals."""
        ...

    def route_geometries(
        self, city_id: str, nodes: list[Node], sequences: list[list[str]]
    ) -> list[list[list[float]]]:
        """Returns one road-following [[lat, lon], ...] polyline per node-id
        sequence -- the shortest road path between each consecutive pair of
        stops, for drawing routes on the map. Raises UnknownCityError for an
        unrecognized city_id."""
        ...
