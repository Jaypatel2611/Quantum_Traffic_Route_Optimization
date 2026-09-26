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
