"""
sustainability_agent.py — Eco analysis agent.

Integrates:
  - PVGIS API (free, EU JRC) — solar generation estimate
  - Rule-based ventilation, shading, water harvesting scores
  - Green rating (Platinum / Gold / Silver / Bronze)
"""

from __future__ import annotations

from typing import Any
import httpx
from agents.base_agent import BaseAgent

PVGIS_URL = "https://re.jrc.ec.europa.eu/api/v5_2/PVcalc"


# ─────────────────────────────────────────────────────────────────────────────
# PVGIS solar estimate
# ─────────────────────────────────────────────────────────────────────────────

async def _get_pvgis_data(lat: float, lon: float, panel_area: float) -> dict[str, Any]:
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(
                PVGIS_URL,
                params={
                    "lat":           lat,
                    "lon":           lon,
                    "peakpower":     round(panel_area * 0.2, 2),   # ~200 W/sqm
                    "loss":          14,
                    "outputformat":  "json",
                    "mountingplace": "building",
                    "optimalangles": 1,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            annual_kwh = (
                data.get("outputs", {})
                    .get("totals", {})
                    .get("fixed", {})
                    .get("E_y", panel_area * 1_400)
            )
            solar_score = min(100.0, float(annual_kwh) / max(1, panel_area * 15))
            return {"annual_kwh": round(float(annual_kwh)), "solar_score": round(solar_score, 1)}
    except Exception:
        # Fallback: use ~1 400 kWh/kWp rule-of-thumb for India
        return {"annual_kwh": round(panel_area * 1_400), "solar_score": 75.0}


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

_VENTILATION_SCORES: dict[str, int] = {
    "cross_ventilation": 95,
    "courtyard_draft":   90,
    "stack_effect":      85,
    "wind_catcher":      80,
}

def _score_to_rating(score: float) -> str:
    if score >= 85: return "Platinum"
    if score >= 70: return "Gold"
    if score >= 55: return "Silver"
    return "Bronze"


def _generate_recommendations(dna: dict[str, Any], geo: dict[str, Any]) -> list[str]:
    recs: list[str] = []
    if float(dna.get("shading_coefficient", 0.5)) < 0.4:
        recs.append(
            "Add brise-soleil or jaali screens to reduce solar heat gain by 25–35 %."
        )
    if not dna.get("courtyard_presence"):
        recs.append(
            "Consider a central courtyard for natural ventilation and diffused daylight."
        )
    if float(dna.get("window_wall_ratio", 0.4)) > 0.6:
        recs.append(
            "High glazing ratio detected — specify double-glazed low-e glass to cut heat gain."
        )
    recs.append("Install rainwater harvesting — estimated saving: ₹12,000 / year.")
    recs.append("Rooftop solar can offset 60–80 % of electricity consumption.")
    return recs


# ─────────────────────────────────────────────────────────────────────────────
# Core analysis
# ─────────────────────────────────────────────────────────────────────────────

async def analyze_sustainability(
    latitude: float,
    longitude: float,
    plot_area_sqm: float,
    floors: int,
    design_dna: dict[str, Any],
    geo_data: dict[str, Any],
) -> dict[str, Any]:

    roof_area       = float(design_dna.get("built_up_area", plot_area_sqm * 0.55))
    panel_area      = roof_area * 0.6           # 60 % of roof usable

    solar_data      = await _get_pvgis_data(latitude, longitude, panel_area)

    strategy        = design_dna.get("natural_ventilation_strategy", "cross_ventilation")
    ventilation_score = _VENTILATION_SCORES.get(strategy, 70)

    shading_coeff   = float(design_dna.get("shading_coefficient", 0.5))
    cooling_reduction = shading_coeff * 30      # % reduction in cooling load

    rainfall_mm_yr  = float(geo_data.get("annual_rainfall_mm", 800))
    rainwater_kl    = (roof_area * rainfall_mm_yr * 0.8) / 1_000    # 80 % efficiency

    green_score = round(
        solar_data["solar_score"]  * 0.30 +
        ventilation_score          * 0.30 +
        (shading_coeff * 100)      * 0.20 +
        min(100.0, rainwater_kl * 5) * 0.20
    )

    annual_kwh      = solar_data["annual_kwh"]
    electricity_rate = 8.0   # INR / kWh

    return {
        "green_score":  green_score,
        "green_rating": _score_to_rating(green_score),
        "solar": {
            "panel_area_sqm":         round(panel_area, 1),
            "annual_generation_kwh":  annual_kwh,
            "monthly_savings_inr":    round(annual_kwh / 12 * electricity_rate),
            "payback_years":          round(
                (panel_area * 4_000) / max(1, annual_kwh * electricity_rate), 1
            ),
        },
        "ventilation": {
            "strategy":               strategy,
            "effectiveness_score":    ventilation_score,
            "ac_reduction_percent":   round(ventilation_score * 0.4),
        },
        "shading": {
            "coefficient":                 round(shading_coeff, 3),
            "cooling_load_reduction_percent": round(cooling_reduction),
        },
        "water": {
            "rainwater_potential_kl_yr": round(rainwater_kl),
            "greywater_recycling":       bool(
                design_dna.get("sustainability_features", {}).get("greywater", False)
            ),
        },
        "recommendations": _generate_recommendations(design_dna, geo_data),
    }


class SustainabilityAgent(BaseAgent):
    """Uses Open-Meteo + PVGIS for real data — NO API KEY."""
    def __init__(self, db=None, user_id: str | None = None):
        super().__init__("sustainability", user_id)

    async def run(self, project: dict) -> dict:
        lat = project.get('lat', 20.0)
        lng = project.get('lng', 78.0)
        weather = await self._fetch_weather(lat, lng)
        return await self._call_llm_json(
            prompt=f"""
Generate sustainability recommendations for a {project.get('style','modern')} home.
Location: lat={lat}, lng={lng}
Climate: {weather}
Plot area: {project.get('plot_area_sqm')} sqm
Floors: {project.get('floors', 2)}
Roof area: {project.get('plot_area_sqm', 100) * 0.7} sqm (approx)

Return JSON with solar, water and green_score recommendations.
""",
            system="You are a sustainable architecture and green building expert for Indian climate zones."
        )


# ─────────────────────────────────────────────────────────────────────────────
# Agent entry-point
# ─────────────────────────────────────────────────────────────────────────────

async def run(project_id: str, context: dict[str, Any]) -> dict[str, Any]:
    result = await analyze_sustainability(
        latitude      = float(context.get("latitude",      20.0)),
        longitude     = float(context.get("longitude",     78.0)),
        plot_area_sqm = float(context.get("plot_area_sqm", 1000.0)),
        floors        = int(  context.get("floors",        2)),
        design_dna    = dict( context.get("best_dna",      {})),
        geo_data      = dict( context.get("geo_data",      {})),
    )
    return {"sustainability": result, **result}
