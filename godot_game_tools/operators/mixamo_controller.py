import bpy
import glob
import os

from bpy.props import (StringProperty, FloatProperty, PointerProperty, CollectionProperty)
from bpy.types import (Operator, PropertyGroup)
from bpy_extras.io_utils import ImportHelper

from ..utils import validateArmature

class GGT_OT_INIT_CHARACTER_OT_GGT(bpy.types.Operator, ImportHelper):
    """Initializes imported model for the tool"""
    bl_idname = "wm_ggt.init_character"
    bl_label = "Initialize Character"
    bl_description = "Used to init 'Main' Armature. Loaded character should have 'T-Pose' animation from mixamo."
    bl_options = {'REGISTER', 'UNDO'}
    expected_filename = "t-pose.fbx"
    filename_ext = ".fbx"
    filter_glob = StringProperty(default="*.fbx", options={'HIDDEN'})
    files = CollectionProperty(type=bpy.types.PropertyGroup)

    def import_from_folder(self, path, context):
        extensions = ['fbx']
        filenames = sorted(os.listdir(path))
        valid_files = []
        fileNamesList = []

        for filename in filenames:
            for ext in extensions:
                if filename.lower().endswith('.{}'.format(ext)):
                    valid_files.append(filename)
                    break

        for name in valid_files:
            file_path = os.path.join(path, name)
            extension = (os.path.splitext(file_path)[1])[1:].lower()

            if ext == "fbx":
                if hasattr(bpy.types, bpy.ops.import_scene.fbx.idname()):
                    actionName, actionExtension = os.path.splitext(name)
                    if actionName == "T-Pose":
                        # Local Variable
                        fileNamesList.append(actionName)
                        bpy.ops.import_scene.fbx(filepath = file_path)

    def execute(self, context):
        scene = context.scene
        tool = scene.godot_game_tools
        characterCollectionName = tool.character_collection_name
        if bpy.data.collections.get(characterCollectionName) is None:
          characterCollection = bpy.data.collections.new(characterCollectionName)
          bpy.context.scene.collection.children.link(characterCollection)
        self.report({'INFO'}, 'Loading Character T-Pose')
        filePathWithName = bpy.path.abspath(self.properties.filepath)
        path = os.path.dirname(filePathWithName)
        self.import_from_folder(path, context)
        if bpy.data.collections.get(characterCollectionName) is not None:
            characterArmature = bpy.context.view_layer.objects.active
            if len(characterArmature.children) > 0:
                for mesh in characterArmature.children:
                    bpy.context.scene.collection.children[0].objects.unlink(mesh)
                    characterCollection.objects.link(mesh)
            bpy.context.scene.collection.children[0].objects.unlink(characterArmature)
            characterCollection.objects.link(characterArmature)
            characterArmature.animation_data.action.name = "T-Pose"
            tool.target_object = characterArmature
        bpy.ops.wm_ggt.prepare_mixamo_rig('EXEC_DEFAULT')
        return {'FINISHED'}

# ------------------------------------------------------------------------ #
# ------------------------------------------------------------------------ #
# ------------------------------------------------------------------------ #

class GGT_OT_JOIN_ANIMATIONS_OT_GGT(Operator, ImportHelper):
    bl_idname = "wm_ggt.join_animations"
    bl_label = "Join Animations"
    bl_description = "Join mixamo animations into a single armature"
    bl_options = {'PRESET', 'UNDO'}
    filename_ext = ".fbx"
    filter_glob: StringProperty(default="*.fbx", options={'HIDDEN'})
    files: CollectionProperty(type=bpy.types.PropertyGroup)

    def importModels(self, path, target_armature, context):
        scene = context.scene
        tool = scene.godot_game_tools
        characterCollectionName = tool.character_collection_name
        extensions = ['fbx']
        filenames = sorted(os.listdir(path))
        valid_files = []
        fileNamesList = []
        removeList = []
        # Debug
        removeImports = True

        if bpy.data.collections.get(characterCollectionName) is not None:
            characterCollection = bpy.data.collections.get(characterCollectionName)
            for filename in filenames:
                for ext in extensions:
                    if filename.lower().endswith('.{}'.format(ext)):
                        valid_files.append(filename)
                        break

            for name in valid_files:
                file_path = os.path.join(path, name)
                extension = (os.path.splitext(file_path)[1])[1:].lower()

                if ext == "fbx":
                    if hasattr(bpy.types, bpy.ops.import_scene.fbx.idname()):
                        actionName, actionExtension = os.path.splitext(name)
                        if actionName != "T-Pose":
                            # Local Variable
                            fileNamesList.append(actionName)
                            bpy.ops.import_scene.fbx(filepath = file_path)
                            characterArmature = bpy.context.view_layer.objects.active
                            if len(characterArmature.children) > 0:
                                for mesh in characterArmature.children:
                                    bpy.context.scene.collection.children[0].objects.unlink(mesh)
                                    characterCollection.objects.link(mesh)
                            bpy.context.scene.collection.children[0].objects.unlink(characterArmature)
                            characterCollection.objects.link(characterArmature)

            if len(characterCollection.objects) > 0:
                index = 0
                for obj in characterCollection.objects:
                    if obj.type == "ARMATURE" and obj is not target_armature:
                        # print("Importing animation from file {}".format(obj.name))
                        obj.animation_data.action.name = fileNamesList[index]
                        # Rename the bones
                        for bone in obj.pose.bones:
                            if ':' not in bone.name:
                                continue
                            bone.name = bone.name.split(":")[1]
                        removeList.append(obj)
                        if len(obj.children) > 0:
                            for mesh in obj.children:
                                removeList.append(mesh)
                        index += 1

        # Delete Imported Armatures
        if removeImports:
            objs = [ob for ob in removeList if ob.type in ('ARMATURE', 'MESH')]
            bpy.ops.object.delete({"selected_objects": objs})
            bpy.context.view_layer.objects.active = target_armature

    def setDefaultAnimation(self, context):
        scene = context.scene
        tool = scene.godot_game_tools
        target_armature = tool.target_object
        if len(bpy.data.actions) > 0:
            for action in bpy.data.actions:
                animation = action.name
                if animation in "T-Pose":
                    tool.animations = animation

    def execute(self, context):
        scene = context.scene
        tool = scene.godot_game_tools
        target_armature = tool.target_object
        filePathWithName = bpy.path.abspath(self.properties.filepath)
        path = os.path.dirname(filePathWithName)
        self.importModels(path, target_armature, context)
        bpy.ops.scene.process_actions('EXEC_DEFAULT')
        self.setDefaultAnimation(context)
        self.report({'INFO'}, 'Animations Imported Successfully')
        return {'FINISHED'}

