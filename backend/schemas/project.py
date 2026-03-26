"""Pydantic schemas for Project CRUD and generation requests."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


# ─────────────────────────────────────────────────────────────────────────────
# Project schemas
# ─────────────────────────────────────────────────────────────────────────────

class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    plot_area_sqm: Optional[float] = Field(None, gt=0)
    budget_inr: Optional[int] = Field(None, gt=0)
    floors: int = Field(2, ge=1, le=50)
    style_preferences: list[str] = []


class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    plot_area_sqm: Optional[float] = Field(None, gt=0)
    budget_inr: Optional[int] = Field(None, gt=0)
    floors: Optional[int] = Field(None, ge=1, le=50)
    style_preferences: Optional[list[str]] = None
    status: Optional[str] = None


class DesignVariantOut(BaseModel):
    id: uuid.UUID
    variant_number: Optional[int]
    dna: Optional[dict[str, Any]]
    score: Optional[float]
    is_selected: bool
    floor_plan_svg: Optional[str]
    model_url: Optional[str]
    thumbnail_url: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class CostEstimateOut(BaseModel):
    id: uuid.UUID
    breakdown: Optional[dict[str, Any]]
    total_cost_inr: Optional[int]
    cost_per_sqft: Optional[float]
    roi_estimate: Optional[dict[str, Any]]
    land_value_estimate: Optional[int]
    created_at: datetime

    model_config = {"from_attributes": True}


class GeoAnalysisOut(BaseModel):
    id: uuid.UUID
    plot_data: Optional[dict[str, Any]]
    zoning_type: Optional[str]
    fsi_allowed: Optional[float]
    road_access: Optional[dict[str, Any]]
    nearby_amenities: Optional[dict[str, Any]]
    elevation_profile: Optional[dict[str, Any]]
    solar_irradiance: Optional[float]
    wind_data: Optional[dict[str, Any]]
    created_at: datetime

    model_config = {"from_attributes": True}


class ComplianceCheckOut(BaseModel):
    id: uuid.UUID
    fsi_used: Optional[float]
    fsi_allowed: Optional[float]
    setback_compliance: Optional[dict[str, Any]]
    height_compliance: Optional[bool]
    parking_required: Optional[int]
    green_area_required: Optional[float]
    issues: list[Any]
    passed: Optional[bool]
    created_at: datetime

    model_config = {"from_attributes": True}


class AgentRunOut(BaseModel):
    id: uuid.UUID
    agent_name: str
    status: str
    input_data: Optional[dict[str, Any]]
    output_data: Optional[dict[str, Any]]
    error_message: Optional[str]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime

    model_config = {"from_attributes": True}


class ProjectResponse(BaseModel):
    id: uuid.UUID
    name: str
    status: str
    latitude: Optional[float]
    longitude: Optional[float]
    plot_area_sqm: Optional[float]
    budget_inr: Optional[int]
    floors: int
    style_preferences: list[Any]
    design_seed: Optional[str]
    design_dna: Optional[dict[str, Any]]
    share_token: Optional[str] = None
    is_public: bool = False
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProjectDetailResponse(ProjectResponse):
    """Full project with all related data."""
    agent_runs: list[AgentRunOut] = []
    design_variants: list[DesignVariantOut] = []
    cost_estimate: Optional[CostEstimateOut] = None
    geo_analysis: Optional[GeoAnalysisOut] = None
    compliance_check: Optional[ComplianceCheckOut] = None

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────────────────────────────────────
# Generation schemas
# ─────────────────────────────────────────────────────────────────────────────

class GenerationStartRequest(BaseModel):
    project_id: uuid.UUID
    latitude: float
    longitude: float
    plot_area_sqm: float = Field(..., gt=0)
    budget_inr: int = Field(..., gt=0)
    floors: int = Field(2, ge=1, le=50)
    style_preferences: list[str] = []


class GenerationStartResponse(BaseModel):
    task_id: str
    project_id: uuid.UUID
    status: str = "started"
    message: str


class AgentStatusItem(BaseModel):
    name: str
    status: str          # pending | running | complete | error
    progress: int = 0    # 0–100
    output: Optional[dict[str, Any]] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class GenerationStatusResponse(BaseModel):
    project_id: uuid.UUID
    project_status: str
    agents: list[AgentStatusItem]


class CustomizeRequest(BaseModel):
    changed_inputs: dict[str, Any]
    agents_to_rerun: list[str]      # e.g. ["cost", "compliance"]


class SelectVariantRequest(BaseModel):
    pass   # variant_id comes from the path


class SelectVariantResponse(BaseModel):
    variant_id: uuid.UUID
    project_id: uuid.UUID
    message: str = "Variant selected successfully"
