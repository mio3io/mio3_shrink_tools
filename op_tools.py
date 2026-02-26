import math
import bpy
import bmesh
from mathutils import Vector
from bpy.props import BoolProperty, FloatProperty, EnumProperty
from .utils import (
    Mio3ShrinkToolsBase,
    find_edge_loops_by_edges,
    find_x_mirror_verts,
    find_x_mirror_edges,
    find_bone_by_weight,
    find_islands,
)


def reset_shape_keys(obj):
    basis_kb = obj.data.shape_keys.reference_key
    try:
        bpy.ops.mesh.blend_from_shape(shape=basis_kb.name, blend=1, add=False)
    except Exception as e:
        print("Error resetting shape keys:", str(e))


def find_target_edges(obj, armature, selected_edges, angle_threshold):
    cos_threshold = math.cos(math.radians(angle_threshold))
    target_selected_edges = set()
    for edge in selected_edges:
        if bone := find_bone_by_weight(obj, armature, edge.verts):
            direction = (bone.tail_local - bone.head_local).normalized()
            v1, v2 = edge.verts
            edge_vector = v2.co - v1.co
            edge_vector.normalize()
            if abs(edge_vector.dot(direction)) < cos_threshold:
                target_selected_edges.add(edge)
    return target_selected_edges


class MESH_OT_mio3_shrink_snap(bpy.types.Operator, Mio3ShrinkToolsBase):
    bl_idname = "mesh.mio3_shrink_snap"
    bl_label = "Snap to Bone"
    bl_description = "Snap selected vertices to bones"
    bl_options = {"REGISTER", "UNDO"}

    volume_type: EnumProperty(
        name="Type",
        description="スナップ方法の選択",
        items=[
            ("FIXED", "Fixed", "スナップ先から一定距離に移動"),
            ("RELATIVE", "Relative", "ボリュームに応じてスナップ先に近づける"),
        ],
    )
    overwrite: BoolProperty(name="初期位置から", default=True)
    align: BoolProperty(
        name="Align edge loops",
        description="シリンダータイプのメッシュをエッジループでグループ分けして整列します。エッジの角度によってうまく整列しないことがあります",
        default=True,
    )
    angle_threshold: FloatProperty(
        name="Angle Threshold",
        description="ベクトルとの最大角度",
        default=60.0,
        min=0.0,
        max=90.0,
        step=100.0,
    )
    volume_factor: FloatProperty(
        name="Volume",
        description="残すボリューム（0だと頂点が重なりミラー編集ができなくなることがあります）",
        default=0.05,  # 0.03
        min=0.0,
        max=1.0,
        step=5,
    )
    radius: FloatProperty(
        name="Radius",
        description="シュリンク後の半径（0だと頂点が重なりミラー編集ができなくなることがあります）",
        default=0.001,
        min=0.0,
        max=0.1,
        step=0.1,
        precision=3,
    )
    offset: FloatProperty(
        name="Offset", default=0, min=-1.0, max=1.0, step=1, description="Y軸の位置をオフセット"
    )

    def execute(self, context):
        self.start_time()
        obj = context.active_object

        if not obj.active_shape_key:
            obj.shape_key_add(name="Shrink")

        if self.overwrite:
            reset_shape_keys(obj)

        armature = obj.find_armature()

        bm = bmesh.from_edit_mesh(obj.data)
        bm.select_mode = {"EDGE"}
        bm.verts.ensure_lookup_table()
        bm.edges.ensure_lookup_table()

        vart_mode = False
        if obj.data.total_vert_sel == 1:
            vart_mode = True
            v = next(v for v in bm.verts if v.select)
            if obj.use_mesh_mirror_x:
                mirror_verts = find_x_mirror_verts(bm, {v})
                islands = [v, mirror_verts.pop()] if mirror_verts else [v]
            else:
                islands = [v]
        else:
            selected_edges = {e for e in bm.edges if e.select}
            if obj.use_mesh_mirror_x:
                selected_edges.update(find_x_mirror_edges(bm, selected_edges))

            # vertex_infos = {}
            # for edge in selected_edges:
            #     for v in edge.verts:
            #         if v.index not in vertex_infos:
            #             vertex_infos[v.index] = {"vert": v, "edges": set()}
            #         vertex_infos[v.index]["edges"].add(edge)

            if self.align:
                target_selected_edges = find_target_edges(obj, armature, selected_edges, self.angle_threshold)
            else:
                target_selected_edges = selected_edges

            islands = find_edge_loops_by_edges(target_selected_edges)

        arm_mw = armature.matrix_world
        obj_mw = obj.matrix_world
        obj_mw_inv = obj_mw.inverted()

        factor = 1 - self.volume_factor
        eps = 1e-12

        for el in islands:
            verts = {el} if vart_mode else {v for el in el for v in el.verts}
            bone = find_bone_by_weight(obj, armature, verts)
            if bone:
                bone_matrix = arm_mw @ bone.matrix_local
                bone_matrix_inv = bone_matrix.inverted()
                center = sum([obj_mw @ v.co for v in verts], Vector()) / len(verts)

                head = arm_mw @ bone.head_local
                tail = arm_mw @ bone.tail_local
                vec = tail - head

                if vec.length_squared < eps:
                    continue

                for vert in verts:
                    vert_world_co = obj_mw @ vert.co

                    if self.align:
                        bone_space_co = bone_matrix_inv @ vert_world_co
                        bone_space_center = bone_matrix_inv @ center
                        bone_space_co.y = bone_space_center.y
                        vert_world_co = bone_matrix @ bone_space_co

                    vert_to_bone = vert_world_co - head
                    proj_vec = vert_to_bone.project(vec)
                    snapped_pos = head + proj_vec

                    if self.offset:
                        snapped_pos = snapped_pos + vec.normalized() * (self.offset * vec.length)

                    if self.volume_type == "FIXED":
                        radial = vert_world_co - snapped_pos
                        if radial.length_squared > eps:
                            radial_dir = radial.normalized()
                        else:
                            bone_dir = vec.normalized()
                            tmp = Vector((1.0, 0.0, 0.0))
                            if abs(bone_dir.dot(tmp)) > 0.99:
                                tmp = Vector((0.0, 0.0, 1.0))
                            radial_dir = bone_dir.cross(tmp)
                            if radial_dir.length_squared <= eps:
                                radial_dir = Vector((0.0, 1.0, 0.0))
                            else:
                                radial_dir.normalize()

                        result_pos = obj_mw_inv @ (snapped_pos + radial_dir * self.radius)
                    else:
                        result_pos = obj_mw_inv @ vert_world_co.lerp(snapped_pos, factor)

                    vert.co = result_pos

        bmesh.update_edit_mesh(obj.data)
        self.print_time()

        return {"FINISHED"}

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False
        row = layout.row()
        row.prop(self, "volume_type", expand=True)
        if self.volume_type == "FIXED":
            layout.prop(self, "radius")
        else:
            layout.prop(self, "volume_factor")
        layout.prop(self, "align")
        col = layout.column()
        col.active = bool(self.align)
        col.prop(self, "angle_threshold")
        layout.prop(self, "offset")
        layout.prop(self, "overwrite")