# ------------------------------------------------------------------------ #
# ------------------------------------------------------------------------ #
# ------------------------------------------------------------------------ #


class GGT_OT_RENAME_RIG_OT_GGT(Operator):
    bl_idname = "wm_ggt.rename_mixamo_rig"
    bl_label = "Rename Rig Bones"
    bl_description = "Rename rig bones"

    def execute(self, context):
        scene = context.scene
        tool = scene.godot_game_tools
        visible_armature = tool.visible_armature
        target_armature = tool.target_object
        valid = True
        if valid:
            bpy.data.objects["Armature"].select_set(True)
            target_armature.hide_viewport = False
            bpy.ops.object.mode_set(mode='OBJECT')
            if not bpy.ops.object:
                self.report({'INFO'}, 'Please select the armature')
            for rig in bpy.context.selected_objects:
                if rig.type == 'ARMATURE':
                    for mesh in rig.children:
                        for vg in mesh.vertex_groups:
                            # If no ':' probably its already renamed
                            if ':' not in vg.name:
                                continue
                            vg.name = vg.name.split(":")[1]
                    for bone in rig.pose.bones:
                        if ':' not in bone.name:
                            continue
                        bone.name = bone.name.split(":")[1]
            if bpy.data.actions:
                bpy.context.scene.frame_end = bpy.context.object.animation_data.action.frame_range[-1]
            self.report({'INFO'}, 'Character Bones Successfully Renamed')
        return {'FINISHED'}

# ------------------------------------------------------------------------ #
# ------------------------------------------------------------------------ #
# ------------------------------------------------------------------------ #


class GGT_OT_PREPARE_RIG_OT_GGT(Operator):
    bl_idname = "wm_ggt.prepare_mixamo_rig"
    bl_label = "Prepare Mixamo Rig"
    bl_description = "Fix mixamo rig to export for Godot"

    def execute(self, context):
        scene = context.scene
        tool = scene.godot_game_tools
        target_armature = tool.target_object
        visible_armature = tool.visible_armature
        valid = True
        # Apply transformations on selected Armature
        bpy.context.view_layer.objects.active = target_armature
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
        bpy.ops.wm_ggt.rename_mixamo_rig('EXEC_DEFAULT')

        if valid:
            bpy.data.objects["Armature"].select_set(True)
            target_armature.hide_viewport = False
            bpy.ops.object.select_all(action='SELECT')
            if len(bpy.data.actions) > 0:
                for anim in bpy.data.actions:
                    animation = anim.name
                    bpy.context.scene.frame_start = 0
                    animationToPlay = [anim for anim in bpy.data.actions.keys() if anim in (animation)]
                    animationIndex = bpy.data.actions.keys().index(animation)
                    target_armature.animation_data.action = bpy.data.actions.values()[animationIndex]
                    bpy.context.scene.frame_end = bpy.context.object.animation_data.action.frame_range[-1]
                    bpy.ops.scene.process_actions('EXEC_DEFAULT')
                    tool.actions.append(anim)

            self.report({'INFO'}, 'Rig Armature Prepared')
        return {'FINISHED'}

# ------------------------------------------------------------------------ #
# ------------------------------------------------------------------------ #
# ------------------------------------------------------------------------ #


class GGT_OT_RENAME_MIXAMORIG_OT_GGT(Operator):
    bl_idname = "wm_ggt.rename_mixamo_rig"
    bl_label = "Rename Rig Bones"
    bl_description = "Rename rig bones"

    def execute(self, context):
        scene = context.scene
        tool = scene.godot_game_tools
        visible_armature = tool.visible_armature
        target_armature = tool.target_object
        valid = validateArmature(self, context)
        if valid:
            bpy.data.objects["Armature"].select_set(True)
            target_armature.hide_viewport = False
            bpy.ops.object.mode_set(mode='OBJECT')
            if not bpy.ops.object:
                self.report({'INFO'}, 'Please select the armature')
            for rig in bpy.context.selected_objects:
                if rig.type == 'ARMATURE':
                    for mesh in rig.children:
                        for vg in mesh.vertex_groups:
                            # If no ':' probably its already renamed
                            if ':' not in vg.name:
                                continue
                            vg.name = vg.name.split(":")[1]
                    for bone in rig.pose.bones:
                        if ':' not in bone.name:
                            continue
                        bone.name = bone.name.split(":")[1]
            # for action in bpy.data.actions:
            #     fc = action.fcurves
            #     for f in fc:
            #         f.data_path = f.data_path.replace("mixamorig:","")
            if bpy.data.actions:
                bpy.context.scene.frame_end = bpy.context.object.animation_data.action.frame_range[-1]
            self.report({'INFO'}, 'Character Bones Successfully Renamed')
        return {'FINISHED'}
