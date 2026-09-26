from dataclasses import dataclass


@dataclass(frozen=True)
class CO2EmissionProfile:
    total_kg: float
    average_speed_kmh: float
    fuel_type: str = "diesel"
