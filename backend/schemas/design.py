from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class DesignDNASchema(BaseModel):
    style: str = "contemporary"
    materials: List[str] = []
    color_palette: List[str] = []
    form_language: str = "rectilinear"
    sustainability_emphasis: float = 0.5
    seed: Optional[int] = None

class Room(BaseModel):
    id: str
    name: str
    type: str
    x: float = Field(..., description="X position in metres")
    y: float = Field(..., description="Y position in metres") 
    w: float = Field(..., description="Width in metres")
    h: float = Field(..., description="Height in metres")
    floor: int = Field(default=0, description="Floor number (0-indexed)")
    rotation: Optional[float] = Field(default=0, description="Rotation in degrees")

class FloorPlanUpdate(BaseModel):
    rooms: List[Room]
    metadata: Optional[Dict[str, Any]] = None
