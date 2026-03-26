from pydantic import BaseModel
from typing import List, Optional

class DesignDNASchema(BaseModel):
    style: str = "contemporary"
    materials: List[str] = []
    color_palette: List[str] = []
    form_language: str = "rectilinear"
    sustainability_emphasis: float = 0.5
    seed: Optional[int] = None
