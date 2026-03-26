"""GLB / FBX / OBJ exporter."""
import bpy, os

def export_glb(output_path: str):
    bpy.ops.export_scene.gltf(filepath=output_path, export_format="GLB")

def export_fbx(output_path: str):
    bpy.ops.export_scene.fbx(filepath=output_path)

def export_obj(output_path: str):
    bpy.ops.wm.obj_export(filepath=output_path)
