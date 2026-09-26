from dataclasses import dataclass


@dataclass
class Vehicle:
    id: str
    capacity: float
    fuel_type: str = "diesel"

    def __post_init__(self) -> None:
        if self.capacity <= 0:
            raise ValueError(f"capacity must be > 0, got {self.capacity}")
