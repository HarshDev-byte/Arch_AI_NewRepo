"""Blender template: residential building."""
import bpy

def build_residential(floors: int = 3, width: float = 10.0, depth: float = 15.0):
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()
    bpy.ops.mesh.primitive_cube_add(size=1)
    obj = bpy.context.object
    obj.dimensions = (width, depth, floors * 3.0)
    return obj
