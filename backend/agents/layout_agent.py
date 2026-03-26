"""
layout_agent.py — Layout planning agent.

Uses Claude claude-3-5-sonnet to generate an intelligent room layout JSON,
then renders it as an inline SVG floor plan.
"""

from __future__ import annotations

import json
import re
from typing import Any

from agents.base_agent import BaseAgent
import math


class LayoutAgent(BaseAgent):
    def __init__(self, db=None, user_id: str | None = None):
        super().__init__("layout", user_id)

    async def run(self, project: dict) -> dict:
        plot_area = project.get('plot_area_sqm', 100.0)
        floors = project.get('floors', 2)
        built_up_per_floor = float((project.get('best_dna') or {}).get('built_up_area', plot_area * 0.55))
        if built_up_per_floor < 80:
            unit_type = '2bhk'
        elif built_up_per_floor < 130:
            unit_type = '3bhk'
        else:
            unit_type = '4bhk'

        prompt = f"""
Generate an optimized floor plan layout for a {project.get('style','modern')} home.
Plot area: {plot_area} sqm
Floors: {floors}
Unit type: {unit_type}

Return JSON with rooms array and floor_plan dimensions.
"""
        return await self._call_llm_json(prompt=prompt, system="You are an expert Indian residential architect.")



# ─────────────────────────────────────────────────────────────────────────────
# Room programs by unit type
# ─────────────────────────────────────────────────────────────────────────────

ROOM_PROGRAMS: dict[str, list[str]] = {
    "2bhk": [
        "living", "dining", "kitchen",
        "master_bedroom", "bedroom_2",
        "bathroom_1", "bathroom_2", "balcony",
    ],
    "3bhk": [
        "living", "dining", "kitchen",
        "master_bedroom", "bedroom_2", "bedroom_3",
        "bathroom_1", "bathroom_2", "bathroom_3",
        "utility", "balcony_1", "balcony_2",
    ],
    "4bhk": [
        "living", "dining", "kitchen",
        "master_bedroom", "bedroom_2", "bedroom_3", "bedroom_4",
        "bathroom_1", "bathroom_2", "bathroom_3",
        "study", "utility", "balcony_1", "balcony_2",
    ],
}

ROOM_COLORS: dict[str, str] = {
    "living":      "#E8F4FD",
    "dining":      "#FDF5E8",
    "kitchen":     "#FDE8E8",
    "bedroom":     "#E8FDE8",
    "bathroom":    "#F0E8FD",
    "balcony":     "#D4F5D4",
    "utility":     "#F5F5F5",
    "circulation": "#FAFAFA",
    "study":       "#FFF8E8",
    "default":     "#F0F0F0",
}


# ─────────────────────────────────────────────────────────────────────────────
# SVG generator
# ─────────────────────────────────────────────────────────────────────────────

def generate_floor_plan_svg(floor_plan: dict[str, Any], floor_number: int = 0) -> str:
    scale   = 30    # px per metre
    padding = 40

    fp_width  = float(floor_plan.get("width_m",  10.0))
    fp_depth  = float(floor_plan.get("depth_m",  12.0))
    width_px  = fp_width  * scale + padding * 2
    depth_px  = fp_depth * scale + padding * 2

    parts: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{width_px:.0f}" height="{depth_px:.0f}" '
        f'viewBox="0 0 {width_px:.0f} {depth_px:.0f}">',
        "<defs>"
        '<filter id="shadow"><feDropShadow dx="1" dy="1" stdDeviation="1" flood-opacity="0.15"/></filter>'
        "</defs>",
        f'<rect width="100%" height="100%" fill="#FAFAFA"/>',
        # Outer building outline
        f'<rect x="{padding}" y="{padding}" '
        f'width="{fp_width * scale:.1f}" height="{fp_depth * scale:.1f}" '
        f'fill="none" stroke="#222" stroke-width="3" rx="2"/>',
        # North arrow
        f'<text x="{width_px - 24}" y="24" text-anchor="middle" '
        f'font-family="sans-serif" font-size="10" fill="#666">N ↑</text>',
        # Floor label
        f'<text x="{padding}" y="{padding - 8}" '
        f'font-family="sans-serif" font-size="11" font-weight="bold" fill="#444">'
        f'Floor {floor_number}</text>',
    ]

    rooms_on_floor = [
        r for r in floor_plan.get("rooms", [])
        if int(r.get("floor", 0)) == floor_number
    ]

    for room in rooms_on_floor:
        rx = padding + float(room.get("x",     0)) * scale
        ry = padding + float(room.get("y",     0)) * scale
        rw =           float(room.get("width", 3)) * scale
        rd =           float(room.get("depth", 3)) * scale

        rtype = room.get("type", "default")
        color = ROOM_COLORS.get(rtype, ROOM_COLORS["default"])
        label = room.get("name", rtype).replace("_", " ").title()
        w_m   = float(room.get("width", 0))
        d_m   = float(room.get("depth", 0))
        dim   = f"{w_m:.1f}×{d_m:.1f}m"

        font_size = max(7, min(11, int(rw / 9)))

        parts += [
            f'<rect x="{rx:.1f}" y="{ry:.1f}" width="{rw:.1f}" height="{rd:.1f}" '
            f'fill="{color}" stroke="#AAAAAA" stroke-width="0.8" filter="url(#shadow)" rx="1"/>',
            # Room name
            f'<text x="{rx + rw/2:.1f}" y="{ry + rd/2 - font_size/2:.1f}" '
            f'text-anchor="middle" dominant-baseline="central" '
            f'font-family="Inter,sans-serif" font-size="{font_size}" fill="#333">'
            f'{label}</text>',
            # Dimension
            f'<text x="{rx + rw/2:.1f}" y="{ry + rd/2 + font_size:.1f}" '
            f'text-anchor="middle" font-family="sans-serif" font-size="7" fill="#888">'
            f'{dim}</text>',
        ]

    parts.append("</svg>")
    return "\n".join(parts)


