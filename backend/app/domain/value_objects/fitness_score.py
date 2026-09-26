from dataclasses import dataclass


@dataclass(frozen=True)
class FitnessScore:
    total: float
    distance_component: float
    time_component: float
    penalty_component: float
