"""Blender base scene setup – lighting, camera, world."""
import bpy

def setup_scene():
    bpy.context.scene.render.engine = "CYCLES"
    bpy.ops.object.light_add(type="SUN", location=(10, -10, 20))
    bpy.ops.object.camera_add(location=(20, -20, 15))
    bpy.context.scene.camera = bpy.context.object
