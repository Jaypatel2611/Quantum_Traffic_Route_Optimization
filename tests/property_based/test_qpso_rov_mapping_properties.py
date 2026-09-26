import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

import numpy as np
from hypothesis import given
from hypothesis import strategies as st
from app.infrastructure.algorithms.qpso_solver import rov_map


@given(st.lists(st.floats(allow_nan=False, allow_infinity=False, width=32), min_size=1, max_size=50))
def test_rov_always_produces_a_valid_permutation(values):
    """PRD Section 14: ROV mapping, for any input vector of length N, always
    produces a permutation of {0, ..., N-1} with no duplicates and no omissions."""
    position = np.array(values)
    result = rov_map(position)
    assert sorted(result.tolist()) == list(range(len(values)))
