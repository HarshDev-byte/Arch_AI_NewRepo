"""
geo_agent.py — Geospatial analysis agent.

Uses FREE public APIs only:
  - Nominatim     (OpenStreetMap) — reverse geocoding
  - Overpass API  (OpenStreetMap) — nearby buildings, roads, amenities
  - OpenTopoData  (SRTM 90m)     — elevation
  - Open-Meteo                   — solar radiation, climate
"""

from __future__ import annotations

import asyncio
import math
from typing import Any

import httpx

OVERPASS_URL       = "https://overpass-api.de/api/interpreter"
NOMINATIM_URL      = "https://nominatim.openstreetmap.org"
OPENTOPODATA_URL   = "https://api.opentopodata.org/v1/srtm90m"
OPEN_METEO_URL     = "https://api.open-meteo.com/v1"

# Cities in India with higher FSI norms
_HIGH_FSI_CITIES = {"mumbai", "delhi", "bangalore", "bengaluru", "chennai", "hyderabad", "pune"}


# ─────────────────────────────────────────────────────────────────────────────
# Sub-tasks
# ─────────────────────────────────────────────────────────────────────────────

async def _get_location_context(client: httpx.AsyncClient, lat: float, lon: float) -> dict:
    resp = await client.get(
        f"{NOMINATIM_URL}/reverse",
        params={"lat": lat, "lon": lon, "format": "json", "zoom": 16},
        headers={"User-Agent": "ArchAI/1.0 (archai.dev)"},
    )
    resp.raise_for_status()
    return resp.json()


async def _get_elevation(client: httpx.AsyncClient, lat: float, lon: float) -> float:
    resp = await client.get(f"{OPENTOPODATA_URL}?locations={lat},{lon}")
    resp.raise_for_status()
    data = resp.json()
    return float(data["results"][0]["elevation"])


async def _get_solar_data(client: httpx.AsyncClient, lat: float, lon: float) -> dict:
    resp = await client.get(
        f"{OPEN_METEO_URL}/forecast",
        params={
            "latitude":    lat,
            "longitude":   lon,
            "daily":       "shortwave_radiation_sum,precipitation_sum",
            "timezone":    "auto",
            "forecast_days": 7,
        },
    )
    resp.raise_for_status()
    data = resp.json()
    daily = data.get("daily", {})

    radiation_vals = daily.get("shortwave_radiation_sum", [])
    precip_vals    = daily.get("precipitation_sum", [])

    avg_radiation_kwh = (sum(radiation_vals) / len(radiation_vals) / 1000) if radiation_vals else 5.0
    avg_precip_mm     = (sum(precip_vals) / len(precip_vals)) if precip_vals else 2.0

    return {
        "avg_daily_radiation_kwh_m2": round(avg_radiation_kwh, 3),
        "avg_daily_precip_mm": round(avg_precip_mm, 2),
        # Annualise precipitation for water harvesting calc
        "annual_rainfall_mm": round(avg_precip_mm * 365),
    }


async def _get_nearby_amenities(client: httpx.AsyncClient, lat: float, lon: float, radius: int = 500) -> dict:
    query = f"""
[out:json][timeout:15];
(
  node["amenity"](around:{radius},{lat},{lon});
  way["building"](around:{radius},{lat},{lon});
  way["highway"](around:{radius},{lat},{lon});
  node["shop"](around:{radius},{lat},{lon});
  node["leisure"](around:{radius},{lat},{lon});
);
out count;
"""
    resp = await client.post(OVERPASS_URL, data={"data": query})
    resp.raise_for_status()
    data = resp.json()
    count = data.get("total", {}).get("count", 0)
    return {"total": {"count": count}, "radius_m": radius}


async def _get_road_access(client: httpx.AsyncClient, lat: float, lon: float) -> dict:
    query = f"""
[out:json][timeout:10];
way["highway"](around:100,{lat},{lon});
out tags;
"""
    resp = await client.post(OVERPASS_URL, data={"data": query})
    resp.raise_for_status()
    data = resp.json()
    roads = [e.get("tags", {}) for e in data.get("elements", [])]
    types = list({r.get("highway", "unknown") for r in roads})
    return {
        "roads": roads[:5],
        "count": len(roads),
        "road_types": types,
        "primary_access": types[0] if types else "unknown",
    }


# ─────────────────────────────────────────────────────────────────────────────
# Derived estimations
# ─────────────────────────────────────────────────────────────────────────────

