"""
compliance_agent.py — Building code compliance checker.

Standards applied (approximate):
  - UDCPR 2020  (Maharashtra Unified Development Control & Promotion Regulations)
  - NBC 2016    (National Building Code of India)
  - General Indian municipal norms
"""

from __future__ import annotations

from typing import Any
from agents.base_agent import BaseAgent  # type: ignore


async def check_compliance(
    plot_area_sqm: float,
    floors: int,
    design_dna: dict[str, Any],
    geo_data: dict[str, Any],
) -> dict[str, Any]:

    fsi_allowed          = float(geo_data.get("fsi_allowed", 1.5))
    built_up_per_floor   = float(design_dna.get("built_up_area", plot_area_sqm * 0.55))
    total_built_up       = built_up_per_floor * floors
    fsi_used             = total_built_up / plot_area_sqm if plot_area_sqm else 0.0

    setback_front        = float(design_dna.get("setback_front",  3.0))
    setback_side         = float(design_dna.get("setback_sides",  1.5))
    floor_height         = float(design_dna.get("floor_height",   3.0))

    issues:   list[str] = []
    warnings: list[str] = []

    # ── FSI ───────────────────────────────────────────────────────────────────
    fsi_ok = fsi_used <= fsi_allowed
    if not fsi_ok:
        overshoot = (fsi_used - fsi_allowed) * plot_area_sqm
        issues.append(
            f"FSI violation: used {fsi_used:.2f}, allowed {fsi_allowed:.2f}. "
            f"Reduce built-up area by {overshoot:.0f} sqm."
        )

    # ── Setbacks (UDCPR 2020) ─────────────────────────────────────────────────
    front_required = 3.0 if plot_area_sqm < 500 else 4.5
    side_required  = 1.5 if plot_area_sqm < 500 else 2.25

    setback_ok = True
    if setback_front < front_required:
        issues.append(
            f"Front setback insufficient: {setback_front:.1f} m provided, "
            f"{front_required} m required."
        )
        setback_ok = False
    if setback_side < side_required:
        issues.append(
            f"Side setback insufficient: {setback_side:.1f} m provided, "
            f"{side_required} m required."
        )
        setback_ok = False

    # ── Building height (NBC 2016) ────────────────────────────────────────────
    max_height_m = floors * floor_height
    if floors <= 4:
        height_ok = max_height_m <= 15.0
    else:
        height_ok = max_height_m <= 24.0

    if not height_ok:
        warnings.append(
            f"Building height {max_height_m:.1f} m may require special fire-NOC "
            f"and structural clearance."
        )

    # ── Parking (1 space per 100 sqm BUA) ────────────────────────────────────
    parking_required = max(1, int(total_built_up / 100))

    # ── Green / open area (≥15 % of plot) ────────────────────────────────────
    green_required  = plot_area_sqm * 0.15
    # Approximate open land = plot − ground footprint − front setback strip
    open_land       = plot_area_sqm - built_up_per_floor - (setback_front * 5.0)
    green_available = max(0.0, open_land)
    green_ok        = green_available >= green_required

    if not green_ok:
        warnings.append(
            f"Insufficient open/green area: {green_available:.0f} sqm available, "
            f"{green_required:.0f} sqm required (15 % norm)."
        )

    # ── Solar access (shading coefficient advisory) ───────────────────────────
    shading = float(design_dna.get("shading_coefficient", 0.5))
    if shading < 0.3:
        warnings.append(
            "Low shading coefficient — consider passive cooling devices "
            "(brise-soleil, jaali) for thermal comfort compliance."
        )

    # ── Fire safety advisory for high-rise ───────────────────────────────────
    if floors >= 4:
        warnings.append(
            f"Building ≥ {floors} storeys — mandatory fire exit staircase, "
            f"fire-rated doors, and smoke detection system (NBC Part 4)."
        )

    passed = len(issues) == 0

    return {
        "passed":                    passed,
        "fsi_used":                  float(f"{fsi_used:.3f}"),
        "fsi_allowed":               fsi_allowed,
        "fsi_ok":                    fsi_ok,
        "setback_compliance": {
            "front_provided_m":      setback_front,
            "front_required_m":      front_required,
            "side_provided_m":       setback_side,
            "side_required_m":       side_required,
            "ok":                    setback_ok,
        },
        "height_compliance": {
            "max_height_m":          float(f"{max_height_m:.1f}"),
            "ok":                    height_ok,
        },
        "parking_required":          parking_required,
        "green_area": {
            "required_sqm":          float(f"{green_required:.1f}"),
            "available_sqm":         float(f"{green_available:.1f}"),
            "ok":                    green_ok,
        },
        "issues":                    issues,
        "warnings":                  warnings,
        "standards_reference":       "UDCPR 2020 / NBC 2016 (approximate)",
    }


class ComplianceAgent(BaseAgent):
    def __init__(self, db=None, user_id: str | None = None):
        super().__init__("compliance", user_id)  # type: ignore

    async def run(self, project: dict) -> dict:
        return await self._call_llm_json(
            prompt=f"""
Check building plan compliance for Indian regulations (UDCPR / NBC 2016).
Plot area: {project.get('plot_area_sqm')} sqm
Built-up area: {project.get('built_up_sqm', project.get('plot_area_sqm', 100) * 1.5)} sqm
Floors: {project.get('floors', 2)}
City: {project.get('city', 'Pune')}
State: {project.get('state', 'Maharashtra')}

Return JSON with compliance fields.
""",
            system="You are an expert in Indian building codes — UDCPR, NBC 2016, local municipal rules."
        )


# ─────────────────────────────────────────────────────────────────────────────
# Agent entry-point
# ─────────────────────────────────────────────────────────────────────────────

async def run(project_id: str, context: dict[str, Any]) -> dict[str, Any]:
    result = await check_compliance(
        plot_area_sqm = float(context.get("plot_area_sqm", 1000.0)),
        floors        = int(  context.get("floors",        2)),
        design_dna    = dict( context.get("best_dna",      {})),
        geo_data      = dict( context.get("geo_data",      {})),
    )
    return {"compliance": result, **result}
