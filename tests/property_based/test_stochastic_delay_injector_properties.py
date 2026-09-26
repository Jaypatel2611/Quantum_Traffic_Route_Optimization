import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

import numpy as np
from app.infrastructure.geospatial.stochastic_delay_injector import inject_stochastic_delay


def test_same_seed_reproduces_identical_delays():
    """The fairness guarantee two phases from now (PRD Section 7) depends on this holding exactly."""
    base = np.array([[0, 60, 90], [120, 0, 45], [80, 30, 0]], dtype=float)
    result_a = inject_stochastic_delay(base, np.random.default_rng(123))
    result_b = inject_stochastic_delay(base, np.random.default_rng(123))
    assert np.array_equal(result_a, result_b)


def test_different_seeds_diverge():
    base = np.array([[0, 60, 90], [120, 0, 45], [80, 30, 0]], dtype=float)
    result_a = inject_stochastic_delay(base, np.random.default_rng(1))
    result_b = inject_stochastic_delay(base, np.random.default_rng(2))
    assert not np.array_equal(result_a, result_b)
