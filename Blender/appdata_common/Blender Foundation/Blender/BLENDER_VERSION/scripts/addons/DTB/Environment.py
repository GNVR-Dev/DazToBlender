import bpy
import os
import json
import math
from . import Versions
from . import Global
from . import Util
from . import DtbMaterial
from . import NodeArrange
from . import Poses
from . import DataBase
from . import DazRigBlend
from . import Animations
from . import DtbShapeKeys
from . import DtbIKBones

import re
from bpy.props import EnumProperty

#default to "" - will be set by operator or automation 
#folder_path = ""
dtu_address = ""
dtu = DataBase.DtuLoader()

file_name = ""

def set_transform(obj,data,type):
    if type == "scale":
        transform = obj.scale
    if type == "rotate":
        transform = obj.rotation_euler
        for i in range(len(data)):
            data[i] = math.radians(data[i])
    if type == "translate":
        transform = obj.location
    for i in range(3):
        transform[i] = float(data[i])    
def progress_bar(percent):
    bpy.context.window_manager.progress_update(percent)

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

class Import_Models():

    def __init__(self):
        Util.deleteEmptyDazCollection() # Remove Empty Collections
        folder_path = ""
        self.execute()

    def execute(self):

        wm = bpy.context.window_manager
        wm.progress_begin(0, 100)
        Versions.active_object_none() # deselect all

        Global.dtu_address = dtu_address.replace("/", "\\")
        self.find_fbx_from_dtu_file(dtu_address,0)

        progress_bar(0)
        dirs = os.listdir(Global.folder_path)
        print ("got here")
        
        import_dirs = [f for f in dirs if os.path.isdir(os.path.join(Global.folder_path, f))]
        for j in range(len(import_dirs)):
            print ("length of file =", str(j))
        int_progress = 100/len(dirs)
            
        for i in range(len(import_dirs)):
            print ("made it here")
            if i > 0:
                new_dtu_address = os.path.join(Global.folder_path,Global.import_type+str(i))
                for file in os.listdir(new_dtu_address):
                    if file.endswith(".dtu"):
                        new_dtu_address = os.path.join(Global.folder_path,Global.import_type+str(i), file)
                    break
                print ("i equals ",i)
                self.find_fbx_from_dtu_file(new_dtu_address,i)
                Global.clear_variables()
                if Global.non_interactive_mode == False:
                    Global.fbx_address=(os.path.join(Global.folder_path,Global.import_type+str(i),Global.file_name))
            print ("global fbx address =",Global.fbx_address) 
            Util.decideCurrentCollection(Global.import_type)
            progress_bar(int(int_progress * i) + 5)
            ReadFbx( i, int_progress)
            Versions.active_object_none()
        progress_bar(100)
        Global.setOpsMode("OBJECT")
        wm.progress_end()
        Versions.make_sun()
        if Global.non_interactive_mode == False:
            Global.scale_settings()
        return {"FINISHED"}

    def set_default_settings(self):
        if bpy.context.window_manager.update_scn_settings:
            bpy.context.preferences.inputs.use_mouse_depth_navigate = True
            bpy.context.scene.render.engine = 'CYCLES'
            bpy.context.space_data.shading.type = 'SOLID'
            bpy.context.space_data.shading.color_type = 'OBJECT'
            bpy.context.space_data.shading.show_shadows = False
        bco = bpy.context.object
        if bco != None and bco.mode != 'OBJECT':
            Global.setOpsMode('OBJECT')
        bpy.ops.view3d.snap_cursor_to_center()

    def find_fbx_from_dtu_file(self,new_dtu_address, idx):

        new_dtu_address = new_dtu_address.replace("/", "\\")
        print ("New dtu address is", new_dtu_address)

        if new_dtu_address.endswith(".dtu"):
            print ("dtu address is ", new_dtu_address)
            dtu.load_dtu

            fbx_path = dtu.get_fbx_path() # get fbx_file from .dtu file
            fbx_path = fbx_path.replace("/", "\\")
            fbx_path = fbx_path.rstrip()
            print ("fbx path=",fbx_path)
            if fbx_path == 'ENV/ENV0/B_ENV.fbx': 
                folder_path = os.path.join(dtu_address[:dtu_address.rfind('\\ENV0\\')])
                file_name = 'B_ENV.fbx'
            elif fbx_path == 'FIG/FIG0/B_FIG.fbx':  # if the fbx path is the default /FIG/FIG0/B_FIG.fbx
                folder_path = os.path.join(dtu_address[:dtu_address.rfind('\\FIG0\\')])
                file_name = 'B_FIG.fbx'
                print ("fbx address =",fbx_path)
            else:           
                Global.folder_path = os.path.join(fbx_path[:fbx_path.rfind('\\')])
                Global.folder_path = os.path.join(Global.folder_path[:Global.folder_path.rfind('\\')])
                print ("Global.folder_path = ",Global.folder_path)
                Global.fbx_address = fbx_path

            # get asset type from dtu file
            asset_type = dtu.get_asset_type()
            Global.asset_type = asset_type
            print ("Asset_type is ",asset_type)
            if asset_type == 'Set':
                Global.import_type = "ENV"               

            else:           
                Global.import_type = "FIG"
                return
        else:
            print ("Please use .dtu file for import")
            return
        print ("made it to return")

