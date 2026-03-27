"""
tools/registry.py — LangGraph Tool Registry for ArchAI

Each agent capability is surfaced as a LangChain @tool so:
  1. The LangGraph orchestrator can call them dynamically via ToolNode
  2. The MCP server can expose them as named MCP tools
  3. Any future agent can compose them without importing the full agent class

Categories:
  - geo        : Site & climate analysis
  - design     : Evolutionary DNA generation
  - layout     : Floor-plan generation
  - cost       : Cost estimation & ROI
  - compliance : FSI / zoning checks
  - sustain    : Solar, ventilation, water
  - memory     : Vector + Redis design memory
  - util       : Project helpers
"""
from __future__ import annotations

import json
import logging
import os
import sys
from typing import Any

# Ensure the backend root is on sys.path so imports like `from agents.x import y`
# resolve correctly both in the IDE and at runtime.
_BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BACKEND_ROOT not in sys.path:
    sys.path.insert(0, _BACKEND_ROOT)

from langchain_core.tools import tool  # type: ignore[import]  # noqa: E402

logger = logging.getLogger(__name__)



# ─────────────────────────────────────────────────────────────────────────────
# GEO TOOLS
# ─────────────────────────────────────────────────────────────────────────────

@tool
async def analyze_site(latitude: float, longitude: float, plot_area_sqm: float) -> str:
    """
    Analyse a construction site: zoning, FSI, road access, climate, solar
    orientation, and nearby amenities.

    Returns a JSON string with geo_data fields.
    """
    from agents.geo_agent import analyze_geo  # type: ignore[import]
    result = await analyze_geo(latitude=latitude, longitude=longitude, plot_area=plot_area_sqm)
    return json.dumps(result, default=str)


@tool
async def get_climate_data(latitude: float, longitude: float) -> str:
    """
    Fetch annual solar irradiance (kWh/m²/day) and rainfall (mm) for a location.
    Returns a JSON string with climate_data fields.
    """
    from agents.geo_agent import analyze_geo  # type: ignore[import]
    result = await analyze_geo(latitude=latitude, longitude=longitude, plot_area=500.0)
    climate = {
        "solar_irradiance_kwh_m2_day": result.get("solar_irradiance_kwh_m2_day"),
        "annual_rainfall_mm":          result.get("annual_rainfall_mm"),
        "optimal_solar_orientation":   result.get("optimal_solar_orientation"),
    }
    return json.dumps(climate)


# ─────────────────────────────────────────────────────────────────────────────
# DESIGN TOOLS
# ─────────────────────────────────────────────────────────────────────────────

@tool
async def generate_design_variants(
    plot_area_sqm: float,
    floors: int,
    budget_inr: int,
    style_preferences: list[str],
    latitude: float = 20.0,
    longitude: float = 78.0,
    num_variants: int = 3,
) -> str:
    """
    Run the evolutionary design engine to produce N unique Design DNA variants.

    Args:
        plot_area_sqm: Total plot size in square metres.
        floors: Number of floors.
        budget_inr: Total budget in Indian Rupees.
        style_preferences: List of style strings e.g. ['modern', 'vastu'].
        latitude: Site latitude (default: India centre).
        longitude: Site longitude (default: India centre).
        num_variants: How many variants to return (1-5).

    Returns JSON with a list of design variant dicts.
    """
    from core.evolutionary import evolve_designs, individual_to_dict  # type: ignore[import]
    ranked = await evolve_designs(
        plot_area=plot_area_sqm,
        floors=floors,
        budget=budget_inr,
        style_prefs=style_preferences,
        geo_data={"latitude": latitude, "longitude": longitude},
        population_size=max(num_variants * 2, 6),
        generations=2,
        survivors_per_gen=num_variants,
        final_variants=num_variants,
    )
    variants = [individual_to_dict(ind, i + 1) for i, ind in enumerate(ranked)]
    return json.dumps(variants, default=str)


@tool
async def score_design(dna: dict, plot_area_sqm: float, budget_inr: int) -> str:
    """
    Score a single Design DNA against fitness criteria (area efficiency,
    budget fit, style coherence).

    Returns JSON with score and breakdown.
    """
    from core.evolutionary import score_individual  # type: ignore[import]
    score, breakdown = score_individual(dna, plot_area_sqm, budget_inr)
    return json.dumps({"score": score, "breakdown": breakdown})


# ─────────────────────────────────────────────────────────────────────────────
# LAYOUT TOOLS
# ─────────────────────────────────────────────────────────────────────────────

