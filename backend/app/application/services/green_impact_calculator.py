from app.infrastructure.algorithms.copert_model import co2_reduction_percent, total_emissions_kg

FUEL_CO2_FACTOR_KG_PER_LITER = 2.68
"""Diesel combustion: ~2.68 kg CO2 per liter burned (standard IPCC/EPA
default road-transport factor, the same family this project's COPERT-proxy
already relies on) -- used only to convert an already-computed CO2 delta
into a liters-saved figure, never as an independent emissions source."""

EMISSION_FACTOR_SOURCE = (
    "EMEP/EEA Guidebook COPERT formula (European-fleet-calibrated; "
    "India-specific ARAI/CPCB coefficients not yet available -- V2 dependency). "
    f"Fuel-saved liters derived from the CO2 delta via a standard "
    f"{FUEL_CO2_FACTOR_KG_PER_LITER} kgCO2/liter diesel combustion factor "
    "(IPCC/EPA default), not an independent measurement."
)


def compute_green_impact(ortools_routes: list, qpso_routes: list) -> dict:
    """QPSO (`qpso_routes`) is compared against the OR-Tools baseline
    (`ortools_routes`) -- positive figures mean QPSO used/emitted less."""
    ortools_co2_kg = total_emissions_kg(ortools_routes)
    qpso_co2_kg = total_emissions_kg(qpso_routes)
    ortools_time_s = sum(r.total_time_s for r in ortools_routes)
    qpso_time_s = sum(r.total_time_s for r in qpso_routes)
    co2_saved_kg = ortools_co2_kg - qpso_co2_kg

    return {
        "co2_saved_kg": co2_saved_kg,
        "co2_reduction_percent": co2_reduction_percent(ortools_co2_kg, qpso_co2_kg),
        "fuel_saved_liters": co2_saved_kg / FUEL_CO2_FACTOR_KG_PER_LITER,
        "time_saved_s": ortools_time_s - qpso_time_s,
        "emission_factor_source": EMISSION_FACTOR_SOURCE,
    }


def algorithm_result_payload(routes: list, meta: dict) -> dict:
    return {
        "routes": routes,
        "meta": meta,
        "total_co2_kg": total_emissions_kg(routes),
        "total_time_s": sum(r.total_time_s for r in routes),
    }
