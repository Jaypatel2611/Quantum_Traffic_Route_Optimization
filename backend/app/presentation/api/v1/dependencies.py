from app.application.interfaces.geospatial_repository_port import GeospatialRepositoryPort
from app.application.services.optimization_orchestrator import OptimizationOrchestrator
from app.infrastructure.geospatial.cached_graph_repository import CachedGraphRepository

# Module-level singletons, shared across every router (and main.py's own
# legacy /jobs endpoint) so a job created by one endpoint is visible to
# /jobs/{id}/stream and /jobs/{id}/result regardless of which endpoint
# created it. Mirrors Phase 5's original main.py-level singleton exactly --
# moved here so the routers don't import from main (which would import
# main.py's own routes back into itself).
orchestrator = OptimizationOrchestrator()
geospatial_repository: GeospatialRepositoryPort = CachedGraphRepository()


def get_orchestrator() -> OptimizationOrchestrator:
    return orchestrator


def get_geospatial_repository() -> GeospatialRepositoryPort:
    return geospatial_repository
