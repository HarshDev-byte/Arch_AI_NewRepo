"""
threed_agent.py — 3D model generation agent.

Generates a Babylon.js-compatible JSON scene graph from the Design DNA
and floor plan layout. Optionally invokes Blender CLI (if available) to
produce a real .glb file; otherwise returns a parametric JSON scene.
"""

from __future__ import annotations

import json
import math
import os
import subprocess
import tempfile
from typing import Any


# ─────────────────────────────────────────────────────────────────────────────
# Babylon.js scene graph helpers
# ─────────────────────────────────────────────────────────────────────────────

def _hex_to_rgb(hex_color: str) -> dict[str, float]:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return {"r": round(r / 255, 3), "g": round(g / 255, 3), "b": round(b / 255, 3)}


PALETTE_COLORS: dict[str, dict[str, str]] = {
    "warm_earthy":       {"wall": "#C4956A", "roof": "#8B4513", "trim": "#D4A574"},
    "cool_modern":       {"wall": "#E8EEF2", "roof": "#2C3E50", "trim": "#7F8C8D"},
    "natural_organic":   {"wall": "#D4C5A9", "roof": "#5D4037", "trim": "#8D6E63"},
    "luxury_premium":    {"wall": "#F5F5F0", "roof": "#1A1A2E", "trim": "#B8860B"},
    "sustainable_green": {"wall": "#E8F5E9", "roof": "#2E7D32", "trim": "#66BB6A"},
}


def _build_scene(dna: dict[str, Any], layout: dict[str, Any]) -> dict[str, Any]:
    """Assemble a Babylon.js-compatible JSON scene graph."""
    palette_key = dna.get("facade_material_palette", "cool_modern")
    palette = PALETTE_COLORS.get(palette_key, PALETTE_COLORS["cool_modern"])

    fp = layout.get("floor_plan", {})
    width  = float(fp.get("width_m",   10.0))
    depth  = float(fp.get("depth_m",   12.0))
    floors = int(  dna.get("floors",    2))
    fh     = float(dna.get("floor_height", 3.0))
    total_h = floors * fh

    wwr    = float(dna.get("window_wall_ratio", 0.4))

    meshes: list[dict] = []

    # ── Foundation slab ──────────────────────────────────────────────────────
    meshes.append({
        "id":       "foundation",
        "type":     "box",
        "position": [0, -0.15, 0],
        "scaling":  [width + 0.3, 0.3, depth + 0.3],
        "material": {"diffuseColor": _hex_to_rgb("#5D4037"), "roughness": 0.9},
    })

    # ── Floor slabs ────────────────────────────────────────────────────────
    for f in range(floors):
        y = f * fh + fh
        meshes.append({
            "id":       f"slab_floor_{f}",
            "type":     "box",
            "position": [0, y, 0],
            "scaling":  [width, 0.2, depth],
            "material": {"diffuseColor": _hex_to_rgb("#ECEFF1")},
        })

    # ── Exterior walls (4 faces) ─────────────────────────────────────────────
    wall_thick = 0.23
    wall_color = _hex_to_rgb(palette["wall"])
    wall_mat   = {"diffuseColor": wall_color, "roughness": 0.7}
    wall_h     = total_h

    for face_id, pos, scale in [
        ("wall_front",  [0,         wall_h / 2, -depth / 2],  [width, wall_h, wall_thick]),
        ("wall_back",   [0,         wall_h / 2,  depth / 2],  [width, wall_h, wall_thick]),
        ("wall_left",   [-width/2,  wall_h / 2,  0],          [wall_thick, wall_h, depth]),
        ("wall_right",  [ width/2,  wall_h / 2,  0],          [wall_thick, wall_h, depth]),
    ]:
        meshes.append({"id": face_id, "type": "box", "position": pos, "scaling": scale, "material": wall_mat})

    # ── Windows (WWR driven) ─────────────────────────────────────────────────
    win_w   = width * wwr * 0.25
    win_h   = fh * 0.55
    glass_mat = {"diffuseColor": {"r": 0.7, "g": 0.85, "b": 0.95}, "alpha": 0.35, "specular": 0.8}
    for f in range(floors):
        for i, x in enumerate([-width * 0.25, width * 0.25]):
            meshes.append({
                "id":       f"window_front_f{f}_{i}",
                "type":     "box",
                "position": [x, f * fh + fh * 0.6, -depth / 2 - 0.01],
                "scaling":  [win_w, win_h, 0.05],
                "material": glass_mat,
            })

    # ── Roof ────────────────────────────────────────────────────────────────
    roof_form  = dna.get("roof_form", "flat_terrace")
    roof_color = _hex_to_rgb(palette["roof"])
    if roof_form == "flat_terrace":
        meshes.append({
            "id": "roof", "type": "box",
            "position": [0, total_h + 0.15, 0],
            "scaling":  [width + 0.2, 0.3, depth + 0.2],
            "material": {"diffuseColor": roof_color, "roughness": 0.8},
        })
    elif "butterfly" in roof_form:
        # V-shaped butterfly: two angled planes
        for side, xoff, angle in [("left", -width * 0.25, 15), ("right", width * 0.25, -15)]:
            meshes.append({
                "id": f"roof_{side}", "type": "box",
                "position": [xoff, total_h + 0.5, 0],
                "scaling":   [width * 0.52, 0.15, depth + 0.2],
                "rotation":  [0, 0, math.radians(angle)],
                "material":  {"diffuseColor": roof_color},
            })
    else:
        # mono-pitch / shed
        meshes.append({
            "id": "roof", "type": "box",
            "position": [0, total_h + 0.4, 0],
            "scaling":  [width + 0.2, 0.15, depth + 0.2],
            "rotation": [math.radians(10), 0, 0],
            "material": {"diffuseColor": roof_color},
        })

    # ── Courtyard void (if present) ──────────────────────────────────────────
    if dna.get("courtyard_presence"):
        cw, cd = width * 0.3, depth * 0.3
        meshes.append({
            "id": "courtyard_floor", "type": "box",
            "position": [0, 0.05, 0],
            "scaling":  [cw, 0.1, cd],
            "material": {"diffuseColor": _hex_to_rgb("#A5D6A7")},
        })

    # ── Camera + lighting ────────────────────────────────────────────────────
    camera = {
        "type":     "ArcRotateCamera",
        "alpha":    -math.pi / 4,
        "beta":     math.pi / 3.5,
        "radius":   max(width, depth) * 2.2,
        "target":   [0, total_h / 2, 0],
    }
    lights = [
        {"type": "HemisphericLight", "direction": [0, 1, 0], "intensity": 0.8},
        {"type": "DirectionalLight",  "direction": [-1, -2, -1], "intensity": 0.6,
         "position": [width * 3, total_h * 3, depth * 2]},
    ]

    return {
        "engine": "BabylonJS",
        "version": "6.x",
        "camera":  camera,
        "lights":  lights,
        "meshes":  meshes,
        "metadata": {
            "style":        dna.get("primary_style"),
            "floors":       floors,
            "floor_height": fh,
            "width_m":      width,
            "depth_m":      depth,
            "palette":      palette_key,
        },
    }


