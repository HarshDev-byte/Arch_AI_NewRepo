"""
blender/generator.py — 3D model generation via Blender headless.

Pipeline:
  1. Design DNA → format Blender Python script from template
  2. Run `blender --background --python <script>` (async subprocess)
  3. Export → .glb via bpy.ops.export_scene.gltf
  4. (Optional) Upload to Supabase Storage → return public URL

Works without Blender installed:
  - Returns None for model_path / model_url
  - The Babylon.js scene graph from threed_agent is used as fallback
"""

from __future__ import annotations

import asyncio
import json
import os
import tempfile
from typing import Any

from config import settings


# ─────────────────────────────────────────────────────────────────────────────
# Blender Python script template
# ─────────────────────────────────────────────────────────────────────────────

BLENDER_SCRIPT_TEMPLATE = r'''
import bpy
import bmesh
import math
import json
import random

# ── Clear default scene ───────────────────────────────────────────────────────
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
for block in bpy.data.meshes:
    bpy.data.meshes.remove(block)

# ── Design DNA ────────────────────────────────────────────────────────────────
dna = {dna_json}

PALETTE_COLORS = {{
    'warm_earthy':       (0.80, 0.65, 0.50, 1.0),
    'cool_modern':       (0.85, 0.87, 0.90, 1.0),
    'natural_organic':   (0.60, 0.55, 0.45, 1.0),
    'luxury_premium':    (0.95, 0.90, 0.85, 1.0),
    'sustainable_green': (0.50, 0.65, 0.45, 1.0),
}}

# ── Derived dimensions ────────────────────────────────────────────────────────
bua          = dna.get('built_up_area', 100.0)
width        = (bua ** 0.5) * 1.20
depth        = (bua ** 0.5) * 0.85
floor_height = dna.get('floor_height', 3.0)
floors       = {floors}
wwr          = dna.get('window_wall_ratio', 0.40)
facade_pal   = dna.get('facade_material_palette', 'cool_modern')
facade_pat   = dna.get('facade_pattern', 'horizontal_louvers')
roof_form    = dna.get('roof_form', 'flat_terrace')
base_color   = PALETTE_COLORS.get(facade_pal, (0.80, 0.80, 0.80, 1.0))


def new_mat(name, base, roughness=0.7, metallic=0.0, alpha=1.0):
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes['Principled BSDF']
    bsdf.inputs['Base Color'].default_value = (*base[:3], 1.0)
    bsdf.inputs['Roughness'].default_value  = roughness
    bsdf.inputs['Metallic'].default_value   = metallic
    if alpha < 1.0:
        bsdf.inputs['Alpha'].default_value  = alpha
        mat.blend_method = 'BLEND'
    return mat


# ═══════════════════════════════════════════════════════════════════════════════
# FLOOR PLATES
# ═══════════════════════════════════════════════════════════════════════════════
for floor in range(floors):
    bpy.ops.mesh.primitive_cube_add(
        size=1,
        location=(0, 0, floor * floor_height + floor_height / 2)
    )
    obj       = bpy.context.active_object
    obj.name  = f'Floor_{{floor}}'
    obj.scale = (width, depth, floor_height * 0.95)
    bpy.ops.object.transform_apply(scale=True)
    obj.data.materials.append(
        new_mat(f'FloorMat_{{floor}}', base_color)
    )


# ═══════════════════════════════════════════════════════════════════════════════
# ROOF
# ═══════════════════════════════════════════════════════════════════════════════
roof_z = floors * floor_height

if roof_form == 'flat_terrace':
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, roof_z + 0.15))
    roof       = bpy.context.active_object
    roof.name  = 'Roof'
    roof.scale = (width + 0.3, depth + 0.3, 0.3)
    bpy.ops.object.transform_apply(scale=True)
    roof.data.materials.append(
        new_mat('RoofMat', (0.25, 0.25, 0.28, 1.0), roughness=0.85)
    )

elif roof_form == 'shed_mono_pitch':
    mesh = bpy.data.meshes.new('RoofMesh')
    obj  = bpy.data.objects.new('Roof', mesh)
    bpy.context.collection.objects.link(obj)
    bm   = bmesh.new()
    w, d = width / 2 + 0.5, depth / 2 + 0.5
    pitch = dna.get('mutation_factor', 0.15) * 3 + 1.5
    for v in [(-w,-d,roof_z),(w,-d,roof_z),(w,d,roof_z+pitch),(-w,d,roof_z+pitch)]:
        bm.verts.new(v)
    bm.verts.ensure_lookup_table()
    bm.faces.new(bm.verts)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh); bm.free()

elif roof_form == 'butterfly_inverted':
    mesh = bpy.data.meshes.new('ButterflyRoof')
    obj  = bpy.data.objects.new('Roof', mesh)
    bpy.context.collection.objects.link(obj)
    bm   = bmesh.new()
    w, d = width / 2 + 0.5, depth / 2 + 0.5
    dip  = 0.8
    raw  = [(-w,-d,roof_z+1.5),(w,-d,roof_z+1.5),(0,0,roof_z+dip),
            (-w,d,roof_z+1.5),(w,d,roof_z+1.5)]
    vs = [bm.verts.new(v) for v in raw]
    bm.faces.new([vs[0],vs[1],vs[2]])
    bm.faces.new([vs[2],vs[1],vs[4],vs[3]])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh); bm.free()

elif roof_form in ('green_roof', 'parasol_floating'):
    # Green roof slab + parapet
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, roof_z + 0.15))
    roof       = bpy.context.active_object
    roof.name  = 'GreenRoof'
    roof.scale = (width + 0.3, depth + 0.3, 0.3)
    bpy.ops.object.transform_apply(scale=True)
    roof.data.materials.append(
        new_mat('GreenRoofMat', (0.25, 0.55, 0.25, 1.0), roughness=1.0)
    )
else:
    # Fallback: flat
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, roof_z + 0.15))
    roof       = bpy.context.active_object
    roof.name  = 'Roof'
    roof.scale = (width + 0.3, depth + 0.3, 0.3)
    bpy.ops.object.transform_apply(scale=True)
    roof.data.materials.append(
        new_mat('RoofMat', (0.3, 0.3, 0.32, 1.0))
    )


# ═══════════════════════════════════════════════════════════════════════════════
# FACADE ELEMENTS (windows / fins / louvers)
# ═══════════════════════════════════════════════════════════════════════════════
glass_mat = new_mat('GlassMat', (0.70, 0.85, 1.0), roughness=0.0, alpha=0.15)

for floor in range(floors):
    floor_z = floor * floor_height

    if facade_pat == 'vertical_fins':
        fin_count = max(3, int(width / 1.5))
        fin_mat   = new_mat('FinMat', (0.9, 0.9, 0.95), metallic=0.8, roughness=0.15)
        for i in range(fin_count):
            x = -width / 2 + (i + 0.5) * (width / fin_count)
            bpy.ops.mesh.primitive_cube_add(
                size=1,
                location=(x, depth / 2 + 0.06, floor_z + floor_height / 2)
            )
            fin      = bpy.context.active_object
            fin.name = f'Fin_{{floor}}_{{i}}'
            fin.scale = (0.08, 0.12, floor_height * 0.90)
            bpy.ops.object.transform_apply(scale=True)
            fin.data.materials.append(fin_mat)

    elif facade_pat in ('horizontal_louvers', 'glass_box'):
        win_h = floor_height * wwr * 0.8
        win_w = width * 0.75
        win_z = floor_z + floor_height * 0.3 + win_h / 2
        bpy.ops.mesh.primitive_cube_add(size=1, location=(0, depth / 2 + 0.01, win_z))
        win      = bpy.context.active_object
        win.name = f'Window_{{floor}}'
        win.scale = (win_w, 0.02, win_h)
        bpy.ops.object.transform_apply(scale=True)
        win.data.materials.append(glass_mat)

    elif facade_pat in ('jaali_screen', 'perforated_metal'):
        # Array of small openings as proxy for jaali
        rows, cols = 4, int(width / 0.6)
        for r in range(rows):
            for c in range(cols):
                x = -width / 2 + 0.3 + c * (width / cols)
                z = floor_z + 0.4 + r * (floor_height / (rows + 1))
                bpy.ops.mesh.primitive_cube_add(size=1, location=(x, depth/2+0.02, z))
                hole      = bpy.context.active_object
                hole.name = f'Jaali_{{floor}}_{{r}}_{{c}}'
                hole.scale = (0.25, 0.04, 0.25)
                bpy.ops.object.transform_apply(scale=True)
                hole.data.materials.append(glass_mat)

    else:
        # Default: horizontal strip window
        win_h = floor_height * wwr
        bpy.ops.mesh.primitive_cube_add(
            size=1, location=(0, depth/2+0.01, floor_z + floor_height*0.55)
        )
        win      = bpy.context.active_object
        win.name = f'Window_{{floor}}'
        win.scale = (width * 0.6, 0.02, win_h)
        bpy.ops.object.transform_apply(scale=True)
        win.data.materials.append(glass_mat)


# ═══════════════════════════════════════════════════════════════════════════════
# COURTYARD (if DNA flag set)
# ═══════════════════════════════════════════════════════════════════════════════
if dna.get('courtyard_presence', False):
    cy_w, cy_d = width * 0.30, depth * 0.30
    bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 0, 0.02))
    cy      = bpy.context.active_object
    cy.name = 'Courtyard'
    cy.scale = (cy_w, cy_d, 1)
    bpy.ops.object.transform_apply(scale=True)
    cy.data.materials.append(
        new_mat('CourtyardMat', (0.40, 0.65, 0.35, 1.0), roughness=1.0)
    )


# ═══════════════════════════════════════════════════════════════════════════════
# GROUND PLANE
# ═══════════════════════════════════════════════════════════════════════════════
bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 0, -0.05))
ground       = bpy.context.active_object
ground.name  = 'Ground'
ground.scale = (width * 3.5, depth * 3.5, 1)
bpy.ops.object.transform_apply(scale=True)
ground.data.materials.append(
    new_mat('GroundMat', (0.20, 0.35, 0.15, 1.0), roughness=0.95)
)


# ═══════════════════════════════════════════════════════════════════════════════
# TREES (randomised, seeded from DNA)
# ═══════════════════════════════════════════════════════════════════════════════
rng = random.Random(hash(str(dna.get('seed', 42))) & 0xFFFFFFFF)
tree_mat = new_mat('TreeMat', (0.10, 0.45, 0.10, 1.0), roughness=1.0)
trunk_mat = new_mat('TrunkMat', (0.35, 0.22, 0.10, 1.0), roughness=0.9)
for i in range(6):
    side  = rng.choice([-1, 1])
    tx    = side * rng.uniform(width * 0.75, width * 1.60)
    ty    = rng.uniform(-depth * 1.20, depth * 1.20)
    scale = rng.uniform(0.80, 1.30)
    # Trunk
    bpy.ops.mesh.primitive_cylinder_add(radius=0.12*scale, depth=2.0*scale, location=(tx, ty, scale))
    trunk = bpy.context.active_object
    trunk.name = f'Trunk_{{i}}'
    trunk.data.materials.append(trunk_mat)
    # Canopy
    bpy.ops.mesh.primitive_ico_sphere_add(radius=1.1*scale, location=(tx, ty, 2.8*scale))
    canopy = bpy.context.active_object
    canopy.name = f'Tree_{{i}}'
    canopy.data.materials.append(tree_mat)


# ═══════════════════════════════════════════════════════════════════════════════
# LIGHTING
# ═══════════════════════════════════════════════════════════════════════════════
bpy.ops.object.light_add(type='SUN', location=(width*1.5, depth, floors*floor_height*2))
sun          = bpy.context.active_object
sun.name     = 'Sun'
sun.data.energy = 3.5
sun.data.angle  = math.radians(12)

bpy.ops.object.light_add(type='AREA', location=(-width, -depth, floors*floor_height*1.5))
fill         = bpy.context.active_object
fill.name    = 'FillLight'
fill.data.energy = 60
fill.data.size   = 10


# ═══════════════════════════════════════════════════════════════════════════════
# CAMERA
# ═══════════════════════════════════════════════════════════════════════════════
cam_x = width * 2.20
cam_y = -depth * 2.80
cam_z = floors * floor_height + 6.0
bpy.ops.object.camera_add(location=(cam_x, cam_y, cam_z))
cam          = bpy.context.active_object
cam.name     = 'ArchAICamera'
cam.rotation_euler = (math.radians(62), 0, math.radians(35))
cam.data.lens = 35
bpy.context.scene.camera = cam


# ═══════════════════════════════════════════════════════════════════════════════
# RENDER SETTINGS (cycles, for thumbnail)
# ═══════════════════════════════════════════════════════════════════════════════
scene = bpy.context.scene
scene.render.engine  = 'CYCLES'
scene.cycles.samples = 64
scene.render.resolution_x = 1280
scene.render.resolution_y = 720


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORT → GLB
# ═══════════════════════════════════════════════════════════════════════════════
# If user edited the layout, add flat marker planes for each room (metadata only)
user_rooms = dna.get('user_rooms', [])
if user_rooms:
    for room in user_rooms:
        if room.get('floor', 0) == 0:
            # Add a flat marker plane for each room at ground level
            bpy.ops.mesh.primitive_plane_add(
                size=1,
                location=(
                    room['x'] + room['w']/2 - width/2,
                    -(room['y'] + room['h']/2 - depth/2),
                    0.05
                )
            )
            marker = bpy.context.active_object
            marker.name = f"Room_{room['name'].replace(' ', '_')}"
            marker.scale = (room['w'], room['h'], 1)
            bpy.ops.object.transform_apply(scale=True)
            # Invisible render, just for structure metadata
            marker.hide_render = True

bpy.ops.export_scene.gltf(
    filepath="{output_path}",
    export_format='GLB',
    export_materials='EXPORT',
    export_cameras=True,
    export_lights=True,
    export_apply=True,
    export_texcoords=True,
    export_normals=True,
    export_colors=True,
)
print("ArchAI 3D: Export complete →", "{output_path}")
'''


