from dataclasses import dataclass


@dataclass
class Route:
    vehicle_id: str
    node_sequence: list[str]
    total_distance_m: float
    total_time_s: float
