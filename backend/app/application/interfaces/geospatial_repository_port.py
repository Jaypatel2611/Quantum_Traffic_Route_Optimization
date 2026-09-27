from typing import Protocol

import numpy as np

from app.domain.entities.node import Node


class GeospatialRepositoryPort(Protocol):
    def list_cities(self) -> list[dict]:
        """Returns [{"id": ..., "name": ...}, ...] for every cached city."""
        ...

    def build_matrices(self, city_id: str, nodes: list[Node]) -> tuple[np.ndarray, np.ndarray]:
        """Returns (distance_matrix, base_time_matrix) for the given nodes
        against city_id's cached road graph. Raises UnknownCityError
        (app.domain.exceptions) for an unrecognized city_id -- never a bare
        KeyError, so the presentation layer can translate it to a clean
        404/422 without knowing this port's internals."""
        ...
