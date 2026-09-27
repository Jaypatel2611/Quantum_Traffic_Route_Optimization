from fastapi import APIRouter, Depends, HTTPException

from app.application.interfaces.geospatial_repository_port import GeospatialRepositoryPort
from app.domain.exceptions import UnknownCityError
from app.presentation.api.v1.dependencies import get_geospatial_repository
from app.presentation.schemas.optimize_response import CityResponse, EdgeResponse

router = APIRouter()


@router.get("/cities", response_model=list[CityResponse])
async def list_cities(
    repository: GeospatialRepositoryPort = Depends(get_geospatial_repository),
) -> list[dict]:
    return repository.list_cities()


@router.get("/cities/{city_id}/edges", response_model=list[EdgeResponse])
async def list_edges(
    city_id: str, repository: GeospatialRepositoryPort = Depends(get_geospatial_repository)
) -> list[dict]:
    """Flow C's accident-injection map picks an edge from this list -- the
    graph-edge API gap flagged as missing since Phase 6."""
    try:
        return repository.list_edges(city_id)
    except UnknownCityError as exc:
        raise HTTPException(status_code=404, detail=f"unknown city_id: {city_id!r}") from exc