# ─────────────────────────────────────────────────────────────────────────────
# Blender availability check
# ─────────────────────────────────────────────────────────────────────────────

def _blender_path() -> str | None:
    """Return Blender executable path if available, else None."""
    path = settings.blender_path or "blender"
    if os.path.isfile(path) and os.access(path, os.X_OK):
        return path
    # Try PATH lookup
    import shutil
    return shutil.which("blender")


# ─────────────────────────────────────────────────────────────────────────────
# Core model generator
# ─────────────────────────────────────────────────────────────────────────────

async def generate_3d_model(
    design_dna: dict[str, Any],
    floors: int,
    output_dir: str,
    timeout_seconds: int = 120,
) -> str:
    """
    Generate a .glb model from Design DNA using Blender headlessly.

    Returns the absolute path to the generated .glb file.
    Raises RuntimeError if Blender is unavailable or fails.
    """
    blender = _blender_path()
    if blender is None:
        raise RuntimeError(
            "Blender not found. Set BLENDER_PATH in .env or install Blender and add it to PATH."
        )

    dna_id = design_dna.get("dna_id", "unknown")
    output_path = os.path.join(output_dir, f"model_{dna_id}.glb")

    # Render the script from the template
    script_content = BLENDER_SCRIPT_TEMPLATE.format(
        dna_json=json.dumps(design_dna, default=str),
        floors=int(floors),
        output_path=output_path.replace("\\", "/"),
    )

    # Write script to a temp file
    with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False, encoding="utf-8") as f:
        f.write(script_content)
        script_path = f.name

    try:
        proc = await asyncio.create_subprocess_exec(
            blender,
            "--background",
            "--python", script_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout_seconds)
        except asyncio.TimeoutError:
            proc.kill()
            raise RuntimeError(f"Blender timed out after {timeout_seconds}s")

        if proc.returncode != 0:
            err = stderr.decode(errors="replace")
            raise RuntimeError(f"Blender exited {proc.returncode}: {err[-2000:]}")

        if not os.path.exists(output_path):
            raise RuntimeError(
                f"Blender succeeded but output file not found: {output_path}\n"
                f"stdout: {stdout.decode(errors='replace')[-1000:]}"
            )

        return output_path

    finally:
        try:
            os.unlink(script_path)
        except OSError:
            pass