@tool
async def generate_floor_plan(
    plot_area_sqm: float,
    floors: int,
    budget_inr: int,
    design_dna: dict | None = None,
    geo_data: dict | None = None,
) -> str:
    """
    Generate a detailed room-by-room floor plan for the given design parameters.

    Returns JSON with rooms, areas, SVG floor plan data, and unit_type.
    """
    from agents.layout_agent import generate_layout  # type: ignore[import]
    result = await generate_layout(
        plot_area_sqm=plot_area_sqm,
        floors=floors,
        budget_inr=budget_inr,
        design_dna=design_dna or {},
        geo_data=geo_data or {},
    )
    return json.dumps(result, default=str)


# ─────────────────────────────────────────────────────────────────────────────
# COST TOOLS
# ─────────────────────────────────────────────────────────────────────────────

@tool
async def estimate_construction_cost(
    plot_area_sqm: float,
    floors: int,
    budget_inr: int,
    design_dna: dict | None = None,
    geo_data: dict | None = None,
) -> str:
    """
    Estimate full construction cost breakdown and ROI for a building design.

    Returns JSON with total_cost_inr, cost_per_sqft, breakdown dict, and roi.
    """
    from agents.cost_agent import estimate_costs  # type: ignore[import]
    result = await estimate_costs(
        plot_area_sqm=plot_area_sqm,
        floors=floors,
        budget_inr=budget_inr,
        design_dna=design_dna or {},
        geo_data=geo_data or {},
    )
    return json.dumps(result, default=str)


# ─────────────────────────────────────────────────────────────────────────────
# COMPLIANCE TOOLS
# ─────────────────────────────────────────────────────────────────────────────

@tool
async def check_building_compliance(
    plot_area_sqm: float,
    floors: int,
    design_dna: dict | None = None,
    geo_data: dict | None = None,
) -> str:
    """
    Check if a building design is FSI-compliant and meets zoning regulations.

    Returns JSON with passed (bool), fsi_used, setback_compliance, issues list.
    """
    from agents.compliance_agent import check_compliance  # type: ignore[import]
    result = await check_compliance(
        plot_area_sqm=plot_area_sqm,
        floors=floors,
        design_dna=design_dna or {},
        geo_data=geo_data or {},
    )
    return json.dumps(result, default=str)


# ─────────────────────────────────────────────────────────────────────────────
# SUSTAINABILITY TOOLS
# ─────────────────────────────────────────────────────────────────────────────

@tool
async def analyze_sustainability(
    latitude: float,
    longitude: float,
    plot_area_sqm: float,
    floors: int,
    design_dna: dict | None = None,
    geo_data: dict | None = None,
) -> str:
    """
    Analyse solar potential, natural ventilation, rainwater harvesting,
    and overall green rating for a building design.

    Returns JSON with green_rating, green_score, and sub-metric breakdowns.
    """
    from agents.sustainability_agent import analyze_sustainability as _analyze  # type: ignore[import]
    result = await _analyze(
        latitude=latitude,
        longitude=longitude,
        plot_area_sqm=plot_area_sqm,
        floors=floors,
        design_dna=design_dna or {},
        geo_data=geo_data or {},
    )
    return json.dumps(result, default=str)


# ─────────────────────────────────────────────────────────────────────────────
# MEMORY TOOLS
# ─────────────────────────────────────────────────────────────────────────────

@tool
async def search_design_memory(query: str, top_k: int = 5) -> str:
    """
    Search the vector memory store for similar past architectural designs.

    Args:
        query: Natural-language description of the design you want to find.
        top_k: Number of results to return.

    Returns JSON list of matching design records with similarity scores.
    """
    try:
        from core.vector_memory import query_designs  # type: ignore[import]
        results = await query_designs(query=query, top_k=top_k)
        return json.dumps(results, default=str)
    except ImportError:
        return json.dumps({"error": "Vector memory not configured. Install qdrant-client."})
    except Exception as exc:
        logger.warning("search_design_memory failed: %s", exc)
        return json.dumps({"error": str(exc)})


