class UnknownCityError(Exception):
    """Raised by a GeospatialRepositoryPort implementation when asked for a
    city_id that isn't in its catalog (Phase 7)."""
