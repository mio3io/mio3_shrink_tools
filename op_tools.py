import bpy
import bmesh
from mathutils import Vector, kdtree
from bpy.props import BoolProperty, FloatProperty, EnumProperty
from bpy.app.translations import pgettext
from .utils import (
    Mio3ShrinkToolsBase,
    find_edge_loops_by_edges,
    find_x_mirror_verts,
    find_bone_by_weight,
    find_islands,
    find_x_mirror_edges,
)


class MESH_OT_mio3_snap_to_bone(bpy.types.Operator, Mio3ShrinkToolsBase):
    bl_idname = "mesh.mio3_snap_to_bone"
    bl_label = "Snapping a vertex to a bone"
    bl_description = "Snap selected vertices to bones"
    bl_options = {"REGISTER", "UNDO"}

    align: BoolProperty(name="Align edge loops", default=True)
    volume_factor: FloatProperty(
        name="Volume",
        description="残すボリューム（0だと頂点が重なりミラー編集ができなくなることがあります）",
        default=0.05,  # 0.03
        min=0.0,
        max=1.0,
        step=5,
    )

    @classmethod
    def poll(cls, context):
        return context.active_object is not None and context.active_object.mode == "EDIT"

    def invoke(self, context, event):
        obj = context.active_object
        obj.update_from_editmode()
        if not obj.find_armature():
            self.report({"ERROR"}, "Armature modifier not set")
            return {"CANCELLED"}
        if not obj.active_shape_key:
            self.report({"ERROR"}, "Register ShapeKey for Shrink")
            return {"CANCELLED"}
        return self.execute(context)

    def execute(self, context):
        self.start_time()
        obj = context.active_object

        if not obj.active_shape_key:
            obj.shape_key_add(name="Shrink")

        bm = bmesh.from_edit_mesh(obj.data)
        bm.verts.ensure_lookup_table()

        selected_verts = {v for v in bm.verts if v.select}
        if obj.use_mesh_mirror_x:
            selected_verts.update(find_x_mirror_verts(bm, selected_verts))

        selected_edges = {e for e in bm.edges if e.select}
        islands = find_islands(selected_verts, selected_edges)

        factor = 1 - self.volume_factor
        armature = obj.find_armature()

        for verts in islands:
            bone = find_bone_by_weight(obj, armature, verts)
            if bone:
                head = armature.matrix_world @ bone.head_local
                tail = armature.matrix_world @ bone.tail_local
                vec = tail - head
                for vert in verts:
                    vert_world_co = obj.matrix_world @ vert.co

                    vert_to_bone = vert_world_co - head
                    proj_vec = vert_to_bone.project(vec)
                    snapped_pos = head + proj_vec

                    vert.co = obj.matrix_world.inverted() @ vert_world_co.lerp(snapped_pos, factor)

        bmesh.update_edit_mesh(obj.data)
        self.print_time()

        if self.align and obj.data.total_face_sel < 1:
            bpy.ops.mesh.mio3_align_to_bone()

        return {"FINISHED"}