class ReadFbx:
    adr = ""
    index = 0
    my_meshs = []


    def __init__(self,i,int_progress):
        self.dtu = DataBase.DtuLoader()
        self.drb = DazRigBlend.DazRigBlend(self.dtu)
        self.pose = Poses.Posing(self.dtu)
        self.dtb_shaders = DtbMaterial.DtbShaders(self.dtu)
        self.anim = Animations.Animations(self.dtu)
        self.db = DataBase.DB()
        self.my_meshs = []
        self.index = i 
        self.dsk = DtbShapeKeys.DtbShapeKeys(False, self.dtu)
        if self.read_fbx():
            progress_bar(int(i * int_progress)+int(int_progress / 2))
            self.setMaterial()

    def pbar(self, v, wm):
        wm.progress_update(v)

    def read_fbx(self):
        self.my_meshs = []
        adr = Global.fbx_address 
        if os.path.exists(Global.fbx_address) == False:
            return
        objs = self.convert_file(Global.fbx_address)
        print (str(len(objs)))
        for obj in objs:
            if obj.type == 'MESH':
                self.my_meshs.append(obj)
        if objs is None or len(objs) == 0:
            return

        # Model imported - Now finalize
        if Global.import_type == "ENV": #Finalize Environment import
            Global.find_ENVROOT(objs[0])
            root = Global.getEnvRoot()
            if len(objs) > 1:
                if root is None:
                    return
                else:
                    objs.remove(root)
            else:
                root = objs[0]
        # Temporaily Delete Animation Until Support is Added
            root.animation_data_clear()
            for obj in objs:
                obj.animation_data_clear()
            Versions.active_object(root)

            Global.deselect()
            if root.type == 'ARMATURE':
                self.import_as_armature(objs, root)
            #TODO: Remove Groups with no MESH   
            elif root.type == 'EMPTY':
                no_empty = False
                for o in objs:
                    if o.type != 'EMPTY':
                        no_empty = True
                        break
                if no_empty == False:
                    for o in objs:
                        bpy.data.objects.remove(o)
                    return False
                else:
                    self.import_empty(objs, Global.getEnvRoot())
            Global.change_size(Global.getEnvRoot())
        
        else: #Finalize figure import

            Util.decideCurrentCollection("FIG")
            wm = bpy.context.window_manager
            wm.progress_begin(0, 100)
            Global.clear_variables()
            DtbIKBones.ik_access_ban = True

            #self.anim.reset_total_key_count()
            self.pbar(10, wm)            
            Global.load_dtu(self.dtu)
            Global.store_variables()
            self.pbar(15, wm)
            if Global.getAmtr() is not None and Global.getBody() is not None:

                # Set Custom Properties
                Global.getAmtr()["Asset Name"] = self.dtu.get_asset_name()
                Global.getAmtr()["Collection"] = Util.cur_col_name()
                reload_dropdowns("choose_daz_figure")
                self.pose.add_skeleton_data()

                Global.deselect()  # deselect all the objects
                self.pose.clear_pose()  # Select Armature and clear transform
                self.drb.mub_ary_A()  # Find and read FIG.dat file
                self.drb.orthopedy_empty()  # On "EMPTY" type objects
                self.pbar(18, wm)
                self.drb.orthopedy_everything()  # clear transform, clear and reapply parent, CMs -> METERS
                Global.deselect()
                self.pbar(20, wm)
                self.drb.set_bone_head_tail()  # Sets head and tail positions for all the bones
                Global.deselect()
                self.pbar(25, wm)
                self.drb.bone_limit_modify()
                if self.anim.has_keyframe(Global.getAmtr()):
                    self.anim.clean_animations()
                Global.deselect()
                self.pbar(30, wm)
                self.drb.unwrapuv()
                Global.deselect()

                # materials
                self.dtb_shaders.make_dct()
                self.dtb_shaders.load_shader_nodes()
                body = Global.getBody()
                self.dtb_shaders.setup_materials(body)
                self.pbar(35, wm)

                fig_objs_names = [Global.get_Body_name()]
                for obj in Util.myacobjs():
                    # Skip for any of the following cases
                    case1 = not Global.isRiggedObject(obj)
                    case2 = obj.name in fig_objs_names
                    if case1 or case2:
                        continue
                    self.dtb_shaders.setup_materials(obj)

                self.pbar(40, wm)

                if Global.getIsGen():
                    drb.fixGeniWeight(db)
                Global.deselect()
                self.pbar(45, wm)
                Global.setOpsMode("OBJECT")
                Global.deselect()

                # Shape keys
                self.dsk.make_drivers()
                Global.deselect()
                self.pbar(60, wm)

                self.drb.makeRoot()
                self.drb.makePole()
                self.drb.makeIK()
                self.drb.pbone_limit()
                self.drb.mub_ary_Z()
                self.pbar(70, wm)
                Global.setOpsMode("OBJECT")
                try:
                    CustomBones.CBones()
                except:
                    print("Custom bones currently not supported for this character")
                self.pbar(80, wm)
                Global.setOpsMode("OBJECT")
                Global.deselect()
                self.pbar(90, wm)
                amt = Global.getAmtr()
                for bname in DtbIKBones.bone_name:
                    if bname in amt.pose.bones.keys():
                        bone = amt.pose.bones[bname]
                        for bc in bone.constraints:
                            if bc.name == bname + "_IK":
                                pbik = amt.pose.bones.get(bname + "_IK")
                                amt.pose.bones[bname].constraints[
                                    bname + "_IK"
                                ].influence = 0
                self.drb.makeBRotationCut(self.db)  # lock movements around axes with zeroed limits for each bone
                Global.deselect()

                # materials
                DtbMaterial.forbitMinus()
                self.pbar(95, wm)
                Global.deselect()

                Versions.active_object(Global.getAmtr())
                Global.setOpsMode("POSE")
                self.drb.mub_ary_Z()
                Global.setOpsMode("OBJECT")
                self.drb.finishjob()
                Global.setOpsMode("OBJECT")
                if not self.anim.has_keyframe(Global.getAmtr()):
                    self.pose.update_scale()
                    self.pose.restore_pose()  # Run when no animation exists.
                DtbIKBones.bone_disp(-1, True)
                DtbIKBones.set_scene_settings(self.anim.total_key_count)
                self.pbar(100, wm)
                DtbIKBones.ik_access_ban = False
                if bpy.context.window_manager.morph_prefix:
                    bpy.ops.rename.morphs('EXEC_DEFAULT')
                #self.report({"INFO"}, "Success")
                print ("Success")
            else:
                #self.show_error()
                print ("Failed")

            wm.progress_end()
            DtbIKBones.ik_access_ban = False

        return True
        
    
    def convert_file(self, filepath):
        Global.store_ary(False) #Gets all objects before.
        basename = os.path.basename(filepath)
        (filename, fileext) = os.path.splitext(basename)
        ext = fileext.lower()
        if os.path.isfile(filepath):
            if ext == '.fbx':
                bpy.ops.import_scene.fbx(
                    filepath = filepath,
                    use_manual_orientation = False,
                    #global_scale = 1,
                    bake_space_transform = False,
                    use_image_search = True,
                    use_anim = True,
                    anim_offset = 0,
                    ignore_leaf_bones = False,
                    force_connect_children = False,
                    automatic_bone_orientation = False,
                    primary_bone_axis = 'Y',
                    secondary_bone_axis = 'X',
                    use_prepost_rot = False
                    )
        Global.store_ary(True) #Gets all objects after.
        return self.new_objects()

    def new_objects(self):
        rtn = []
        if len(Global.now_ary) == len(Global.pst_ary):
            return ""
        rtn = [bpy.data.objects[n] for n in Global.now_ary if not n in Global.pst_ary]
        return rtn
    
    #TODO: combine shared code with figure import
    def import_as_armature(self, objs, amtr):
        
        Global.deselect()
        self.create_controller()
        vertex_group_names = []
        empty_objs = []
        amtr_objs = []
        
        for i in range(3):
            amtr.scale[i] = 1
            
        #Apply Armature Modifer if it does not exist
        for obj in objs:
            if obj.type == 'MESH':
                amtr_objs.append(obj)
                vgs = obj.vertex_groups
                if len(vgs) > 0:
                    vertex_group_names = [vg.name for vg in vgs]
                    if self.is_armature_modified(obj) == False:
                        amod = obj.modifiers.new(type='ARMATURE', name="ama" + obj.name)
                        amod.object = amtr
                self.pose.reposition_asset(obj, amtr)
            elif obj.type == 'EMPTY':
                if obj.parent == amtr:
                    empty_objs.append(obj)
        Global.deselect()
        
        

        #Apply rest pose        
        Versions.select(amtr, True)
        Versions.active_object(amtr)
        Global.setOpsMode("POSE")
        bpy.ops.pose.select_all(action='SELECT')
        bpy.ops.pose.armature_apply(selected=False)
        bpy.ops.pose.select_all(action='DESELECT')
        Global.setOpsMode("EDIT")
        
        hides = []
        bones = amtr.data.edit_bones
        
        #Fix and Check Bones to Hide
        for bone in bones:
            to_hide = self.pose.set_bone_head_tail(bone)
            if not to_hide:
                hides.append(bone.name)
                continue
            if bone.name not in vertex_group_names:
                if self.is_child_bone(amtr, bone, vertex_group_names) == False:
                    hides.append(bone.name)
                    continue
        
        Global.setOpsMode("OBJECT")
        for obj in objs:
            Versions.select(obj, True)
            Versions.active_object(obj)
            bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
            Versions.select(obj,False)

        Versions.select(amtr, True)
        Versions.active_object(amtr)
        Global.setOpsMode("POSE")
        amtr.show_in_front = True

        #Apply Custom Shape
        for pb in amtr.pose.bones:
            
            binfo = self.pose.get_bone_limits_dict(pb.name)
            if binfo is None:
                continue
            else:
                ob = Util.allobjs().get('daz_prop')
                if ob is not None:
                    pb.custom_shape = ob
                    pb.custom_shape_scale = 0.04
                    amtr.data.bones.get(pb.name).show_wire = True
            #Apply Limits and Change Rotation Order
            self.pose.bone_limit_modify(pb)

        # Hide Bones
        for hide in hides:
            amtr.data.bones.get(hide).hide = True

        #Restore Pose.
        self.pose.restore_env_pose(amtr)
    
    def create_controller(self):
        if 'daz_prop' in Util.colobjs('DAZ_HIDE'):
            return
        Global.setOpsMode('OBJECT')
        bpy.ops.mesh.primitive_circle_add()
        Global.setOpsMode('EDIT')
        args = [(0, 0, math.radians(90)), (math.radians(90), 0, 0), (0, math.radians(90), 0)]
        for i in range(3):
            bpy.ops.mesh.primitive_circle_add(
                rotation=args[i]
            )
        Global.setOpsMode('OBJECT')
        bpy.context.object.name = 'daz_prop'
        Util.to_other_collection([bpy.context.object],'DAZ_HIDE',Util.cur_col_name())

    
    def is_armature_modified(self,dobj):
        if dobj.type == 'MESH':
            for modifier in dobj.modifiers:
                if modifier.type=='ARMATURE' and modifier.object is not None:
                    return True
        return False


    def is_child_bone(self,amtr,bone,vertex_groups):
        rtn = self.has_child(amtr,bone)
        if rtn is None or len(rtn) == 0:
            return False
        for r in rtn:
            if r not in vertex_groups:
                return False
        return True

    def has_child(self,amtr,vertex_groups):
        rtn = []
        for bone in amtr.data.edit_bones:
            if bone.parent == vertex_groups:
                rtn.append(bone.name)
        return rtn
    

    def import_empty(self, objs, root):
        # Load an instance of the pose info
        set_transform(root,[1,1,1],"scale")
        Global.deselect()
        Versions.select(root, True)
        Versions.active_object(root)

        for i in range(3):
            root.lock_location[i] = True
            root.lock_rotation[i] = True
            root.lock_scale[i] = True
        Global.setOpsMode('OBJECT')    

    
    def setMaterial(self):
        self.dtb_shaders.make_dct()
        self.dtb_shaders.load_shader_nodes()
        for mesh in self.my_meshs:
            self.dtb_shaders.setup_materials(mesh)


            


    