# ─────────────────────────────────────────────────────────────────────────────
# Optional Blender export
# ─────────────────────────────────────────────────────────────────────────────

async def _try_blender_export(scene: dict[str, Any], project_id: str) -> str | None:
    """Try to generate a .glb via Blender CLI. Returns file path or None."""
    blender_path = os.environ.get("BLENDER_PATH", "/usr/bin/blender")
    if not os.path.exists(blender_path):
        return None

    try:
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            json.dump(scene, f)
            scene_file = f.name

        out_glb = f"/tmp/archai_{project_id}.glb"
        script = f"""
import bpy, json, mathutils
scene_data = json.load(open('{scene_file}'))
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()
for mesh in scene_data['meshes']:
    bpy.ops.mesh.primitive_cube_add(size=1)
    obj = bpy.context.active_object
    obj.name = mesh['id']
    obj.location = mesh['position']
    obj.scale = mesh['scaling']
bpy.ops.export_scene.gltf(filepath='{out_glb}', export_format='GLB')
"""
        proc = subprocess.run(
            [blender_path, "--background", "--python-expr", script],
            timeout=60, capture_output=True,
        )
        if proc.returncode == 0 and os.path.exists(out_glb):
            return out_glb
    except Exception:
        pass
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Agent entry-point
# ─────────────────────────────────────────────────────────────────────────────

async def run(project_id: str, context: dict[str, Any]) -> dict[str, Any]:
    dna    = dict(context.get("best_dna", {}))
    layout = dict(context.get("layout",   {}))

    scene = _build_scene(dna, layout)

    model_url = await _try_blender_export(scene, project_id)

    return {
        "threed": {
            "scene_graph": scene,
            "model_url":   model_url,
            "format":      "glb" if model_url else "babylon_json",
            "mesh_count":  len(scene["meshes"]),
        },
        "model_url":  model_url,
        "scene_graph": scene,
    }
