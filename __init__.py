import bpy
from . import op_auto_shrink
from . import op_tools
from . import op_shape_keys


bl_info = {
    "name": "Mio3 Shrink Tools",
    "version": (1, 0, 0),
    "blender": (3, 6, 0),
    "location": "View 3D > Sidebar > Edit Tab > Mio3 Shrink Tools",
    "description": "Support tools for shrink-shape keys",
    "category": "Mesh",
}


class MMIO3SST_PT_main(bpy.types.Panel):
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Mio3"
    bl_label = "Mio3 Shrink Tools"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        return context.active_object and context.active_object.type == "MESH"

    def draw(self, context):
        layout = self.layout

        row = layout.row(align=True)
        row.operator("mesh.mio3_auto_shrink", icon="ARMATURE_DATA")

        layout.label(text="Manual Tools")
        col = layout.column(align=True)

        row = col.row(align=True)
        row.operator("mesh.mio3srt_shape_reset", text="Reset", icon="LOOP_BACK")
        row.operator("mesh.mio3_align_to_bone", text="Align", icon="COLLAPSEMENU")

        row = col.row(align=True)
        row.operator("mesh.mio3_shrink_snap", text="Snap", icon="SNAP_ON")
        row.operator("mesh.mio3_shrink_joint", text="Joint", icon="SNAP_MIDPOINT")

        row = col.row(align=True)
        row.operator("mesh.mio3srt_deselect_used")


def update_panel(self, context):
    is_exist = hasattr(bpy.types, "MMIO3SST_PT_main")
    category = bpy.context.preferences.addons[__package__].preferences.category
    if is_exist:
        try:
            bpy.utils.unregister_class(MMIO3SST_PT_main)
        except:
            pass

    MMIO3SST_PT_main.bl_category = category
    bpy.utils.register_class(MMIO3SST_PT_main)


class MMIO3SST_Preferences(bpy.types.AddonPreferences):
    bl_idname = __package__

    category: bpy.props.StringProperty(
        name="Tab Name",
        default="Edit",
        update=update_panel,
    )

    def draw(self, context):
        layout = self.layout
        layout.row().prop(self, "category")


translation_dict = {
    "en_US": {
        ("*", "DESC Auto Shrink"): "Automatically create shrink shape keys for deform bones\nHide bones you want to exclude, such as auxiliary bones and bust bones, in pause mode.",
    },
    "ja_JP": {
        ("Operator", "Auto Shrink"): "シュリンクを自動生成",
        ("*", "DESC Auto Shrink"): "デフォームボーンのシュリンクシェイプキーを自動的に作成\n補助ボーンや胸ボーンなど対象外にしたいボーンはポーズモードで隠してください",

        ("*", "Manual Tools"): "マニュアルツール",

        ("Operator", "Align edge loops"): "エッジループを整列",
        ("*", "Align edge loops"): "エッジループを整列",
        ("Operator", "Snapping a vertex to a bone"): "頂点をボーンにスナップ",
        ("Operator", "Snap selected vertices to bones"): "選択した頂点をボーンにスナップ",
        ("*", "Align the selected edge loop perpendicular to the bone"): "選択したエッジループをボーンに対して垂直に整列",

        ("*", "Selected bones only"): "選択したボーンのみ",
        ("*", "Selected vertices only"): "選択した頂点のみ",

        ("*", "End Bone"): "エンドボーン",
        ("Operator", "Snap to Bone"): "ボーンにスナップ",
        ("Operator", "Snap to Joint"): "関節にスナップ",
        ("*", "Snap to Joint"): "関節にスナップ",
        ("Operator", "Align to Bone"): "ボーンに整列",
        ("Operator", "Joint"): "関節",
        ("Operator", "Deselect Shape Key Moved"): "変位頂点の選択を解除",
        ("*", "Snap selected vertices to bones"): "選択した頂点をボーンにスナップ",
        ("*", "Snap selected vertices to joints"): "選択した頂点を関節にスナップ",

        ("*", "Reset the shape keys to their default state"): "シェイプキーをデフォルト状態にリセット",
        ("*", "Deselect vertices that have been moved in the active shape key"): "アクティブなシェイプキーで移動している頂点の選択のみを解除",

        # Messages
        ("*", "Armature modifier not set"): "アーマチュアが設定されていません",
        ("*", "Register ShapeKey for Shrink"): "シュリンク用シェイプキーを登録してください",
        ("*", "No deform bone shown"): "表示されているデフォームボーンがありません",
    }
}  # fmt: skip


ops = [
    op_auto_shrink,
    op_tools,
    op_shape_keys,
]


def register():
    bpy.app.translations.register(__name__, translation_dict)
    bpy.utils.register_class(MMIO3SST_Preferences)
    bpy.utils.register_class(MMIO3SST_PT_main)
    for op in ops:
        op.register()


def unregister():
    for op in reversed(ops):
        op.unregister()
    bpy.utils.unregister_class(MMIO3SST_PT_main)
    bpy.utils.unregister_class(MMIO3SST_Preferences)
    bpy.app.translations.unregister(__name__)


if __name__ == "__main__":
    register()
