import bpy
from . import op_auto_shrink
from . import op_tools

bl_info = {
    "name": "Mio3 Shrink Tools",
    "version": (0, 9),
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

    def draw(self, context):
        layout = self.layout
        col = layout.column()
        row = col.row(align=True)
        row.operator("mesh.mio3_auto_shrink", icon="ARMATURE_DATA")

        row = layout.row(align=True)
        row.label(text="Snap")
        op = row.operator("mesh.mio3_snap_to_bone", text="並行")
        row.operator("mesh.mio3_snap_to_joint", text="関節")

        row = layout.row(align=True)
        row.operator("mesh.mio3_align_to_bone", text="Align", icon="CURVES")


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
        ("*", "Snapping a vertex to a bone"): "頂点をボーンにスナップ",
        ("*", "Snap selected vertices to bones"): "選択した頂点をボーンにスナップ",
        ("*", "Align edge loops"): "エッジループを整列",
        ("*", "Align the selected edge loop perpendicular to the bone"): "選択したエッジループをボーンに対して垂直に整列させます",

        ("*", "Selected bones only"): "選択したボーンのみ",
        ("*", "Selected vertices only"): "選択した頂点のみ",
        ("Operator", "Verts Only"): "頂点のみ",
        ("Operator", "Bone Only"): "ボーンのみ",

        ("*", "End Bone"): "エンドボーン",
        ("*", "Joint Snap"): "関節スナップ",

        ("*", "Armature modifier not set"): "アーマチュアが設定されていません",
        ("*", "Register ShapeKey for Shrink"): "シュリンク用シェイプキーを登録してください",
        ("*", "Please select only edges"): "エッジのみ選択してください",
        ("*", "No deform bone shown"): "表示されているデフォームボーンがありません",
    }
}  # fmt: skip


ops = [
    op_auto_shrink,
    op_tools,
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
