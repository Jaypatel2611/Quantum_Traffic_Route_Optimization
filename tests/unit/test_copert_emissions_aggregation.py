import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

import pytest
from app.domain.entities.route import Route
from app.infrastructure.algorithms.copert_model import (
    route_emissions, total_emissions_kg, co2_reduction_percent,
)


def test_route_emissions_uses_average_speed():
    # 10 km at a steady pace taking 600s (10 minutes) -> 60 km/h average
    route = Route(vehicle_id="v0", node_sequence=["depot", "n1", "depot"], total_distance_m=10_000.0, total_time_s=600.0)
    profile = route_emissions(route)
    assert profile.average_speed_kmh == pytest.approx(60.0)
    # EF(60) = 286 - 4.07*60 + 0.0271*3600 = 286 - 244.2 + 97.56 = 139.36 g/km, over 10 km
    assert profile.total_kg == pytest.approx(139.36 * 10 / 1000, abs=1e-4)


def test_total_emissions_sums_across_routes():
    r1 = Route(vehicle_id="v0", node_sequence=["depot", "n1", "depot"], total_distance_m=10_000.0, total_time_s=600.0)
    r2 = Route(vehicle_id="v1", node_sequence=["depot", "n2", "depot"], total_distance_m=5_000.0, total_time_s=300.0)
    total = total_emissions_kg([r1, r2])
    assert total == pytest.approx(route_emissions(r1).total_kg + route_emissions(r2).total_kg)


def test_reduction_percent_positive_means_optimized_emits_less():
    """Sign convention: positive = improvement (QPSO/optimized route emits
    less than the baseline) -- a flipped sign would invert the sustainability
    claim silently on a judge-facing number."""
    assert co2_reduction_percent(baseline_kg=100.0, optimized_kg=80.0) == pytest.approx(20.0)


def test_reduction_percent_negative_means_optimized_emits_more():
    assert co2_reduction_percent(baseline_kg=100.0, optimized_kg=120.0) == pytest.approx(-20.0)


def test_unused_vehicle_route_emits_zero_not_nan():
    """An unused vehicle (0 distance, 0 time -- e.g. QPSO's split leaving a
    vehicle idle because that's cheaper) must not divide 0/0 into NaN: a
    NaN float serializes to JSON `null`, corrupting the whole CO2 payload.
    Found live via the bigger demo-scenario verification, not a test."""
    unused = Route(vehicle_id="v3", node_sequence=["depot", "depot"], total_distance_m=0.0, total_time_s=0.0)
    profile = route_emissions(unused)
    assert profile.total_kg == 0.0
    assert not str(profile.total_kg) == "nan"


def test_total_emissions_sums_across_routes_including_an_unused_one():
    r1 = Route(vehicle_id="v0", node_sequence=["depot", "n1", "depot"], total_distance_m=10_000.0, total_time_s=600.0)
    unused = Route(vehicle_id="v1", node_sequence=["depot", "depot"], total_distance_m=0.0, total_time_s=0.0)
    assert total_emissions_kg([r1, unused]) == pytest.approx(route_emissions(r1).total_kg)
