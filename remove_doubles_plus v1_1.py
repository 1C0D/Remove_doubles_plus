from bpy.props import FloatProperty, BoolProperty
import bmesh
import bpy

bl_info = {
    "name": "remove doubles plus",
    "author": "1C0D",
    "version": (1, 1, 0),
    "blender": (2, 81, 0),
    "category": "Mesh"}


class Remove_doubles_plus(bpy.types.Operator):
    """Tooltip"""
    bl_idname = "remove.doubles_plus"
    bl_label = "remove doubles plus"
    bl_description = 'remove doubles than loose edges and vertices then insidefaces'
    bl_options = {"UNDO", "REGISTER"}

    double_verts: FloatProperty(default=0.0001, precision=4, step=0.002, min=0)
    interior_faces: BoolProperty(default=True)
    loose_verts: BoolProperty(default=True)
    loose_edges: BoolProperty(default=True)

    def remove_doubles(self, context):

        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.remove_doubles(threshold=self.double_verts)
        bpy.ops.mesh.select_all(action='DESELECT')

    def remove_int_faces(self, context, dont_sel):

        if self.interior_faces:

            context.tool_settings.mesh_select_mode = (False, False, True)
            bpy.ops.mesh.select_all(action='DESELECT')
            bpy.ops.mesh.select_interior_faces()

            for ob in context.selected_objects:
                bm = bmesh.from_edit_mesh(ob.data)

                try:
                    for f in dont_sel:
                        f.select = False
                except ReferenceError:
                    pass

            bpy.ops.mesh.delete(type='ONLY_FACE')
            context.tool_settings.mesh_select_mode = (True, False, False)

    def remove_loose_edges(self, context):

        if self.loose_edges:

            bpy.ops.mesh.select_non_manifold(extend=False, use_wire=True, use_boundary=False,
                                             use_multi_face=False, use_non_contiguous=False, use_verts=False)
            bpy.ops.mesh.delete(type='EDGE')

    def remove_loose_verts(self, context):

        if self.loose_verts:

            bpy.ops.mesh.select_loose()
            bpy.ops.mesh.delete(type='VERT')

    def execute(self, context):

        context.tool_settings.mesh_select_mode = (True, False, False)
        bpy.ops.object.editmode_toggle()
        bpy.ops.object.editmode_toggle()
        dont_sel = []
        dont_sel = [f for e in context.selected_objects for f in bmesh.from_edit_mesh(
            e.data).faces if f.select]

        self.remove_doubles(context)
        self.remove_loose_verts(context)
        self.remove_loose_edges(context)
        self.remove_int_faces(context, dont_sel)

        return {'FINISHED'}


def doubles_plus(self, context):

    self.layout.operator("remove.doubles_plus")

    return {'FINISHED'}


def register():
    bpy.utils.register_class(Remove_doubles_plus)
    bpy.types.VIEW3D_MT_edit_mesh_merge.append(doubles_plus)


def unregister():
    bpy.utils.unregister_class(Remove_doubles_plus)
    bpy.types.VIEW3D_MT_edit_mesh_merge.remove(doubles_plus)
