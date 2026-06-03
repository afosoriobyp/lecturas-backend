from pydantic import BaseModel, Field


class GPSPoint(BaseModel):
    lat: float = Field(..., ge=-90, le=90)
    lng: float = Field(..., ge=-180, le=180)
    altitude: float | None = None
    accuracy: float | None = Field(None, ge=0, le=100)
