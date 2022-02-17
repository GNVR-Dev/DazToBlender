from . import DazRigBlend
from . import DtbShapeKeys
from . import DataBase
from . import ToRigify
from . import Global
from . import Versions
from . import DtbDazMorph
from . import DtbMaterial
from . import CustomBones
from . import Poses
from . import Animations
from . import Util
from . import DtbCommands
from . import DtbIKBones
from . import DtbProperties
from . import DtbImports

import bpy
from bpy_extras.io_utils import ImportHelper
from bpy.props import EnumProperty
from bpy.props import BoolProperty
from bpy.props import StringProperty
from bpy.props import PointerProperty
import os
import json

from copy import deepcopy

region = "UI"
BV = Versions.getBV()

# Start of Utlity Classes
def reload_dropdowns(version):
    if version == "choose_daz_figure":
        w_mgr = bpy.types.WindowManager
        prop = Versions.get_properties(w_mgr.choose_daz_figure)
        for arm in Util.all_armature():
            check = [x for x in prop["items"] if x[0] == arm.name]
            if len(check) == 0:
                if "Asset Name" in arm.keys():
                    prop["items"].append(
                        (arm.name, arm["Asset Name"], arm["Collection"])
                    )
        w_mgr.choose_daz_figure = EnumProperty(
            name=prop["name"],
            description=prop["description"],
            items=prop["items"],
            default=Global.get_Amtr_name(),
        )


class OP_SAVE_CONFIG(bpy.types.Operator):
    bl_idname = "save.daz_settings"
    bl_label = "Save Config"
    bl_description = "Saves the Configuration to be used by Daz and Blender"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        scn = context.scene
        w_mgr = context.window_manager
        config = Global.get_config_path()
        with open(os.path.join(config, "daz_paths.json"), "r") as f:
            data = json.load(f)
        data["Custom Path"] = scn.dtb_custom_path.path.replace("\\", "/")
        data["Use Custom Path"] = w_mgr.use_custom_path
        with open(os.path.join(config, "daz_paths.json"), "w") as f:
            json.dump(data, f, indent=2)
        self.report({"INFO"}, "Config Saved!")
        return {"FINISHED"}


class REFRESH_DAZ_FIGURES(bpy.types.Operator):
    bl_idname = "refresh.alldaz"
    bl_label = "Refresh All Daz Figures"
    bl_description = (
        "Refreshes List of Figures\nOnly needed if figure is not in dropdown"
    )
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        w_mgr = bpy.types.WindowManager
        prop = Versions.get_properties(w_mgr.choose_daz_figure)
        check = ["null"]
        for arm in Util.all_armature():
            check = [x for x in prop["items"] if x[0] == arm.name]
            if len(check) == 0:
                if "Asset Name" in arm.keys():
                    prop["items"].append(
                        (arm.name, arm["Asset Name"], arm["Collection"])
                    )
        if "null" in check:
            prop["items"] = [("null", "Choose Character", "Default Value")]
        w_mgr.choose_daz_figure = EnumProperty(
            name=prop["name"],
            description=prop["description"],
            items=prop["items"],
            default=prop["default"],
        )
        return {"FINISHED"}


class REMOVE_DAZ_OT_button(bpy.types.Operator):
    bl_idname = "remove.alldaz"
    bl_label = "Remove All Daz"
    bl_description = "Clears out all imported assets\nCurrently deletes all Materials"
    bl_options = {"REGISTER", "UNDO"}

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)

    def execute(self, context):
        col = bpy.data.collections.get("DAZ_ROOT")
        if col is not None:
            for c in col.children:
                for obj in c.objects:
                    bpy.data.objects.remove(obj)
                bpy.data.collections.remove(c)
            for material in bpy.data.materials:
                material.user_clear()
                bpy.data.materials.remove(material)
        return {"FINISHED"}


class RENAME_MORPHS(bpy.types.Operator):
    bl_idname = "rename.morphs"
    bl_label = "Remove Morph Prefix"

    def execute(self, context):
        Global.setOpsMode("OBJECT")
        selected_objects = []
        fig_object_name = bpy.context.window_manager.choose_daz_figure
        if fig_object_name == "null":
            selected_objects.append(bpy.context.object)
        else:
            selected_objects = Global.get_children(bpy.data.objects[fig_object_name])
        for selected_object in selected_objects:

            if selected_object is None or selected_object.type != "MESH":
                self.report({"WARNING"}, "Select Object or Choose From Dropdown")
                continue
            if selected_object.data.shape_keys is None:
                self.report(
                    {"INFO"}, "No Morphs found on {0}".format(selected_object.name)
                )
                continue
            # get its shapekeys
            shape_keys = selected_object.data.shape_keys.key_blocks
            string_to_replace = selected_object.data.name + "__"
            # loop through shapekeys and replace the names
            for key in shape_keys:
                key.name = key.name.replace(string_to_replace, "")
        self.report({"INFO"}, "Morphs renamed!")

        return {"FINISHED"} 

# End of Utlity Classes

