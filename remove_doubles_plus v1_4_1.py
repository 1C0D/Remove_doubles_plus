from bpy.props import FloatProperty, BoolProperty
import bmesh
import bpy
import math
import sys

bl_info = {
    "name": "remove doubles plus",
    "author": "1C0D",
    "version": (1, 4, 1),
    "blender": (2, 81, 0),
    "category": "Mesh"}

'''todo:option UVs or not
add move to cursor (offset)to menu?'''

class Multi_OT_Merge(bpy.types.Operator):
    """merging 2 lists of vertices"""
    bl_idname = "multi.merge"
    bl_label = "Multi Merge"
    bl_description = 'merge 2 separated rows of same number of vertices at once'
    bl_options = {"UNDO", "REGISTER"}

    def update_center(self, context):
        if self.merge_center:
            self.merge_first = False
            self.merge_last = False

    def update_last(self, context):
        if self.merge_last:
            self.merge_first = False
            self.merge_center = False

    def update_first(self, context):
        if self.merge_first:
            self.merge_last = False
            self.merge_center = False

    merge_center: BoolProperty(
        name="multi merge centre", default=True, update=update_center)
    merge_last: BoolProperty(name="multi merge last",
                             default=False, update=update_last)
    merge_first: BoolProperty(name="multi merge first",
                              default=False, update=update_first)
    keep_UVs: BoolProperty(name="Correct Uvs", default=True)

    def execute(self, context):

        obj = bpy.context.active_object
        mesh = obj.data
        bm = bmesh.from_edit_mesh(mesh)
        bm.verts.ensure_lookup_table()
        history = bm.select_history

        def deselect():
            for f in bm.edges:
                f.select = False
            for e in bm.edges:
                e.select = False
            for v in bm.verts:
                v.select = False
            bm.select_flush(False)

        def Merge(v1, v2):
            v1.select = True
            v2.select = True
            
            UVs=self.keep_UVs
            if self.merge_center:
                bpy.ops.mesh.merge(type='CENTER', uvs=UVs)
            if self.merge_last:
                history.add(v2)
                bpy.ops.mesh.merge(type='LAST', uvs=UVs)  # 'INVOKE_DEFAULT'
            if self.merge_first:
                history.add(v1)
                bpy.ops.mesh.merge(type='FIRST', uvs=UVs)
            deselect()

        sel = [v for v in bm.verts if v.select]

        if len(sel) != 4:
            self.report({'ERROR'}, "Select 4 vertices with Shift")
            return {'CANCELLED'}

        for item in history:
            if not isinstance(item, bmesh.types.BMVert):
                self.report({'ERROR'}, "Select Vertices only")
                return {'CANCELLED'}

        try:
            V0 = history[-4]
            V1 = history[-3]
            V2 = history[-2]
            V3 = history[-1]
        except IndexError:
            self.report({'ERROR'}, "Select 4 vertices with Shift")
            return {'CANCELLED'}

        def path(v1, v2):
            v1.select = True
            v2.select = True
            bpy.ops.mesh.shortest_path_select()
            path = [v for v in bm.verts if v.select]
            path_copy = path.copy()

            sorted_path = [v1]

            while len(path_copy) > 1:
                v = sorted_path[-1]
                for e in v.link_edges:
                    if e.other_vert(v) in path_copy:
                        path_copy.remove(v)
                        sorted_path.append(e.other_vert(v))
            if v2 not in sorted_path:
                sorted_path.append(v2)

            return sorted_path

        deselect()
        path1 = path(V0, V1)
        deselect()
        path2 = path(V2, V3)
        deselect()
        [Merge(v1, v2) for v1, v2 in zip(path1, path2)]
        bm.normal_update()
        bmesh.update_edit_mesh(mesh)

        return {'FINISHED'}


