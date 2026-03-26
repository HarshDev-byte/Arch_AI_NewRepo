"""
cost_agent.py — Cost estimation agent.

Uses:
  - Rule-based breakdown (Indian 2024 construction rates)
  - Claude claude-3-haiku for intelligent ROI / market analysis
"""

from __future__ import annotations

import json
from typing import Any

from agents.base_agent import BaseAgent


class CostAgent(BaseAgent):
        def __init__(self, db=None, user_id: str | None = None):
                super().__init__("cost", user_id)

        async def run(self, project: dict) -> dict:
                return await self._call_llm_json(
                        prompt=f"""
Estimate construction costs for this Indian residential project:
    Plot area: {project.get('plot_area_sqm')} sq m
    Floors: {project.get('floors', 2)}
    Style: {project.get('style', 'modern')}
    City tier: {project.get('city_tier', 'tier2')}
    Budget: ₹{project.get('budget_inr', 3000000)}

Provide realistic Indian market rates (2024). Return JSON:
{{
    "cost_per_sqft_inr": 1800,
    "total_construction_inr": 2500000,
    "material_cost_inr": 1400000,
    "labour_cost_inr": 800000,
    "finishing_cost_inr": 300000,
    "contingency_inr": 150000,
    "timeline_months": 18,
    "roi_estimate_percent": 12,
    "cost_breakdown": {{
        "foundation": 15,
        "structure": 35,
        "walls_roof": 25,
        "finishes": 15,
        "mep": 10
    }},
    "budget_feasibility": "within_budget|10pct_over|significantly_over"
}}
""",
                        system="You are an expert construction cost estimator for Indian real estate."
                )



# ─────────────────────────────────────────────────────────────────────────────
# Rate tables (INR per sqft, 2024)
# ─────────────────────────────────────────────────────────────────────────────

CONSTRUCTION_RATES = {
    "budget":   {"rate_per_sqft": 1_200, "label": "Economy Construction"},
    "standard": {"rate_per_sqft": 1_800, "label": "Standard Construction"},
    "premium":  {"rate_per_sqft": 2_800, "label": "Premium Construction"},
    "luxury":   {"rate_per_sqft": 4_500, "label": "Luxury Construction"},
}

BREAKDOWN_RATIOS = {
    "civil_structure":    0.35,
    "brickwork_plaster":  0.12,
    "flooring":           0.08,
    "doors_windows":      0.07,
    "electrical":         0.06,
    "plumbing_sanitary":  0.05,
    "painting_finishing": 0.06,
    "false_ceiling":      0.04,
    "kitchen_modular":    0.08,
    "contingency":        0.09,
}


# ─────────────────────────────────────────────────────────────────────────────
# Core estimation
# ─────────────────────────────────────────────────────────────────────────────

async def estimate_costs(
    plot_area_sqm: float,
    floors: int,
    budget_inr: int,
    geo_data: dict[str, Any],
    design_dna: dict[str, Any],
    user_id: str | None = None,
) -> dict[str, Any]:

    built_up_sqm_per_floor = float(design_dna.get("built_up_area", plot_area_sqm * 0.55))
    total_built_up_sqm     = built_up_sqm_per_floor * floors
    built_up_sqft          = total_built_up_sqm * 10.764

    # Quality tier from budget intensity
    cost_per_sqft_available = budget_inr / built_up_sqft if built_up_sqft else 0
    if cost_per_sqft_available < 1_500:   tier = "budget"
    elif cost_per_sqft_available < 2_500: tier = "standard"
    elif cost_per_sqft_available < 4_000: tier = "premium"
    else:                                  tier = "luxury"

    rate = CONSTRUCTION_RATES[tier]["rate_per_sqft"]
    base = built_up_sqft * rate

    breakdown = {k: round(base * v) for k, v in BREAKDOWN_RATIOS.items()}
    total_construction = sum(breakdown.values())
    cost_per_sqft_actual = round(total_construction / built_up_sqft, 2) if built_up_sqft else rate

    # ── Claude ROI analysis ────────────────────────────────────────────────
    address = geo_data.get("location_context", {}).get("address", {})
    city    = address.get("city") or address.get("town") or "India"
    amenity_count = geo_data.get("nearby_amenities", {}).get("total", {}).get("count", 0)

    roi_data = await _get_roi_from_claude(
        city=city,
        plot_area_sqm=plot_area_sqm,
        built_up_sqm=total_built_up_sqm,
        floors=floors,
        tier=tier,
        total_investment=total_construction,
        amenity_count=amenity_count,
        user_id=user_id,
    )

    return {
        "tier":                  tier,
        "tier_label":            CONSTRUCTION_RATES[tier]["label"],
        "built_up_sqft":         round(built_up_sqft),
        "built_up_sqm":          round(total_built_up_sqm, 2),
        "rate_per_sqft":         rate,
        "cost_per_sqft_actual":  cost_per_sqft_actual,
        "breakdown":             breakdown,
        "total_cost_inr":        total_construction,
        "roi":                   roi_data,
    }


async def _get_roi_from_claude(
    city: str,
    plot_area_sqm: float,
    built_up_sqm: float,
    floors: int,
    tier: str,
    total_investment: int,
    amenity_count: int,
    user_id: str | None = None,
) -> dict[str, Any]:

    prompt = f"""You are a real estate financial analyst in India.
Analyse this property investment and provide ROI estimates.

Location: {city}
Plot Area: {plot_area_sqm:.0f} sqm ({plot_area_sqm * 10.764:.0f} sqft)
Built-up Area: {built_up_sqm:.0f} sqm
Floors: {floors}
Construction Quality: {tier}
Total Investment: ₹{total_investment:,}
Nearby Amenity Density: {amenity_count} nodes within 500m

Respond with ONLY this JSON (no markdown, no explanation):
{{
  "estimated_land_value_per_sqm": <number>,
  "estimated_rental_per_month": <number>,
  "resale_value_3yr": <number>,
  "resale_value_5yr": <number>,
  "rental_roi_percent": <number>,
  "appreciation_rate_percent": <number>,
  "recommendation": "<2-3 sentence string>",
  "risk_level": "low|medium|high"
}}"""

    try:
        base = BaseAgent("cost", user_id)
        text = await base._call_llm(prompt)
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        return json.loads(text)
    except Exception:
        # Sensible rule-based fallback
        monthly_rental = round(total_investment * 0.003)
        return {
            "estimated_land_value_per_sqm":  50_000,
            "estimated_rental_per_month":    monthly_rental,
            "resale_value_3yr":              round(total_investment * 1.4),
            "resale_value_5yr":              round(total_investment * 1.8),
            "rental_roi_percent":            4.2,
            "appreciation_rate_percent":     8.5,
            "recommendation":                "Good investment based on location and construction quality.",
            "risk_level":                    "medium",
        }


# ─────────────────────────────────────────────────────────────────────────────
# Agent entry-point
# ─────────────────────────────────────────────────────────────────────────────

async def run(project_id: str, context: dict[str, Any]) -> dict[str, Any]:
    result = await estimate_costs(
        plot_area_sqm = float(context.get("plot_area_sqm",  1000.0)),
        floors        = int(  context.get("floors",         2)),
        budget_inr    = int(  context.get("budget_inr",     5_000_000)),
        geo_data      = dict( context.get("geo_data",       {})),
        design_dna    = dict( context.get("best_dna",       {})),
        user_id       = context.get("user_id"),
    )
    return {"cost_estimate": result, **result}
