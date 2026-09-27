import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

import pytest
from app.domain.entities.route import Route
from app.application.services.green_impact_calculator import (
    algorithm_result_payload,
    compute_green_impact,
)
from app.infrastructure.algorithms.copert_model import route_emissions

_BASELINE = [Route(vehicle_id="v0", node_sequence=["depot", "n1", "depot"], total_distance_m=10_000.0, total_time_s=600.0)]
_OPTIMIZED = [Route(vehicle_id="v0", node_sequence=["depot", "n1", "depot"], total_distance_m=8_000.0, total_time_s=480.0)]


def test_compute_green_impact_reports_qpso_savings_vs_ortools_baseline():
    impact = compute_green_impact(ortools_routes=_BASELINE, qpso_routes=_OPTIMIZED)
    baseline_kg = route_emissions(_BASELINE[0]).total_kg
    optimized_kg = route_emissions(_OPTIMIZED[0]).total_kg

    assert impact["co2_saved_kg"] == pytest.approx(baseline_kg - optimized_kg)
    assert impact["co2_saved_kg"] > 0  # optimized route is shorter and faster
    assert impact["fuel_saved_liters"] == pytest.approx(impact["co2_saved_kg"] / 2.68)
    assert impact["time_saved_s"] == pytest.approx(600.0 - 480.0)
    assert "COPERT" in impact["emission_factor_source"]


def test_algorithm_result_payload_shapes_routes_meta_and_totals():
    payload = algorithm_result_payload(_BASELINE, meta={"seed": 42})
    assert payload["routes"] == _BASELINE
    assert payload["meta"] == {"seed": 42}
    assert payload["total_time_s"] == 600.0
    assert payload["total_co2_kg"] == pytest.approx(route_emissions(_BASELINE[0]).total_kg)
