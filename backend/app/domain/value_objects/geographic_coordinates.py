from dataclasses import dataclass


@dataclass(frozen=True)
class GeographicCoordinates:
    lat: float
    lon: float

    def __post_init__(self) -> None:
        if not (-90.0 <= self.lat <= 90.0):
            raise ValueError(f"lat must be within [-90, 90], got {self.lat}")
        if not (-180.0 <= self.lon <= 180.0):
            raise ValueError(f"lon must be within [-180, 180], got {self.lon}")
