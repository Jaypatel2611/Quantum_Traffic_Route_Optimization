import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

import numpy as np
from app.infrastructure.algorithms.qpso_solver import reinitialize_stagnant_particles


def test_reinitializes_worst_20_percent_by_personal_best_fitness():
    rng = np.random.default_rng(0)
    positions = np.array([[1.0, 2.0], [3.0, 4.0], [5.0, 6.0], [7.0, 8.0], [9.0, 10.0]])

    class _Score:
        def __init__(self, total):
            self.total = total

    pbest_fitness = [_Score(t) for t in [1.0, 5.0, 2.0, 4.0, 3.0]]  # worst 20% (1 particle) = index 1 (total=5.0)
    new_positions, reinit_indices = reinitialize_stagnant_particles(
        positions, pbest_fitness, rng, fraction=0.2
    )
    assert reinit_indices == [1]
    assert not np.array_equal(new_positions[1], positions[1])
    # untouched particles keep their positions
    for i in [0, 2, 3, 4]:
        assert np.array_equal(new_positions[i], positions[i])
