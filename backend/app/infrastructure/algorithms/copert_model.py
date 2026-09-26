from app.domain.value_objects.co2_emission_profile import CO2EmissionProfile

# Source: EMEP/EEA Air Pollutant Emission Inventory Guidebook-derived COPERT
# formula for diesel passenger cars < 2.5t, valid speed range 10-130 km/h.
# Verified via three independent web searches converging on the same
# citation (2026-09-27) -- not recalled from memory, per the project's
# rule against unsourced figures on a judge-facing sustainability number.
#
# CAVEAT, stated explicitly (not silent): these coefficients are
# CALIBRATED ON THE EUROPEAN VEHICLE FLEET, not Indian vehicles.
# India-specific ARAI/CPCB coefficients were not located within this
# prototype's timeframe (flagged as a V2 dependency) -- the PRD's own
# Section 13 research finding. User-decided (2026-09-27): use this real,
# verifiable curve as-is rather than compound it with a second, unsourced
# India-specific fuel-economy assumption. The primary reported metric is
# therefore the RELATIVE % CO2 reduction between routes under this one
# standardized methodology, not the absolute kg figure.
EMISSION_FACTOR_SOURCE = (
    "EMEP/EEA Guidebook COPERT formula, diesel passenger car <2.5t, "
    "European-fleet-calibrated (ARAI/CPCB India-specific coefficients: V2 dependency)"
)

_A, _B, _C = 286.0, -4.07, 0.0271
_MIN_VALID_SPEED_KMH = 10.0
_MAX_VALID_SPEED_KMH = 130.0


def emission_factor_g_per_km(speed_kmh: float) -> float:
    """CO2 g/km as a function of average speed. Clamped to the formula's
    validated range -- extrapolating a fitted quadratic outside where it
    was published for is not defensible."""
    v = min(max(speed_kmh, _MIN_VALID_SPEED_KMH), _MAX_VALID_SPEED_KMH)
    return _A + _B * v + _C * v**2


def route_emissions(route) -> CO2EmissionProfile:
    """ponytail: route-average-speed approximation (not per-edge EF(v)
    integration) -- Phase 1's matrices are aggregated point-to-point sums,
    not retained edge paths. Upgrade path: per-edge integration if
    distance_matrix_builder starts tracking the path."""
    distance_km = route.total_distance_m / 1000
    average_speed_kmh = distance_km / (route.total_time_s / 3600)
    total_kg = emission_factor_g_per_km(average_speed_kmh) * distance_km / 1000
    return CO2EmissionProfile(total_kg=total_kg, average_speed_kmh=average_speed_kmh)


def total_emissions_kg(routes) -> float:
    return sum(route_emissions(r).total_kg for r in routes)


def co2_reduction_percent(baseline_kg: float, optimized_kg: float) -> float:
    """Positive = optimized route emits less than baseline (an improvement)."""
    return (baseline_kg - optimized_kg) / baseline_kg * 100
