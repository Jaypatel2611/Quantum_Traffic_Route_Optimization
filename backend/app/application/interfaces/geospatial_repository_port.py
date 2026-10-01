from collections.abc import Sequence
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
        self, city_id: str, nodes: list[Node], accident_edges: Sequence[tuple[int, int]] = ()
    ) -> tuple[np.ndarray, np.ndarray]:
        """Returns (distance_matrix, base_time_matrix) for the given nodes
        against city_id's cached road graph. Every pair in accident_edges
        (graph node ids from list_edges, order-independent) has its road
        segment's travel time multiplied fivefold before the matrices are
        computed -- Flow C's accident injection, any number at once. Raises
        UnknownCityError (app.domain.exceptions) for an unrecognized
        city_id -- never a bare KeyError, so the presentation layer can
        translate it to a clean 404/422 without knowing this port's
        internals."""
        ...

    def accident_impacts(
        self,
        city_id: str,
        nodes: list[Node],
        sequences: list[list[str]],
        accident_edges: Sequence[tuple[int, int]],
    ) -> list[dict]:
        """One {"from_node_id", "to_node_id", "status", "added_time_s"} per
        accident, in order, judged against the routes' stop order. status is
        "not_on_route", "rerouted" or "driven_through". Raises
        UnknownCityError for an unrecognized city_id."""
        ...

    def route_leg_geometries(
        self,
        city_id: str,
        nodes: list[Node],
        sequences: list[list[str]],
        accident_edges: Sequence[tuple[int, int]] = (),
    ) -> list[list[list[list[float]]]]:
        """Returns, per node-id sequence, one road-following [[lat, lon], ...]
        polyline per leg (consecutive stop pair) -- the fastest road path,
        for drawing routes on the map. accident_edges (same meaning as
        build_matrices) makes the paths detour around blocked segments.
        Raises UnknownCityError for an unrecognized city_id."""
        ...
