import numpy as np


def rov_map(position: np.ndarray) -> np.ndarray:
    """Rank-Order Value mapping (PRD Section 9): sorts the continuous position
    vector and returns the resulting rank order as a discrete node-visit
    permutation. Validity is a structural property of argsort, not something
    the fitness function needs to check."""
    return np.argsort(position)


def split_into_routes(permutation: np.ndarray, num_vehicles: int) -> list[list[int]]:
    """Divides the giant tour into num_vehicles fixed, equal-ish contiguous
    chunks (user-approved encoding, PRD Section 9's particle stays R^N with
    no extra split-point genes)."""
    n = len(permutation)
    base_size, remainder = divmod(n, num_vehicles)
    routes = []
    start = 0
    for vehicle in range(num_vehicles):
        size = base_size + (1 if vehicle < remainder else 0)
        routes.append(permutation[start:start + size].tolist())
        start += size
    return routes


def capacity_penalty(
    routes: list[list[int]], demands: list[float], vehicle_capacity: float, lam: float
) -> float:
    """PRD Section 12's dynamic scaling penalty: an over-capacity route is
    never discarded, just penalized proportional to the squared violation."""
    total = 0.0
    for route in routes:
        load = sum(demands[i] for i in route)
        violation = max(0.0, load - vehicle_capacity)
        total += lam * violation**2
    return total