@tool
async def store_design_to_memory(
    project_id: str,
    design_summary: str,
    dna: dict,
    score: float,
    user_id: str | None = None,
) -> str:
    """
    Store a completed design into the vector memory for future retrieval.

    Returns JSON with status and the vector ID assigned.
    """
    try:
        from core.vector_memory import store_design  # type: ignore[import]
        vector_id = await store_design(
            project_id=project_id,
            design_summary=design_summary,
            dna=dna,
            score=score,
            user_id=user_id,
        )
        return json.dumps({"status": "stored", "vector_id": vector_id})
    except ImportError:
        return json.dumps({"error": "Vector memory not configured. Install qdrant-client."})
    except Exception as exc:
        logger.warning("store_design_to_memory failed: %s", exc)
        return json.dumps({"error": str(exc)})


@tool
async def get_user_style_profile(user_id: str) -> str:
    """
    Retrieve a user's style preference profile learned from past design selections.

    Returns JSON with preferred_styles, generation_count, and top_style.
    """
    from core.memory_store import get_user_style_profile as _get_profile  # type: ignore[import]
    result = await _get_profile(user_id)
    return json.dumps(result)


# ─────────────────────────────────────────────────────────────────────────────
# UTIL TOOLS
# ─────────────────────────────────────────────────────────────────────────────

@tool
async def run_full_pipeline(
    project_id: str,
    latitude: float,
    longitude: float,
    plot_area_sqm: float,
    budget_inr: int,
    floors: int,
    style_preferences: list[str],
) -> str:
    """
    Run the complete ArchAI design pipeline for a project:
    geo → design evolution → layout + cost + compliance + sustainability (parallel).

    Returns a JSON summary of all agent outputs.
    """
    from agents.orchestrator import run_pipeline  # type: ignore[import]
    final = await run_pipeline(
        project_id=project_id,
        latitude=latitude,
        longitude=longitude,
        plot_area_sqm=plot_area_sqm,
        budget_inr=budget_inr,
        floors=floors,
        style_preferences=style_preferences,
    )
    # Return a lightweight summary (not full state with callbacks)
    summary = {
        "project_id":        project_id,
        "completed_agents":  final.get("completed_agents", []),
        "errors":            final.get("errors", []),
        "design_variants":   len(final.get("design_variants") or []),
        "best_score":        (final.get("design_variants") or [{}])[0].get("score"),
        "total_cost_inr":    (final.get("cost_data") or {}).get("total_cost_inr"),
        "compliance_passed": (final.get("compliance_data") or {}).get("passed"),
        "green_rating":      (final.get("sustainability_data") or {}).get("green_rating"),
    }
    return json.dumps(summary, default=str)


# ─────────────────────────────────────────────────────────────────────────────
# REGISTRY ASSEMBLY
# ─────────────────────────────────────────────────────────────────────────────

TOOL_REGISTRY: dict[str, Any] = {
    # Geo
    "analyze_site":               analyze_site,
    "get_climate_data":           get_climate_data,
    # Design
    "generate_design_variants":   generate_design_variants,
    "score_design":               score_design,
    # Layout
    "generate_floor_plan":        generate_floor_plan,
    # Cost
    "estimate_construction_cost": estimate_construction_cost,
    # Compliance
    "check_building_compliance":  check_building_compliance,
    # Sustainability
    "analyze_sustainability":     analyze_sustainability,
    # Memory
    "search_design_memory":       search_design_memory,
    "store_design_to_memory":     store_design_to_memory,
    "get_user_style_profile":     get_user_style_profile,
    # Util
    "run_full_pipeline":          run_full_pipeline,
}

_CATEGORIES: dict[str, list[str]] = {
    "geo":        ["analyze_site", "get_climate_data"],
    "design":     ["generate_design_variants", "score_design"],
    "layout":     ["generate_floor_plan"],
    "cost":       ["estimate_construction_cost"],
    "compliance": ["check_building_compliance"],
    "sustain":    ["analyze_sustainability"],
    "memory":     ["search_design_memory", "store_design_to_memory", "get_user_style_profile"],
    "util":       ["run_full_pipeline"],
}


def get_tool(name: str) -> Any:
    """Return a single tool by name, or raise KeyError."""
    return TOOL_REGISTRY[name]


def get_tools_by_category(category: str) -> list[Any]:
    """Return all tools in a category as a list suitable for ToolNode."""
    names = _CATEGORIES.get(category, [])
    return [TOOL_REGISTRY[n] for n in names if n in TOOL_REGISTRY]


def list_tools() -> list[dict]:
    """Return a manifest of all registered tools with name + description."""
    return [
        {
            "name":        name,
            "description": tool.description,
            "category":    next(
                (cat for cat, names in _CATEGORIES.items() if name in names),
                "uncategorized",
            ),
        }
        for name, tool in TOOL_REGISTRY.items()
    ]