def _estimate_zoning(amenities: dict) -> str:
    count = amenities.get("total", {}).get("count", 0) if isinstance(amenities, dict) else 0
    if count > 50: return "commercial_mixed"
    if count > 20: return "residential_urban"
    return "residential_suburban"


def _estimate_fsi(location_ctx: dict) -> float:
    address = location_ctx.get("address", {}) if isinstance(location_ctx, dict) else {}
    city = (address.get("city") or address.get("town") or "").lower()
    if city in _HIGH_FSI_CITIES:
        return 2.5
    if address.get("state") in ("Maharashtra", "Karnataka", "Tamil Nadu"):
        return 2.0
    return 1.5


def _optimal_solar_orientation(lat: float) -> float:
    """South-facing in northern hemisphere, North-facing in southern."""
    return 180.0 if lat >= 0 else 0.0


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

async def analyze_geo(
    latitude: float,
    longitude: float,
    plot_area: float,
) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=30.0) as client:
        results = await asyncio.gather(
            _get_location_context(client, latitude, longitude),
            _get_elevation(client, latitude, longitude),
            _get_nearby_amenities(client, latitude, longitude),
            _get_solar_data(client, latitude, longitude),
            _get_road_access(client, latitude, longitude),
            return_exceptions=True,
        )

    location_ctx, elevation, amenities, solar, roads = results

    def _safe(val: Any, default: Any) -> Any:
        return default if isinstance(val, BaseException) else val

    solar_dict   = _safe(solar,    {"avg_daily_radiation_kwh_m2": 5.0, "annual_rainfall_mm": 800})
    amenities_d  = _safe(amenities, {"total": {"count": 0}})
    location_d   = _safe(location_ctx, {})
    roads_d      = _safe(roads, {"roads": [], "count": 0})

    return {
        "latitude":              latitude,
        "longitude":             longitude,
        "plot_area":             plot_area,
        "location_context":      location_d,
        "elevation_m":           _safe(elevation, 0.0),
        "nearby_amenities":      amenities_d,
        "solar_irradiance_kwh_m2_day": solar_dict.get("avg_daily_radiation_kwh_m2", 5.0),
        "annual_rainfall_mm":    solar_dict.get("annual_rainfall_mm", 800),
        "road_access":           roads_d,
        "optimal_solar_orientation": _optimal_solar_orientation(latitude),
        "zoning_type":           _estimate_zoning(amenities_d),
        "fsi_allowed":           _estimate_fsi(location_d),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Class-based agent wrapper (keeps function API for backwards compatibility)
# ─────────────────────────────────────────────────────────────────────────────

from agents.base_agent import BaseAgent


class GeoAgent(BaseAgent):
    """Uses OpenStreetMap + Nominatim — NO API KEY NEEDED."""
    def __init__(self, db=None, user_id: str | None = None):
        super().__init__("geo", user_id)

    async def run(self, project: dict) -> dict:
        lat = project.get("lat") or project.get("latitude")
        lng = project.get("lng") or project.get("longitude")
        address = project.get("address", "")

        if address and not (lat and lng):
            lat, lng = await self._geocode(address)

        osm_data = await self._fetch_osm(lat, lng) if lat else {}
        elevation = await self._fetch_elevation(lat, lng) if lat else 0
        solar_data = await self._fetch_solar(lat, lng) if lat else {}

        analysis = await self._call_llm_json(
            prompt=f"""
Analyze this plot location for architectural suitability.
Location: lat={lat}, lng={lng}
OSM data: {osm_data}
Elevation: {elevation}m
Solar data: {solar_data}

Return JSON:
{{
  "zoning_type": "residential|commercial|mixed",
  "flood_risk": "low|medium|high",
  "sun_orientation": "north|south|east|west|northeast|...",
  "nearby_amenities": ["school", "hospital", ...],
  "access_roads": true/false,
  "recommended_setback_m": 3,
  "plot_grade": "A|B|C",
  "summary": "brief 1-sentence summary"
}}
""",
            system="You are an expert geo-analyst for architectural site assessment."
        )
        return {**analysis, "lat": lat, "lng": lng, "elevation_m": elevation, "solar": solar_data}


# Backwards-compatible function
async def run(project_id: str, context: dict[str, Any]) -> dict[str, Any]:
    lat = float(context.get("latitude", 20.0))
    lon = float(context.get("longitude", 78.0))
    area = float(context.get("plot_area_sqm", 1000.0))
    result = await analyze_geo(lat, lon, area)
    return {"geo_data": result, **result}
