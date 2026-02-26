import bpy
import bmesh
import numpy as np
from .utils import Mio3ShrinkToolsBase


class MESH_OT_mio3srt_shape_reset(bpy.types.Operator, Mio3ShrinkToolsBase):
    bl_idname = "mesh.mio3srt_shape_reset"
    bl_label = "Shape Reset"
    bl_description = "Reset the shape keys to their default state"
    bl_options = {"UNDO"}

    @classmethod
    def poll(cls, context):
        return context.active_object is not None and context.active_object.mode == "EDIT"

    def execute(self, context):
        obj = context.active_object
        active_kb = obj.active_shape_key
        if obj.mode == "EDIT":
            basis_kb = obj.data.shape_keys.reference_key
            try:
                bpy.ops.mesh.blend_from_shape(shape=basis_kb.name, blend=1, add=False)
            except Exception as e:
                self.report({"ERROR"}, str(e))
        elif not active_kb.lock_shape:
            basis_co_flat = np.empty(len(obj.data.vertices) * 3, dtype=np.float32)
            obj.data.vertices.foreach_get("co", basis_co_flat)
            active_kb.data.foreach_set("co", basis_co_flat)
            obj.data.update()
        else:
            self.report({"ERROR"}, "Active Shape Key is Locked")
        return {"FINISHED"}


class MESH_OT_mio3srt_deselect_used(bpy.types.Operator, Mio3ShrinkToolsBase):
    bl_idname = "mesh.mio3srt_deselect_used"
    bl_label = "Deselect Shape Key Moved"
    bl_description = "Deselect vertices that have been moved in the active shape key"
    bl_options = {"UNDO"}

    @classmethod
    def poll(cls, context):
        return context.active_object is not None and context.active_object.mode == "EDIT"

    def execute(self, context):
        obj = context.active_object
        if obj is None or obj.type != "MESH":
            return {"CANCELLED"}

        sk = obj.data.shape_keys
        if sk is None:
            self.report({"ERROR"}, "No shape keys")
            return {"CANCELLED"}

        active_kb = obj.active_shape_key
        basis_kb = sk.reference_key
        if active_kb is None or basis_kb is None or active_kb == basis_kb:
            self.report({"ERROR"}, "No active shape key")
            return {"CANCELLED"}

        bm = bmesh.from_edit_mesh(obj.data)
        bm.verts.ensure_lookup_table()

        eps_sq = 1e-12
        for v in bm.verts:
            if not v.select:
                continue

            i = v.index
            if (active_kb.data[i].co - basis_kb.data[i].co).length_squared > eps_sq:
                v.select = False

        bm.select_flush_mode()
        bmesh.update_edit_mesh(obj.data)
        return {"FINISHED"}


classes = [
    MESH_OT_mio3srt_shape_reset,
    MESH_OT_mio3srt_deselect_used,
]


def register():
    for c in classes:
        bpy.utils.register_class(c)


def unregister():
    for c in classes:
        bpy.utils.unregister_class(c)
