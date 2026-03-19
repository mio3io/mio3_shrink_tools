import bpy
import bmesh
from mathutils import Vector
from bpy.props import BoolProperty, FloatProperty, EnumProperty
from .utils import Mio3ShrinkToolsBase, find_x_mirror_verts, find_x_mirror_vert_pairs

ver_5 = bpy.app.version >= (5, 0, 0)


class MESH_OT_mio3_auto_shrink(bpy.types.Operator, Mio3ShrinkToolsBase):
    bl_idname = "mesh.mio3_auto_shrink"
    bl_label = "Auto Shrink"
    bl_description = "DESC Auto Shrink"
    bl_options = {"REGISTER", "UNDO"}

    mode: EnumProperty(
        name="Mode",
        items=[("SNAP", "Standard", ""), ("SMOOTH", "Smooth", "")],
    )
    selected_bone_only: BoolProperty(name="Selected bones only", default=False)
    selected_vert_only: BoolProperty(name="Selected vertices only", default=True)
    end_bone_snap: EnumProperty(
        name="End Bone",
        items=[("HEAD", "Head", ""), ("TAIL", "Tail", "")],
        default="TAIL",
    )
    snap_factor: FloatProperty(
        name="Snap to Joint",
        description="関節にスナップさせるしきい値",
        default=0.99,
        min=0.0,
        max=1.0,
        step=5,
    )
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
        return context.object is not None and context.object.type == "MESH"

    def execute(self, context):
        self.start_time()
        obj = context.active_object
        is_edit = obj.mode == "EDIT"

        if not is_edit:
            bpy.ops.object.mode_set(mode="EDIT")

        armature = obj.find_armature()
        obj_world_mat = obj.matrix_world
        obj_world_mat_inv = obj_world_mat.inverted()
        arm_world_mat = armature.matrix_world

        if ver_5:
            visible = {b.name for b in armature.pose.bones if not b.hide}
            selected = {b.name for b in armature.pose.bones if not b.hide and b.select}
            pose_bone_names = selected if self.selected_bone_only and selected else visible
            target_bones = [b for b in armature.data.bones if b.use_deform and b.name in pose_bone_names]
        else:
            target_bones = [bone for bone in armature.data.bones if bone.select and bone.use_deform]
            if not target_bones:
                target_bones = [bone for bone in armature.data.bones if not bone.hide and bone.use_deform]

        bone_infos = {}
        for bone in target_bones:
            if vg := obj.vertex_groups.get(bone.name):
                bone_head = arm_world_mat @ bone.head_local
                bone_tail = arm_world_mat @ bone.tail_local
                bone_vec = bone_tail - bone_head
                is_end = len(bone.children) == 0
                bone_tail = bone_head.lerp(bone_tail, 0.95) if is_end else bone_tail
                bone_infos[vg.index] = (bone_head, bone_tail, bone_vec, is_end)

        if not bone_infos:
            return {"CANCELLED"}

        bm = bmesh.from_edit_mesh(obj.data)
        bm.verts.ensure_lookup_table()

        mode = self.mode
        volume_factor = 1 - self.volume_factor
        snap_factor = self.snap_factor
        end_bone_snap = self.end_bone_snap

        vertices = obj.data.vertices

        if self.selected_vert_only:
            target_verts = {v for v in bm.verts if v.select}
            if obj.use_mesh_mirror_x:
                target_verts.update(find_x_mirror_verts(bm, target_verts))
        else:
            target_verts = set(bm.verts)

        for vert in target_verts:
            world_co = obj_world_mat @ vert.co
            total_weighted_pos = Vector((0.0, 0.0, 0.0))

            mesh_vert = vertices[vert.index]
            target_groups = []
            target_total_weight = 0.0
            for group in mesh_vert.groups:
                bone_info = bone_infos.get(group.group)
                if bone_info is None or group.weight <= 0.0:
                    continue
                target_groups.append((group.weight, bone_info))
                target_total_weight += group.weight

            if target_total_weight < 1e-6:
                continue

            for weight, bone_info in target_groups:
                normalized_weight = weight / target_total_weight
                snap_pos = self.calc_snap_pos(
                    mode, end_bone_snap, snap_factor, world_co, normalized_weight, bone_info
                )

                total_weighted_pos += snap_pos * normalized_weight

            vert.co = obj_world_mat_inv @ world_co.lerp(total_weighted_pos, volume_factor)

        bmesh.update_edit_mesh(obj.data)

        if is_edit is False:
            bpy.ops.object.mode_set(mode="OBJECT")

        self.print_time()
        return {"FINISHED"}

    @staticmethod
    def calc_snap_pos(mode, end_bone_snap, snap_factor, world_co, weight, bone_info):
        head, tail, vec, is_end = bone_info
        """スナップする位置を計算する"""
        # 末端ボーン
        if is_end:
            bone = tail if end_bone_snap == "TAIL" else head  # tail側 末端突き抜け対策
            if weight < snap_factor:
                vert_to_bone = world_co - bone
                proj_vec = vert_to_bone.project(vec)
                return bone + proj_vec
            return bone

        dist_to_head_sq = (world_co - head).length_squared
        dist_to_tail_sq = (world_co - tail).length_squared

        if mode == "SMOOTH":
            if vec.length_squared == 0.0:
                snapped_pos = head
            else:
                vert_to_bone = world_co - head
                proj_vec = vert_to_bone.project(vec)
                snapped_pos = head + proj_vec

            if dist_to_head_sq < dist_to_tail_sq:
                return head.lerp(snapped_pos, weight)
            return tail.lerp(snapped_pos, weight)

        # mode == "SNAP"
        if weight < snap_factor:
            return head if dist_to_head_sq < dist_to_tail_sq else tail

        if vec.length_squared == 0.0:
            return head
        vert_to_bone = world_co - head
        proj_vec = vert_to_bone.project(vec)
        return head + proj_vec

    def draw(self, context):
        layout = self.layout
        row = layout.row()
        row.prop(self, "mode", expand=True)

        layout.use_property_split = True
        layout.use_property_decorate = False
        layout.prop(self, "selected_bone_only")
        layout.prop(self, "selected_vert_only")

        row = layout.row()
        row.prop(self, "end_bone_snap", expand=True)
        layout.prop(self, "snap_factor")
        layout.prop(self, "volume_factor")


classes = [MESH_OT_mio3_auto_shrink]


def register():
    for c in classes:
        bpy.utils.register_class(c)


def unregister():
    for c in classes:
        bpy.utils.unregister_class(c)
