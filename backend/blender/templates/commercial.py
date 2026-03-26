"""Blender template: commercial building."""
import bpy

def build_commercial(floors: int = 5, width: float = 20.0, depth: float = 30.0):
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()
    bpy.ops.mesh.primitive_cube_add(size=1)
    obj = bpy.context.object
    obj.dimensions = (width, depth, floors * 4.0)
    return obj
