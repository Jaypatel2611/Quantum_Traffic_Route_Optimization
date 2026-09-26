from pathlib import Path

import osmnx as ox

# PRD Section 10 point 4's highway-type-conditioned defaults (residential ~30 km/h,
# primary/arterial ~60 km/h), passed explicitly because osmnx>=2.0 requires hwy_speeds/
# fallback whenever a graph has zero preexisting maxspeed tags (older versions applied
# a builtin default table automatically; this API tightened, PRD's bare
# `ox.add_edge_speeds(G)` snippet no longer runs unmodified against osmnx==2.1.1).
HWY_SPEEDS_KMH = {
    "motorway": 80,
    "trunk": 60,
    "primary": 60,
    "secondary": 50,
    "tertiary": 40,
    "residential": 30,
    "living_street": 20,
    "unclassified": 30,
}
FALLBACK_SPEED_KMH = 30


def fetch_and_cache_graph(place: str, cache_path: Path, max_place_area_km2: float = 50.0) -> None:
    """One-time, offline, dev-time fetch — never called at demo/runtime (PRD Section 8)."""
    gdf = ox.geocode_to_gdf(place)
    area_km2 = gdf.to_crs(gdf.estimate_utm_crs()).area.iloc[0] / 1_000_000
    if area_km2 > max_place_area_km2:
        raise ValueError(
            f"'{place}' resolves to {area_km2:.1f} km^2, too large "
            f"(cap {max_place_area_km2} km^2) — pass a city/district-scale place name (PRD Section 17)"
        )

    graph = ox.graph_from_place(place, network_type="drive")
    graph = ox.truncate.largest_component(graph, strongly=True)
    graph = ox.add_edge_speeds(graph, hwy_speeds=HWY_SPEEDS_KMH, fallback=FALLBACK_SPEED_KMH)
    graph = ox.add_edge_travel_times(graph)
    ox.save_graphml(graph, filepath=str(cache_path))


def load_cached_graph(cache_path: Path):
    """Zero-network load — the only path the running app ever takes (PRD Section 8)."""
    return ox.load_graphml(str(cache_path))