class MESH_OT_mio3_snap_to_joint(bpy.types.Operator, Mio3ShrinkToolsBase):
    bl_idname = "mesh.mio3_snap_to_joint"
    bl_label = "Snapping a vertex to a joint"
    bl_description = "Snap selected vertices to joints"
    bl_options = {"REGISTER", "UNDO"}

    volume_factor: FloatProperty(
        name="Volume",
        description="残すボリューム（0だと頂点が重なりミラー編集ができなくなることがあります）",
        default=0.05,  # 0.03
        min=0.0,
        max=1.0,
        step=5,
    )

    @classmethod
    def poll(cls, context):
        return context.active_object is not None and context.active_object.mode == "EDIT"

    def invoke(self, context, event):
        obj = context.active_object
        obj.update_from_editmode()
        if not obj.find_armature():
            self.report({"ERROR"}, "Armature modifier not set")
            return {"CANCELLED"}
        if not obj.active_shape_key:
            self.report({"ERROR"}, "Register ShapeKey for Shrink")
            return {"CANCELLED"}
        return self.execute(context)

    def execute(self, context):
        self.start_time()
        obj = context.active_object

        bm = bmesh.from_edit_mesh(obj.data)
        bm.verts.ensure_lookup_table()

        selected_verts = {v for v in bm.verts if v.select}
        if not selected_verts:
            return {"CANCELLED"}

        if obj.use_mesh_mirror_x:
            selected_verts.update(find_x_mirror_verts(bm, selected_verts))

        selected_edges = {e for e in bm.edges if e.select}
        islands = find_islands(selected_verts, selected_edges)

        armature = obj.find_armature()
        factor = 1 - self.volume_factor

        for verts in islands:
            center_world = sum((obj.matrix_world @ v.co for v in verts), Vector()) / len(verts)

            bone = find_bone_by_weight(obj, armature, verts)
            if bone:
                head = armature.matrix_world @ bone.head_local
                tail = armature.matrix_world @ bone.tail_local
                target_world = head if (center_world - head).length_squared < (center_world - tail).length_squared else tail

                for vert in verts:
                    vert_world = obj.matrix_world @ vert.co
                    vert.co = obj.matrix_world.inverted() @ vert_world.lerp(target_world, factor)

        bmesh.update_edit_mesh(obj.data)
        self.print_time()
        return {"FINISHED"}


class MESH_OT_mio3_align_to_bone(bpy.types.Operator, Mio3ShrinkToolsBase):
    bl_idname = "mesh.mio3_align_to_bone"
    bl_label = "Align edge loops"
    bl_description = "Align the selected edge loop perpendicular to the bone"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return context.active_object is not None and context.active_object.mode == "EDIT"

    def invoke(self, context, event):
        obj = context.active_object
        obj.update_from_editmode()
        if obj.data.total_face_sel > 0:
            self.report({"ERROR"}, "Please select only edges")
            return {"CANCELLED"}
        if not obj.find_armature():
            self.report({"ERROR"}, "Armature modifier not set")
            return {"CANCELLED"}
        if not obj.active_shape_key:
            self.report({"ERROR"}, "Register ShapeKey for Shrink")
            return {"CANCELLED"}
        return self.execute(context)

    def execute(self, context):
        self.start_time()

        obj = context.active_object

        bm = bmesh.from_edit_mesh(obj.data)

        armature = obj.find_armature()

        selected_edges = {e for e in bm.edges if e.select}
        if obj.use_mesh_mirror_x:
            selected_edges.update(find_x_mirror_edges(bm, selected_edges))
        edge_loops = find_edge_loops_by_edges(selected_edges)

        for loop in edge_loops:
            verts = {v for el in loop for v in el.verts}

            bone = find_bone_by_weight(obj, armature, verts)

            bone_matrix = armature.matrix_world @ bone.matrix_local
            center = sum([obj.matrix_world @ v.co for v in verts], Vector()) / len(verts)
            bone_matrix_inv = bone_matrix.inverted()

            for vert in verts:
                vert_world_co = obj.matrix_world @ vert.co
                bone_space_co = bone_matrix_inv @ vert_world_co

                # 整列
                bone_space_center = bone_matrix_inv @ center
                bone_space_co.y = bone_space_center.y

                vert_world_co = bone_matrix @ bone_space_co
                vert.co = obj.matrix_world.inverted() @ vert_world_co

        bmesh.update_edit_mesh(obj.data)

        self.print_time()
        return {"FINISHED"}


classes = [
    MESH_OT_mio3_snap_to_bone,
    MESH_OT_mio3_snap_to_joint,
    MESH_OT_mio3_align_to_bone,
]


def register():
    for c in classes:
        bpy.utils.register_class(c)


def unregister():
    for c in classes:
        bpy.utils.unregister_class(c)
