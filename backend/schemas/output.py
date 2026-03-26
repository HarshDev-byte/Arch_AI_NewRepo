from pydantic import BaseModel
from typing import Optional

class GenerationOutput(BaseModel):
    project_id: str
    model_url: Optional[str] = None
    floor_plan_svg: Optional[str] = None
    cost_estimate: Optional[dict] = None
    compliance_report: Optional[dict] = None
    sustainability_score: Optional[float] = None
