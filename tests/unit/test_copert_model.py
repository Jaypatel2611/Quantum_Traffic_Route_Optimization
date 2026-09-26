import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

import pytest
from app.infrastructure.algorithms.copert_model import emission_factor_g_per_km, EMISSION_FACTOR_SOURCE


def test_source_is_documented_not_silent():
    assert "European" in EMISSION_FACTOR_SOURCE
    assert "EMEP" in EMISSION_FACTOR_SOURCE or "COPERT" in EMISSION_FACTOR_SOURCE


@pytest.mark.parametrize(
    "speed_kmh,expected_g_per_km",
    [
        (10.0, 248.01),   # low-speed/idle-adjacent band
        (75.09, 133.18726951),  # the curve's true minimum (v = 4.07 / (2*0.0271))
        (130.0, 214.89),  # highway band
    ],
)
def test_known_reference_values(speed_kmh, expected_g_per_km):
    """PRD Section 14: unit tests against known reference values for at
    least three speed bands (idle, cruise, highway) -- hand-computed
    directly from the sourced formula's own coefficients."""
    assert emission_factor_g_per_km(speed_kmh) == pytest.approx(expected_g_per_km, abs=1e-4)


def test_clamps_below_validated_range():
    # formula validated for [10, 130]; a speed of 2 km/h clamps to 10's value
    assert emission_factor_g_per_km(2.0) == emission_factor_g_per_km(10.0)


def test_clamps_above_validated_range():
    assert emission_factor_g_per_km(200.0) == emission_factor_g_per_km(130.0)
