import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

import numpy as np
from app.infrastructure.algorithms.qpso_solver import rov_map


def test_sorts_ascending_by_rank():
    position = np.array([0.5, -1.2, 3.7, 0.1])
    # ranks (ascending): -1.2 is smallest (index 1), then 0.1 (index 3), then 0.5 (index 0), then 3.7 (index 2)
    assert list(rov_map(position)) == [1, 3, 0, 2]


def test_single_element():
    assert list(rov_map(np.array([42.0]))) == [0]