# Start of Import Classes
def start_model_import(import_type):
    from . import Environment
    # setup file path
    if import_type == 'FIG' or import_type == 'ENV':
        file_path = os.path.join(Global.getRootPath(),import_type,import_type+'0')
        if bpy.context.window_manager.use_custom_path:
            dtu_address = os.path.join(Global.get_custom_path() ,file_path)
        #find dtu file in folder
        for file in os.listdir(file_path):
            if file.endswith(".dtu"):
                dtu_address = os.path.join(file_path, file)
                break
        Environment.dtu_address = dtu_address
    else:
        Environment.dtu_address = dtu_address
    # send .dtu address to Environment.py for processing    
    Environment.Import_Models()
    return

class IMP_OT_FIG(bpy.types.Operator):

    bl_idname = "import_figure.dtu"
    bl_label = "Import New Genesis Figure"
    bl_description = "Supports Genesis 3, 8, and 8.1"
    bl_options = {"REGISTER", "UNDO"}

    def invoke(self, context, event):
        if bpy.data.is_dirty:
            return context.window_manager.invoke_confirm(self, event)
        non_interactive_mode = False
        return self.execute(context)

    def execute(self, context):

        start_model_import('FIG')

        return {"FINISHED"}



class IMP_OT_ENV(bpy.types.Operator):

    bl_idname = "import_environment.dtu"
    bl_label = "Import New Env/Prop"
    bl_description = "Import Environment"
    bl_options = {"REGISTER", "UNDO"}

    def invoke(self, context, event):
        if bpy.data.is_dirty:
            return context.window_manager.invoke_confirm(self, event)
        non_interactive_mode = False
        return self.execute(context)

    def execute(self, context):

        start_model_import('ENV')

        return {"FINISHED"}


# Start of Pose Classes
class IMP_OT_POSE(bpy.types.Operator, ImportHelper):
    """Imports Daz Poses (.DUF)"""

    bl_idname = "import.pose"
    bl_label = "Import Pose"
    bl_options = {"REGISTER", "UNDO"}
    filename_ext: StringProperty(
        default=".duf",
        options={"HIDDEN"},
    )
    filter_glob: StringProperty(
        default="*.duf",
        options={"HIDDEN"},
    )
    files: bpy.props.CollectionProperty(type=DtbProperties.ImportFilesCollection)

    def execute(self, context):
        # Instance Classes
        pose = Poses.Posing("POSE")
        dirname = os.path.dirname(self.filepath)
        for i, f in enumerate(self.files, 1):
            durPath = os.path.join(dirname, f.name)
            pose.pose_copy(durPath)
        return {"FINISHED"}


class CLEAR_OT_Pose(bpy.types.Operator):

    bl_idname = "my.clear"
    bl_label = "Clear All Pose"

    def clear_pose(self):
        if bpy.context.object is None:
            return
        if (
            Global.getAmtr() is not None
            and Versions.get_active_object() == Global.getAmtr()
        ):
            for pb in Global.getAmtr().pose.bones:
                pb.bone.select = True
        if (
            Global.getRgfy() is not None
            and Versions.get_active_object() == Global.getRgfy()
        ):
            for pb in Global.getRgfy().pose.bones:
                pb.bone.select = True
        bpy.ops.pose.transforms_clear()
        bpy.ops.pose.select_all(action="DESELECT")

    def execute(self, context):
        self.clear_pose()
        return {"FINISHED"}


# End of Pose Classes

# Start of Material Classes


class OPTIMIZE_OT_material(bpy.types.Operator):
    bl_idname = "df.optimize"
    bl_label = "Optimize Materials(WIP)"

    def execute(self, context):
        DtbMaterial.optimize_materials()
        return {"FINISHED"}


# End of Material Classes


# Start of Rigify Classes


def clear_pose():
    if bpy.context.object is None:
        return
    if (
        Global.getAmtr() is not None
        and Versions.get_active_object() == Global.getAmtr()
    ):
        for pb in Global.getAmtr().pose.bones:
            pb.bone.select = True
    if (
        Global.getRgfy() is not None
        and Versions.get_active_object() == Global.getRgfy()
    ):
        for pb in Global.getRgfy().pose.bones:
            pb.bone.select = True
    bpy.ops.pose.transforms_clear()
    bpy.ops.pose.select_all(action="DESELECT")


class TRANS_OT_Rigify(bpy.types.Operator):
    bl_idname = "to.rigify"
    bl_label = "To Rigify"

    def invoke(self, context, event):
        if bpy.data.is_dirty:
            return context.window_manager.invoke_confirm(self, event)
        return self.execute(context)

    def execute(self, context):
        clear_pose()
        Util.active_object_to_current_collection()
        dtu = DataBase.DtuLoader()
        trf = ToRigify.ToRigify(dtu)
        db = DataBase.DB()
        DtbIKBones.adjust_shin_y(2, False)
        DtbIKBones.adjust_shin_y(3, False)
        trf.toRigify(db, self)
        return {"FINISHED"}


# End of Rigify Classes