class MESH_OT_mio3_shrink_joint(bpy.types.Operator, Mio3ShrinkToolsBase):
    bl_idname = "mesh.mio3_shrink_joint"
    bl_label = "Snap to Joint"
    bl_description = "Snap selected vertices to joints"
    bl_options = {"REGISTER", "UNDO"}

    snap_type: EnumProperty(
        name="Snap",
        description="スナップ方法の選択",
        items=[("AUTO", "Auto", ""), ("HEAD", "Head", ""), ("TAIL", "Tail", "")],
    )
    volume_factor: FloatProperty(
        name="Volume",
        description="残すボリューム（0だと頂点が重なりミラー編集ができなくなることがあります）",
        default=0.05,  # 0.03
        min=0.0,
        max=1.0,
        step=5,
    )
    overwrite: BoolProperty(name="初期位置から", default=True)

    def execute(self, context):
        self.start_time()
        obj = context.active_object

        if self.overwrite:
            reset_shape_keys(obj)

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
                if self.snap_type == "HEAD":
                    target_world = armature.matrix_world @ bone.head_local
                elif self.snap_type == "TAIL":
                    target_world = armature.matrix_world @ bone.tail_local
                else:
                    is_end = len(bone.children) == 0
                    head = armature.matrix_world @ bone.head_local
                    tail = (
                        armature.matrix_world @ bone.tail_local
                        if not is_end
                        else head.lerp(armature.matrix_world @ bone.tail_local, 0.95)
                    )
                    to_head_sq = (center_world - head).length_squared
                    to_tail_sq = (center_world - tail).length_squared
                    target_world = head if to_head_sq < to_tail_sq else tail

                for vert in verts:
                    vert_world = obj.matrix_world @ vert.co
                    vert.co = obj.matrix_world.inverted() @ vert_world.lerp(target_world, factor)

        bmesh.update_edit_mesh(obj.data)
        self.print_time()
        return {"FINISHED"}

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False
        row = layout.row()
        row.prop(self, "snap_type", expand=True)
        layout.prop(self, "volume_factor")
        layout.prop(self, "overwrite")


class MESH_OT_mio3_align_to_bone(bpy.types.Operator, Mio3ShrinkToolsBase):
    bl_idname = "mesh.mio3_align_to_bone"
    bl_label = "Align edge loops"
    bl_description = "Align the selected edge loop perpendicular to the bone"
    bl_options = {"REGISTER", "UNDO"}

    angle_threshold: FloatProperty(
        name="Angle Threshold",
        description="ベクトルとの最大角度",
        default=60.0,
        min=0.0,
        max=90.0,
        step=100.0,
    )

    def execute(self, context):
        self.start_time()

        obj = context.active_object

        bm = bmesh.from_edit_mesh(obj.data)
        bm.verts.ensure_lookup_table()
        bm.edges.ensure_lookup_table()

        armature = obj.find_armature()

        selected_edges = {e for e in bm.edges if e.select}
        if obj.use_mesh_mirror_x:
            selected_edges.update(find_x_mirror_edges(bm, selected_edges))

        target_selected_edges = find_target_edges(obj, armature, selected_edges, self.angle_threshold)
        islands = find_edge_loops_by_edges(target_selected_edges)

        for loop in islands:
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
    MESH_OT_mio3_shrink_snap,
    MESH_OT_mio3_shrink_joint,
    MESH_OT_mio3_align_to_bone,
]


def register():
    for c in classes:
        bpy.utils.register_class(c)


def unregister():
    for c in classes:
        bpy.utils.unregister_class(c)