# ─────────────────────────────────────────────────────────────────────────────
# Supabase upload (optional)
# ─────────────────────────────────────────────────────────────────────────────

async def upload_to_supabase(local_path: str, dna_id: str) -> str | None:
    """
    Upload the .glb to Supabase Storage bucket 'archai-models'.
    Returns the public URL or None if Supabase is not configured.
    """
    if not settings.supabase_service_key or not settings.supabase_url:
        return None
    try:
        from supabase import create_client  # type: ignore
        supa = create_client(settings.supabase_url, settings.supabase_service_key)
        object_name = f"models/{dna_id}.glb"
        with open(local_path, "rb") as f:
            data = f.read()
        supa.storage.from_("archai-models").upload(
            path=object_name,
            file=data,
            file_options={"content-type": "model/gltf-binary", "upsert": "true"},
        )
        public_url = (
            f"{settings.supabase_url}/storage/v1/object/public/archai-models/{object_name}"
        )
        return public_url
    except Exception:
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Generate + upload all variants
# ─────────────────────────────────────────────────────────────────────────────

async def generate_all_variants(
    variants: list[dict[str, Any]],
    floors: int,
) -> list[dict[str, Any]]:
    """
    Generate 3D .glb models for all design variants concurrently.

    Each variant dict is mutated in-place with:
      - ``model_path``   — local .glb path (or None on failure)
      - ``model_url``    — Supabase public URL (or None)
      - ``model_error``  — error string (or None on success)
    """
    output_dir = tempfile.mkdtemp(prefix="archai_3d_")

    async def _generate_one(variant: dict[str, Any]) -> None:
        dna  = variant.get("dna") or {}
        dnaid = dna.get("dna_id", "unknown")
        try:
            path = await generate_3d_model(dna, floors, output_dir)
            url  = await upload_to_supabase(path, dnaid)
            variant["model_path"]  = path
            variant["model_url"]   = url
            variant["model_error"] = None
        except Exception as exc:
            variant["model_path"]  = None
            variant["model_url"]   = None
            variant["model_error"] = str(exc)

    await asyncio.gather(*[_generate_one(v) for v in variants], return_exceptions=True)
    return variants


# ─────────────────────────────────────────────────────────────────────────────
# Script validation helper (no Blender needed)
# ─────────────────────────────────────────────────────────────────────────────

def validate_script(design_dna: dict[str, Any], floors: int) -> str:
    """
    Render and return the Blender script without executing it.
    Useful for unit tests and debugging.
    """
    return BLENDER_SCRIPT_TEMPLATE.format(
        dna_json=json.dumps(design_dna, default=str),
        floors=int(floors),
        output_path="/tmp/test_output.glb",
    )
