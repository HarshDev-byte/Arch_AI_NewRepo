"""
vr_agent.py — VR/AR experience preparation agent.

Transforms the 3D scene graph into an A-Frame WebXR scene
and generates a QR-code link for mobile AR preview.
"""

from __future__ import annotations

import base64
import io
import json
import math
from typing import Any


# ─────────────────────────────────────────────────────────────────────────────
# A-Frame HTML generator
# ─────────────────────────────────────────────────────────────────────────────

def _mesh_to_aframe(mesh: dict[str, Any]) -> str:
    """Convert a Babylon.js mesh dict to an A-Frame <a-box> entity."""
    pos   = mesh.get("position", [0, 0, 0])
    scale = mesh.get("scaling",  [1, 1, 1])
    rot   = mesh.get("rotation", [0, 0, 0])   # radians → degrees
    mat   = mesh.get("material", {})
    dc    = mat.get("diffuseColor", {"r": 0.8, "g": 0.8, "b": 0.8})
    alpha = mat.get("alpha", 1.0)
    color = "#{:02x}{:02x}{:02x}".format(
        int(dc.get("r", 0.8) * 255),
        int(dc.get("g", 0.8) * 255),
        int(dc.get("b", 0.8) * 255),
    )
    rot_deg = [round(math.degrees(r), 1) for r in rot] if rot else [0, 0, 0]

    attrs = (
        f'id="{mesh["id"]}" '
        f'position="{pos[0]} {pos[1]} {pos[2]}" '
        f'scale="{scale[0]} {scale[1]} {scale[2]}" '
        f'rotation="{rot_deg[0]} {rot_deg[1]} {rot_deg[2]}" '
        f'color="{color}" '
        f'opacity="{alpha}"'
    )
    return f"    <a-box {attrs}></a-box>"


def generate_aframe_scene(
    scene: dict[str, Any],
    project_id: str,
    title: str = "ArchAI Design Preview",
) -> str:
    """Return a complete A-Frame HTML page."""
    # Camera position from scene metadata
    meta  = scene.get("metadata", {})
    w     = float(meta.get("width_m",  10))
    d     = float(meta.get("depth_m",  12))
    h     = float(meta.get("floors",    2)) * float(meta.get("floor_height", 3))
    radius = max(w, d) * 2.2
    cam_y  = h * 0.6
    cam_z  = -radius

    entities = [_mesh_to_aframe(m) for m in scene.get("meshes", [])]
    entities_html = "\n".join(entities)

    style = meta.get("style", "contemporary").replace("_", " ").title()
    palette = meta.get("palette", "cool_modern").replace("_", " ").title()

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>{title}</title>
  <meta name="description" content="ArchAI {style} VR Design Preview">
  <script src="https://aframe.io/releases/1.5.0/aframe.min.js"></script>
  <style>
    #info {{
      position: fixed; top: 12px; left: 12px; z-index: 999;
      background: rgba(0,0,0,.55); color: #fff;
      padding: 8px 14px; border-radius: 8px; font-family: sans-serif; font-size: 13px;
    }}
  </style>
</head>
<body>
  <div id="info">
    <strong>ArchAI VR Preview</strong><br>
    Style: {style} · Palette: {palette}<br>
    <small>Project: {project_id[:8]}…</small>
  </div>
  <a-scene background="color: #87CEEB" fog="type: exponential; color: #87CEEB; density: 0.02">
    <a-assets></a-assets>

    <!-- Sky & environment -->
    <a-sky color="#87CEEB"></a-sky>
    <a-plane position="0 0 0" rotation="-90 0 0"
             width="{int(max(w, d) * 20)}" height="{int(max(w, d) * 20)}"
             color="#8BC34A" roughness="1"></a-plane>

    <!-- Building meshes -->
{entities_html}

    <!-- Camera rig -->
    <a-entity id="rig" position="0 {cam_y:.1f} {cam_z:.1f}">
      <a-camera look-controls wasd-controls>
        <a-cursor color="white" opacity="0.8"></a-cursor>
      </a-camera>
    </a-entity>

    <!-- Lighting -->
    <a-light type="ambient"      color="#FFFFFF" intensity="0.7"></a-light>
    <a-light type="directional"  color="#FFF9E6" intensity="0.8"
             position="-1 3 -1"></a-light>
  </a-scene>
</body>
</html>"""


# ─────────────────────────────────────────────────────────────────────────────
# QR-code generator (pure Python, no PIL needed)
# ─────────────────────────────────────────────────────────────────────────────

def _generate_qr_svg(url: str) -> str:
    """Minimal QR-code placeholder SVG (real QR replaced by segno if installed)."""
    try:
        import segno  # type: ignore
        qr = segno.make_qr(url, error="M")
        buf = io.StringIO()
        qr.save(buf, kind="svg", scale=4, border=1)
        return buf.getvalue()
    except ImportError:
        pass

    # Fallback: simple placeholder SVG
    safe_url = url.replace("&", "&amp;").replace("<", "&lt;")
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200">'
        '<rect width="200" height="200" fill="white" stroke="#ccc"/>'
        '<rect x="10" y="10" width="180" height="180" fill="none" stroke="black" stroke-width="3"/>'
        '<text x="100" y="90" text-anchor="middle" font-size="11" font-family="sans-serif">Scan to view</text>'
        f'<text x="100" y="115" text-anchor="middle" font-size="7" fill="#555">{safe_url[:40]}…</text>'
        '</svg>'
    )


# ─────────────────────────────────────────────────────────────────────────────
# Agent entry-point
# ─────────────────────────────────────────────────────────────────────────────

async def run(project_id: str, context: dict[str, Any]) -> dict[str, Any]:
    scene    = dict(context.get("scene_graph", {}))
    meta     = scene.get("metadata", {})
    style    = str(meta.get("style", "contemporary")).replace("_", " ").title()

    from config import settings
    base_url  = settings.next_public_api_url or "http://localhost:3000"
    vr_url    = f"{base_url}/project/{project_id}/viewer"

    aframe_html = generate_aframe_scene(scene, project_id, title=f"ArchAI — {style}")
    qr_svg      = _generate_qr_svg(vr_url)

    return {
        "vr": {
            "enabled":      True,
            "aframe_html":  aframe_html,
            "vr_url":       vr_url,
            "qr_svg":       qr_svg,
            "webxr_ready":  True,
            "mesh_count":   len(scene.get("meshes", [])),
        },
        "vr_url":    vr_url,
        "aframe_html": aframe_html,
    }