class Remove_OT_doubles_plus(bpy.types.Operator):
    """Tooltip"""
    bl_idname = "remove.doubles_plus"
    bl_label = "remove doubles plus"
    bl_description = 'remove doubles than loose edges and vertices then insidefaces'
    bl_options = {"UNDO", "REGISTER"}

    recalc_normals: BoolProperty(name="Recalculate normals", default=True)
    rmv_doubles: BoolProperty(name="Remove doubles", default=True)
    rmv_doubles_threshold: FloatProperty(
        name="Threshold", default=0.0001, precision=4, step=0.004, min=0)
    zero_surface: BoolProperty(name="Overlapping edges", default=True)
    zero_surface_threshold: FloatProperty(
        name="Threshold", default=0.0001, precision=4, step=0.004, min=0)
    interior_faces: BoolProperty(
        name="int. faces(except selection)", default=True)
    redundant_verts: BoolProperty(name="Redundant verts", default=True)
    straightness: FloatProperty(
        name="Straightness", default=180, min=0, max=180)
    rmv_loose_verts: BoolProperty(name="loose verts", default=True)
    rmv_loose_edges: BoolProperty(name="loose edges", default=True)
    rmv_loose_faces: BoolProperty(name="loose faces", default=False)

    def clean_geometry(self, bm):

        if self.recalc_normals:
            bmesh.ops.recalc_face_normals(bm, faces=bm.faces)

        if self.rmv_doubles:
            bmesh.ops.remove_doubles(
                bm, verts=bm.verts, dist=self.rmv_doubles_threshold)

        if self.zero_surface:
            bmesh.ops.dissolve_degenerate(
                bm, edges=bm.edges, dist=self.zero_surface_threshold)

        if self.rmv_loose_verts:
            loose_verts = [v for v in bm.verts if not v.link_edges]
            bmesh.ops.delete(bm, geom=loose_verts, context="VERTS")

        if self.rmv_loose_edges:
            loose_edges = [e for e in bm.edges if not e.link_faces]
            bmesh.ops.delete(bm, geom=loose_edges, context="EDGES")

        if self.rmv_loose_faces:
            mode = bm.select_mode
            loose_faces = [f for f in bm.faces if all(
                [not e.is_manifold and e.is_boundary for e in f.edges])]
            bmesh.ops.delete(bm, geom=loose_faces, context="FACES")
            bm.select_mode = mode

        if self.interior_faces:
            loose_faces = [e for e in bm.edges if len(e.link_faces) >= 3]
            faces_sel = [f for f in bm.faces if all(
                [e in loose_faces for e in f.edges]) and f.select == False]
            bmesh.ops.delete(bm, geom=faces_sel, context="FACES_ONLY")

        if self.redundant_verts:
            straight_edged = [v for v in bm.verts if len(v.link_edges) == 2 and
                              (self.straightness <
                               math.degrees((v.link_edges[0].other_vert(v).co-v.co)
                                            .angle(v.link_edges[1].other_vert(v).co - v.co)) < 181)]
            bmesh.ops.dissolve_verts(bm, verts=straight_edged)

    def execute(self, context):

        for ob in context.selected_objects:
            if ob.type == "MESH":
                bm = bmesh.from_edit_mesh(ob.data)
                bm.normal_update()
                bm.verts.ensure_lookup_table()
                verts = len(bm.verts[:])
                edges = len(bm.edges[:])
                faces = len(bm.faces[:])
                self.clean_geometry(bm)
                rmv_verts = verts-len(bm.verts)
                rmv_edges = edges-len(bm.edges)
                rmv_faces = faces-len(bm.faces)
                self.report(
                    {'WARNING'}, f"-[Vert:{rmv_verts}, Edg:{rmv_edges}, Fc:{rmv_faces}]")
                bmesh.update_edit_mesh(ob.data)

        return {'FINISHED'}


def doubles_plus(self, context):

    self.layout.operator("remove.doubles_plus")


def multi_merge(self, context):

    self.layout.operator("multi.merge")


def register():
    bpy.utils.register_class(Remove_OT_doubles_plus)
    bpy.utils.register_class(Multi_OT_Merge)
    bpy.types.VIEW3D_MT_edit_mesh_merge.append(doubles_plus)
    bpy.types.VIEW3D_MT_edit_mesh_merge.prepend(multi_merge)


def unregister():
    bpy.utils.unregister_class(Remove_OT_doubles_plus)
    bpy.utils.unregister_class(Multi_OT_Merge)
    bpy.types.VIEW3D_MT_edit_mesh_merge.remove(doubles_plus)
    bpy.types.VIEW3D_MT_edit_mesh_merge.remove(multi_merge)
