from fastapi import APIRouter, Depends

from app.application.interfaces.geospatial_repository_port import GeospatialRepositoryPort
from app.presentation.api.v1.dependencies import get_geospatial_repository
from app.presentation.schemas.optimize_response import CityResponse

router = APIRouter()


@router.get("/cities", response_model=list[CityResponse])
async def list_cities(
    repository: GeospatialRepositoryPort = Depends(get_geospatial_repository),
) -> list[dict]:
    return repository.list_cities()
