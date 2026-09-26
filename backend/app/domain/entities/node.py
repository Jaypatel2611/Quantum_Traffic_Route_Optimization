from dataclasses import dataclass

from app.domain.value_objects.geographic_coordinates import GeographicCoordinates


@dataclass
class Node:
    id: str
    coordinates: GeographicCoordinates
    demand: float = 0.0

    def __post_init__(self) -> None:
        if self.demand < 0:
            raise ValueError(f"demand must be >= 0, got {self.demand}")
