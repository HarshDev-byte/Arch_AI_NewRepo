"""
layout_agent.py — Layout planning agent.

Uses Gemini to generate an intelligent room layout JSON,
then renders it as an inline SVG floor plan.
"""

from __future__ import annotations

import json
import re
import sys
import os
from typing import Any

# Ensure the backend root is on sys.path so the import works both when run
# directly and when called from uvicorn (which sets cwd to backend/).
_BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BACKEND_ROOT not in sys.path:
    sys.path.insert(0, _BACKEND_ROOT)

from agents.base_agent import BaseAgent  # noqa: E402


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

    fp_width  = float(floor_plan.get("width_m",  10.0) or 10.0)
    fp_depth  = float(floor_plan.get("depth_m",  12.0) or 12.0)
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
        rw =           float(room.get("width", room.get("w", 3))) * scale
        rd =           float(room.get("depth", room.get("h", 3))) * scale

        rtype = str(room.get("type", "default"))
        color = ROOM_COLORS.get(rtype, ROOM_COLORS["default"])
        label = str(room.get("name", rtype)).replace("_", " ").title()
        w_m   = float(room.get("width", room.get("w", 0)))
        d_m   = float(room.get("depth", room.get("h", 0)))
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
# Fallback layout generator (used if LLM is unavailable)
# ─────────────────────────────────────────────────────────────────────────────

def _fallback_layout(unit_type: str, rooms: list[str], bua: float, floors: int) -> dict[str, Any]:
    """Simple grid layout fallback — rooms distributed evenly across floors."""
    rooms_per_floor = max(1, len(rooms) // floors)
    cols = 3
    cell_w = max(3.0, round((bua ** 0.5) / cols, 1))
    cell_d = cell_w

    layout_rooms: list[dict[str, Any]] = []
    for i, name in enumerate(rooms):
        rtype: str = (
            "bedroom"  if "bedroom"  in name else
            "bathroom" if "bathroom" in name else
            "balcony"  if "balcony"  in name else
            name.split("_")[0]
        )

        # Evenly distribute across floors
        floor_idx   = min(floors - 1, i // rooms_per_floor)
        pos_on_floor = i % rooms_per_floor

        layout_rooms.append({
            "name":    name,
            "type":    rtype,
            "x":       float((pos_on_floor % cols) * cell_w),
            "y":       float((pos_on_floor // cols) * cell_d),
            "width":   cell_w,
            "depth":   cell_d,
            "floor":   floor_idx,
            "features": [],
        })

    return {
        "unit_type": unit_type,
        "floor_plan": {
            "width_m": cols * cell_w,
            "depth_m": ((rooms_per_floor // cols) + 1) * cell_d,
            "rooms":   layout_rooms,
        },
        "circulation": {
            "staircase_x":    0.0,
            "staircase_y":    0.0,
            "main_entrance_x": cell_w,
        },
        "highlights": [
            "Auto-generated layout (AI unavailable)",
            "Rooms distributed evenly across floors",
        ],
    }


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

    built_up_area_raw = design_dna.get("built_up_area", plot_area_sqm * 0.55)
    built_up_per_floor = float(built_up_area_raw) if built_up_area_raw is not None else plot_area_sqm * 0.55

    if   built_up_per_floor < 80:  unit_type = "2bhk"
    elif built_up_per_floor < 130: unit_type = "3bhk"
    else:                           unit_type = "4bhk"

    rooms = ROOM_PROGRAMS[unit_type]
    rooms_per_floor = max(1, len(rooms) // floors)

    prompt = f"""You are a senior residential architect practising in India.
Generate an optimised floor plan layout as JSON.

Plot:  {plot_area_sqm:.0f} sqm total, {built_up_per_floor:.0f} sqm built-up per floor
Floors: {floors} (Indices from 0 to {floors - 1})
Unit type: {unit_type.upper()}
Building form: {design_dna.get('building_form', 'rectangular')}
Solar orientation: {design_dna.get('solar_orientation', 180):.0f}°
Open-plan ratio: {design_dna.get('open_plan_ratio', 0.5):.1f}
Has courtyard: {design_dna.get('courtyard_presence', False)}
Rooms to include: {rooms}

IMPORTANT: You MUST evenly distribute the {len(rooms)} rooms across all {floors} floors.
Each floor MUST contain approximately {rooms_per_floor} rooms.
Set the "floor" field (0-based integer) on every room object.

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

    layout_data: dict[str, Any] = {}
    try:
        base = BaseAgent("layout", user_id)
        raw = await base._call_llm(prompt)
        raw = raw.strip()
        raw = re.sub(r"^```(?:json)?", "", raw).rstrip("`").strip()
        parsed: Any = json.loads(raw)
        if isinstance(parsed, dict):
            layout_data = dict(parsed)   # explicit dict cast keeps type narrow
        else:
            raise ValueError("LLM returned non-dict JSON")
    except Exception:
        layout_data = _fallback_layout(unit_type, rooms, built_up_per_floor, floors)

    # Render SVG for each floor
    floor_plan_obj: dict[str, Any] = dict(layout_data.get("floor_plan") or {})
    svgs: dict[str, str] = {}
    for f in range(floors):
        svgs[f"floor_{f}"] = generate_floor_plan_svg(floor_plan_obj, floor_number=f)

    result: dict[str, Any] = dict(layout_data)   # new dict — avoids mutating a possibly-unknown type
    result["floor_plan_svgs"] = svgs
    result["floor_plan_svg"]  = svgs.get("floor_0", "")
    return result


# ─────────────────────────────────────────────────────────────────────────────
# Agent entry-point
# ─────────────────────────────────────────────────────────────────────────────

async def run(project_id: str, context: dict[str, Any]) -> dict[str, Any]:
    result = await generate_layout(
        plot_area_sqm = float(context.get("plot_area_sqm") or 1000.0),
        floors        = int(  context.get("floors")        or 2),
        budget_inr    = int(  context.get("budget_inr")    or 5_000_000),
        design_dna    = dict( context.get("best_dna")      or {}),
        geo_data      = dict( context.get("geo_data")      or {}),
        user_id       = context.get("user_id"),
    )
    return {"layout": result, **result}