# ─────────────────────────────────────────────────────────────────────────────
# Layout generation
# ─────────────────────────────────────────────────────────────────────────────

async def generate_layout(
    plot_area_sqm: float,
    floors: int,
    budget_inr: int,
    design_dna: dict[str, Any],
    geo_data: dict[str, Any],
    user_id: str | None = None,
) -> dict[str, Any]:

    built_up_per_floor = float(design_dna.get("built_up_area", plot_area_sqm * 0.55))

    if   built_up_per_floor < 80:  unit_type = "2bhk"
    elif built_up_per_floor < 130: unit_type = "3bhk"
    else:                           unit_type = "4bhk"

    rooms = ROOM_PROGRAMS[unit_type]

    prompt = f"""You are a senior residential architect practising in India.
Generate an optimised floor plan layout as JSON.

Plot:  {plot_area_sqm:.0f} sqm total, {built_up_per_floor:.0f} sqm built-up per floor
Floors: {floors}
Unit type: {unit_type.upper()}
Building form: {design_dna.get('building_form', 'rectangular')}
Solar orientation: {design_dna.get('solar_orientation', 180):.0f}°
Open-plan ratio: {design_dna.get('open_plan_ratio', 0.5):.1f}
Has courtyard: {design_dna.get('courtyard_presence', False)}
Rooms to include: {rooms}

Respond with ONLY valid JSON (no markdown fences):
{{
  "unit_type": "{unit_type}",
  "floor_plan": {{
    "width_m": <number>,
    "depth_m": <number>,
    "rooms": [
      {{
        "name": "<string>",
        "type": "living|bedroom|kitchen|bathroom|balcony|utility|circulation|study",
        "x": <metres from left>,
        "y": <metres from front>,
        "width": <metres>,
        "depth": <metres>,
        "floor": <0|1|2|...>,
        "features": ["<feature>"]
      }}
    ]
  }},
  "circulation": {{
    "staircase_x": <number>,
    "staircase_y": <number>,
    "main_entrance_x": <number>
  }},
  "highlights": ["<highlight 1>", "<highlight 2>", "<highlight 3>"]
}}"""

    try:
        base = BaseAgent("layout", user_id)
        raw = await base._call_llm(prompt)
        raw = raw.strip()
        raw = re.sub(r"^```(?:json)?", "", raw).rstrip("`").strip()
        layout_data = json.loads(raw)
    except Exception:
        # Fallback: generate a simple rectangular grid layout
        layout_data = _fallback_layout(unit_type, rooms, built_up_per_floor, floors)

    # Render SVG for each floor
    svgs: dict[str, str] = {}
    for f in range(floors):
        svgs[f"floor_{f}"] = generate_floor_plan_svg(layout_data.get("floor_plan", {}), floor_number=f)

    layout_data["floor_plan_svgs"] = svgs
    layout_data["floor_plan_svg"]  = svgs.get("floor_0", "")   # primary SVG
    return layout_data


def _fallback_layout(unit_type: str, rooms: list[str], bua: float, floors: int) -> dict:
    """Simple grid layout fallback — used if Claude call fails."""
    cols = 3
    cell_w = max(3.0, round((bua ** 0.5) / cols, 1))
    cell_d = cell_w

    layout_rooms = []
    for i, name in enumerate(rooms):
        rtype = (
            "bedroom" if "bedroom" in name else
            "bathroom" if "bathroom" in name else
            "balcony" if "balcony" in name else
            name.split("_")[0]
        )
        layout_rooms.append({
            "name": name, "type": rtype,
            "x": (i % cols) * cell_w,
            "y": (i // cols) * cell_d,
            "width": cell_w, "depth": cell_d,
            "floor": 0, "features": [],
        })

    return {
        "unit_type": unit_type,
        "floor_plan": {
            "width_m": cols * cell_w,
            "depth_m": ((len(rooms) // cols) + 1) * cell_d,
            "rooms": layout_rooms,
        },
        "circulation": {"staircase_x": 0, "staircase_y": 0, "main_entrance_x": cell_w},
        "highlights": ["Auto-generated layout (Claude unavailable)"],
    }


# ─────────────────────────────────────────────────────────────────────────────
# Agent entry-point
# ─────────────────────────────────────────────────────────────────────────────

async def run(project_id: str, context: dict[str, Any]) -> dict[str, Any]:
    result = await generate_layout(
        plot_area_sqm = float(context.get("plot_area_sqm", 1000.0)),
        floors        = int(  context.get("floors",        2)),
        budget_inr    = int(  context.get("budget_inr",    5_000_000)),
        design_dna    = dict( context.get("best_dna",      {})),
        geo_data      = dict( context.get("geo_data",      {})),
        user_id       = context.get("user_id"),
    )
    return {"layout": result, **result}
