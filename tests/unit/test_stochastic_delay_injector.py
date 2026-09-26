import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

import numpy as np
from app.infrastructure.geospatial.stochastic_delay_injector import inject_stochastic_delay


def test_output_shape_matches_input():
    base = np.array([[0, 60], [120, 0]], dtype=float)
    rng = np.random.default_rng(42)
    result = inject_stochastic_delay(base, rng)
    assert result.shape == base.shape


def test_delayed_times_are_never_shorter_than_base():
    base = np.array([[0, 60], [120, 0]], dtype=float)
    rng = np.random.default_rng(42)
    result = inject_stochastic_delay(base, rng)
    assert np.all(result >= base)


def test_diagonal_stays_zero():
    base = np.array([[0, 60], [120, 0]], dtype=float)
    rng = np.random.default_rng(42)
    result = inject_stochastic_delay(base, rng)
    assert result[0, 0] == 0
    assert result[1, 1] == 0
