import numpy as np


def rov_map(position: np.ndarray) -> np.ndarray:
    """Rank-Order Value mapping (PRD Section 9): sorts the continuous position
    vector and returns the resulting rank order as a discrete node-visit
    permutation. Validity is a structural property of argsort, not something
    the fitness function needs to check."""
    return np.argsort(position)
